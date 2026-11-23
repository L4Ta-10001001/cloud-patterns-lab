from __future__ import annotations

import socket
import threading
import time
import uuid
from collections.abc import Iterator

import httpx
import pytest
import uvicorn

import backend.main as backend_main
import client.main as client_main


@pytest.fixture(autouse=True)
def fast_sleep(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[float]]:
    """Replace real sleeps with a recorder for every test."""
    recorded: list[float] = []

    def fake_sleep(seconds: float) -> None:
        recorded.append(seconds)

    monkeypatch.setattr(client_main, "SLEEP", fake_sleep)
    yield recorded


@pytest.fixture(scope="session")
def backend_server() -> Iterator[str]:
    """Start a real backend process in a thread for integration tests."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

    config = uvicorn.Config(
        backend_main.app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            response = httpx.get(f"{base_url}/health", timeout=0.5)
            if response.status_code == 200:
                break
        except httpx.HTTPError:
            pass
        time.sleep(0.05)
    else:
        raise RuntimeError("El backend de pruebas no inicio")

    yield base_url

    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture
def run_id() -> str:
    return f"test-{uuid.uuid4().hex[:10]}"
