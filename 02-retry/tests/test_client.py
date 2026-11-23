from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

import client.main as client_main


class MockBackend:
    """In-process backend used by the client endpoint tests."""

    def __init__(self) -> None:
        self.statuses: dict[str, list[int]] = {}
        self.requests: list[dict[str, str | int]] = []

    def _record(self, run_id: str, scenario: str, status: int) -> None:
        self.statuses.setdefault(run_id, []).append(status)
        self.requests.append(
            {"scenario": scenario, "run_id": run_id, "status": status}
        )

    def handler(self, request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/stats"):
            run_id = request.url.params.get("run_id", "anonymous")
            statuses = self.statuses.get(run_id, [])
            return httpx.Response(
                200,
                json={
                    "run_id": run_id,
                    "total_requests": len(statuses),
                    "failed_requests": sum(1 for status in statuses if status >= 400),
                    "successful_requests": sum(
                        1 for status in statuses if 200 <= status < 400
                    ),
                    "attempts": [
                        {"attempt": index + 1, "status_code": status}
                        for index, status in enumerate(statuses)
                    ],
                },
            )

        scenario = request.url.params.get("scenario", "success")
        run_id = request.url.params.get("run_id", "anonymous")
        request_number = len(self.statuses.get(run_id, [])) + 1

        if scenario == "success":
            status = 200
        elif scenario == "transient":
            status = 503 if request_number <= 2 else 200
        elif scenario == "permanent":
            status = 503
        elif scenario == "bad_request":
            status = 400
        elif scenario == "rate_limit":
            status = 429
        else:
            status = 500

        self._record(run_id, scenario, status)
        headers = {"Retry-After": "1"} if status == 429 else {}
        return httpx.Response(
            status,
            headers=headers,
            json={
                "status": "ok" if status == 200 else "error",
                "request_number": request_number,
                "scenario": scenario,
            },
        )


@pytest.fixture
def mock_backend(monkeypatch: pytest.MonkeyPatch) -> MockBackend:
    backend = MockBackend()
    transport = httpx.MockTransport(backend.handler)

    def factory() -> httpx.Client:
        return httpx.Client(transport=transport, timeout=2.0)

    monkeypatch.setattr(client_main, "HTTP_CLIENT_FACTORY", factory)
    monkeypatch.setattr(client_main, "BACKEND_URL", "http://backend.test")
    return backend


def test_health_del_cliente() -> None:
    with TestClient(client_main.app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "retry-client"
    assert data["retry_policy"]["max_attempts"] == 3
    assert data["retry_policy"]["initial_wait_seconds"] == 0.5


def test_solicitud_exitosa_un_intento(mock_backend: MockBackend) -> None:
    with TestClient(client_main.app) as client:
        response = client.get(
            "/request",
            params={"scenario": "success", "run_id": "c-success"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["attempts"] == 1
    assert data["retries"] == 0
    assert data["recovered"] is False
    assert data["http_status"] == 200
    assert data["waits"] == []
    assert len(mock_backend.requests) == 1


def test_transient_se_recupera_tras_dos_reintentos(
    mock_backend: MockBackend,
) -> None:
    with TestClient(client_main.app) as client:
        response = client.get(
            "/request",
            params={"scenario": "transient", "run_id": "c-transient"},
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
    assert len(mock_backend.requests) == 3


def test_permanent_agota_los_intentos(mock_backend: MockBackend) -> None:
    with TestClient(client_main.app) as client:
        response = client.get(
            "/request",
            params={"scenario": "permanent", "run_id": "c-permanent"},
        )

    assert response.status_code == 503
    data = response.json()
    assert data["attempts"] == 3
    assert data["retries"] == 2
    assert data["recovered"] is False
    assert [
        attempt["http_status"] for attempt in data["attempt_details"]
    ] == [503, 503, 503]
    assert len(mock_backend.requests) == 3


def test_bad_request_no_se_reintenta(mock_backend: MockBackend) -> None:
    with TestClient(client_main.app) as client:
        response = client.get(
            "/request",
            params={"scenario": "bad_request", "run_id": "c-bad"},
        )

    assert response.status_code == 400
    data = response.json()
    assert data["attempts"] == 1
    assert data["retries"] == 0
    assert data["recovered"] is False
    assert data["waits"] == []
    assert len(mock_backend.requests) == 1


def test_rate_limit_reintenta_con_espera_acotada(
    mock_backend: MockBackend,
) -> None:
    with TestClient(client_main.app) as client:
        response = client.get(
            "/request",
            params={"scenario": "rate_limit", "run_id": "c-rate"},
        )

    assert response.status_code == 429
    data = response.json()
    assert data["attempts"] == 3
    assert data["retries"] == 2
    assert data["waits"] == [1.0, 1.0]
    assert all(wait <= 2.0 for wait in data["waits"])
    assert len(mock_backend.requests) == 3


def test_escenario_invalido_no_llama_al_backend(
    mock_backend: MockBackend,
) -> None:
    with TestClient(client_main.app) as client:
        response = client.get(
            "/request",
            params={"scenario": "unknown", "run_id": "c-unknown"},
        )

    assert response.status_code == 400
    assert response.json()["error"] == "unsupported_scenario"
    assert mock_backend.requests == []


def test_error_de_conexion_reintenta_y_devuelve_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        client_main,
        "HTTP_CLIENT_FACTORY",
        lambda: httpx.Client(transport=transport, timeout=2.0),
    )

    with TestClient(client_main.app) as client:
        response = client.get(
            "/request",
            params={"scenario": "success", "run_id": "c-connection"},
        )

    assert response.status_code == 503
    data = response.json()
    assert data["attempts"] == 3
    assert data["retries"] == 2
    assert data["error"] is not None


def test_timeout_reintenta_y_devuelve_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        client_main,
        "HTTP_CLIENT_FACTORY",
        lambda: httpx.Client(transport=transport, timeout=2.0),
    )

    with TestClient(client_main.app) as client:
        response = client.get(
            "/request",
            params={"scenario": "success", "run_id": "c-timeout"},
        )

    assert response.status_code == 503
    data = response.json()
    assert data["attempts"] == 3
    assert data["retries"] == 2


def test_backend_stats_proxy(mock_backend: MockBackend) -> None:
    with TestClient(client_main.app) as client:
        client.get(
            "/request",
            params={"scenario": "transient", "run_id": "c-stats"},
        )
        response = client.get("/backend/stats", params={"run_id": "c-stats"})

    assert response.status_code == 200
    data = response.json()
    assert data["total_requests"] == 3
    assert [
        attempt["status_code"] for attempt in data["attempts"]
    ] == [503, 503, 200]
