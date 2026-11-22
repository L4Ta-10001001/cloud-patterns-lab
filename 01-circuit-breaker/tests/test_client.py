"""Pruebas de los endpoints del cliente y de los codigos 502/503."""

from __future__ import annotations

from fastapi.testclient import TestClient

from client import main as client_main

client = TestClient(client_main.app)


def backend_ok(scenario: str) -> dict[str, str]:
    return {"status": "ok", "scenario": scenario}


def backend_fail(scenario: str) -> None:
    raise client_main.BackendError("backend devolvio HTTP 500")


def test_health_del_cliente():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "client"
    assert response.json()["breaker"] == "CLOSED"


def test_solicitud_correcta(monkeypatch):
    monkeypatch.setattr(client_main, "call_backend", backend_ok)

    response = client.get("/request", params={"scenario": "ok"})

    assert response.status_code == 200
    assert response.json()["breaker"] == "CLOSED"
    assert response.json()["backend"]["status"] == "ok"


def test_fallos_del_backend_son_502(monkeypatch):
    monkeypatch.setattr(client_main, "call_backend", backend_fail)

    first = client.get("/request", params={"scenario": "fail"})
    second = client.get("/request", params={"scenario": "fail"})

    assert first.status_code == 502
    assert second.status_code == 502
    assert first.json()["error"] == "backend_failure"
    assert second.json()["breaker"] == "CLOSED"


def test_tercer_fallo_abre_y_devuelve_503(monkeypatch):
    monkeypatch.setattr(client_main, "call_backend", backend_fail)

    for _ in range(2):
        assert client.get("/request", params={"scenario": "fail"}).status_code == 502
    third = client.get("/request", params={"scenario": "fail"})

    assert third.status_code == 503
    assert third.json()["reason"] == "threshold_reached"
    assert third.json()["breaker"] == "OPEN"


def test_circuito_abierto_rechaza_sin_backend(monkeypatch):
    monkeypatch.setattr(client_main, "call_backend", backend_fail)
    for _ in range(3):
        client.get("/request", params={"scenario": "fail"})

    respuesta = client.get("/request", params={"scenario": "ok"})

    assert respuesta.status_code == 503
    assert respuesta.json()["reason"] == "timeout_not_elapsed"
    assert respuesta.json()["breaker"] == "OPEN"


def test_estado_expone_transiciones(monkeypatch):
    monkeypatch.setattr(client_main, "call_backend", backend_fail)
    for _ in range(3):
        client.get("/request", params={"scenario": "fail"})

    status = client.get("/breaker/status").json()

    assert status["state"] == "OPEN"
    assert status["fail_counter"] == 3
    assert status["fail_max"] == 3
    assert status["reset_timeout"] == 10
    assert status["success_threshold"] == 1
    assert status["events"][-1]["to"] == "open"
