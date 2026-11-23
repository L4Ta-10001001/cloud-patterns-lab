from __future__ import annotations

import uuid

import httpx
import pytest
from fastapi.testclient import TestClient

import client.main as client_main


@pytest.fixture
def backend_url(
    backend_server: str,
    monkeypatch: pytest.MonkeyPatch,
) -> str:
    monkeypatch.setattr(client_main, "BACKEND_URL", backend_server)
    return backend_server


def _run_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def test_integration_transient_recovers_with_three_backend_requests(
    backend_url: str,
) -> None:
    run_id = _run_id("it-transient")

    with TestClient(client_main.app) as client:
        response = client.get(
            "/request",
            params={"scenario": "transient", "run_id": run_id},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["attempts"] == 3
    assert data["retries"] == 2
    assert data["recovered"] is True
    assert data["waits"] == [0.5, 1.0]
    assert [
        attempt["http_status"] for attempt in data["attempt_details"]
    ] == [503, 503, 200]

    stats = httpx.get(
        f"{backend_url}/stats",
        params={"run_id": run_id},
        timeout=2.0,
    ).json()
    assert stats["total_requests"] == 3
    assert stats["failed_requests"] == 2
    assert stats["successful_requests"] == 1
    assert [attempt["status_code"] for attempt in stats["attempts"]] == [
        503,
        503,
        200,
    ]


def test_integration_permanent_stops_at_three_attempts(backend_url: str) -> None:
    run_id = _run_id("it-permanent")

    with TestClient(client_main.app) as client:
        response = client.get(
            "/request",
            params={"scenario": "permanent", "run_id": run_id},
        )

    assert response.status_code == 503
    data = response.json()
    assert data["attempts"] == 3
    assert data["retries"] == 2

    stats = httpx.get(
        f"{backend_url}/stats",
        params={"run_id": run_id},
        timeout=2.0,
    ).json()
    assert stats["total_requests"] == 3
    assert [attempt["status_code"] for attempt in stats["attempts"]] == [
        503,
        503,
        503,
    ]


def test_integration_bad_request_is_not_retried(backend_url: str) -> None:
    run_id = _run_id("it-bad")

    with TestClient(client_main.app) as client:
        response = client.get(
            "/request",
            params={"scenario": "bad_request", "run_id": run_id},
        )

    assert response.status_code == 400
    data = response.json()
    assert data["attempts"] == 1
    assert data["retries"] == 0

    stats = httpx.get(
        f"{backend_url}/stats",
        params={"run_id": run_id},
        timeout=2.0,
    ).json()
    assert stats["total_requests"] == 1
    assert [attempt["status_code"] for attempt in stats["attempts"]] == [400]


def test_integration_success_has_one_backend_request(backend_url: str) -> None:
    run_id = _run_id("it-success")

    with TestClient(client_main.app) as client:
        response = client.get(
            "/request",
            params={"scenario": "success", "run_id": run_id},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["attempts"] == 1
    assert data["retries"] == 0

    stats = httpx.get(
        f"{backend_url}/stats",
        params={"run_id": run_id},
        timeout=2.0,
    ).json()
    assert stats["total_requests"] == 1
    assert [attempt["status_code"] for attempt in stats["attempts"]] == [200]
