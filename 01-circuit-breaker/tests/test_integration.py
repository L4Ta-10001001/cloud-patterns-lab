"""Integracion real entre ambos servicios usando ASGI (sin red externa)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend import main as backend_main
from client import main as client_main

client = TestClient(client_main.app)


def llamada_real_al_backend(scenario: str) -> dict[str, object]:
    """Sustituye a httpx real por un transporte ASGI hacia el backend."""
    response = TestClient(backend_main.app).get("/work", params={"scenario": scenario})
    if response.status_code >= 500:
        raise client_main.BackendError(f"backend devolvio HTTP {response.status_code}")
    response.raise_for_status()
    return response.json()  # type: ignore[no-any-return]


def test_flujo_completo_con_contador_del_backend(monkeypatch, fake_clock):
    monkeypatch.setattr(client_main, "call_backend", llamada_real_al_backend)

    ok = client.get("/request", params={"scenario": "ok"})
    assert ok.status_code == 200
    assert backend_main.stats()["total"] == 1

    for _ in range(3):
        respuesta = client.get("/request", params={"scenario": "fail"})
        assert respuesta.status_code in (502, 503)
    assert backend_main.stats()["total"] == 4
    assert client.get("/breaker/status").json()["state"] == "OPEN"

    rechazada = client.get("/request", params={"scenario": "ok"})
    assert rechazada.status_code == 503
    assert rechazada.json()["reason"] == "timeout_not_elapsed"
    # Prueba clave: el backend no recibe ninguna peticion mientras esta OPEN.
    assert backend_main.stats()["total"] == 4

    fake_clock.advance(11)
    recuperada = client.get("/request", params={"scenario": "ok"})
    assert recuperada.status_code == 200
    assert client.get("/breaker/status").json()["state"] == "CLOSED"
    assert backend_main.stats()["total"] == 5


def test_backend_expone_sus_contadores():
    stats = TestClient(backend_main.app).get("/stats").json()
    assert stats == {"total": 0, "ok": 0, "fail": 0}
