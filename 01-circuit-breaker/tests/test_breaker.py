"""Ocho escenarios del patrón verificados contra PyBreaker con reloj simulado."""

from __future__ import annotations

import pybreaker
import pytest

from client.breaker import RESET_TIMEOUT, TransitionListener, build_breaker


class BackendFalso:
    def __init__(self) -> None:
        self.llamadas = 0

    def ok(self) -> str:
        self.llamadas += 1
        return "ok"

    def fail(self) -> None:
        self.llamadas += 1
        raise RuntimeError("fallo simulado del backend")


@pytest.fixture
def circuito(fake_clock):  # type: ignore[no-untyped-def]
    oyente = TransitionListener()
    return build_breaker(oyente), oyente, fake_clock


def test_01_operacion_normal(circuito):  # type: ignore[no-untyped-def]
    cb, oyente, _ = circuito
    backend = BackendFalso()

    assert cb.call(backend.ok) == "ok"
    assert cb.current_state == pybreaker.STATE_CLOSED
    assert cb.fail_counter == 0
    assert oyente.events == []


def test_02_primer_fallo(circuito):  # type: ignore[no-untyped-def]
    cb, _, _ = circuito
    backend = BackendFalso()

    with pytest.raises(RuntimeError):
        cb.call(backend.fail)

    assert cb.current_state == pybreaker.STATE_CLOSED
    assert cb.fail_counter == 1
    assert backend.llamadas == 1


def test_03_segundo_fallo(circuito):  # type: ignore[no-untyped-def]
    cb, _, _ = circuito
    backend = BackendFalso()

    for _ in range(2):
        with pytest.raises(RuntimeError):
            cb.call(backend.fail)

    assert cb.current_state == pybreaker.STATE_CLOSED
    assert cb.fail_counter == 2


def test_04_tercer_fallo_abre_circuito(circuito):  # type: ignore[no-untyped-def]
    cb, oyente, _ = circuito
    backend = BackendFalso()

    for _ in range(2):
        with pytest.raises(RuntimeError):
            cb.call(backend.fail)
    with pytest.raises(pybreaker.CircuitBreakerError):
        cb.call(backend.fail)

    assert cb.current_state == pybreaker.STATE_OPEN
    assert cb.fail_counter == 3
    assert [e["to"] for e in oyente.events] == [pybreaker.STATE_OPEN]


def test_05_rechazo_inmediato_sin_llamar_backend(circuito):  # type: ignore[no-untyped-def]
    cb, _, _ = circuito
    backend = BackendFalso()

    for _ in range(3):
        with pytest.raises((RuntimeError, pybreaker.CircuitBreakerError)):
            cb.call(backend.fail)
    llamadas_al_abrir = backend.llamadas

    with pytest.raises(pybreaker.CircuitBreakerError) as info:
        cb.call(backend.ok)

    assert "Timeout not elapsed" in str(info.value)
    assert backend.llamadas == llamadas_al_abrir
    assert cb.current_state == pybreaker.STATE_OPEN


def test_06_half_open_exitoso_cierra_circuito(circuito):  # type: ignore[no-untyped-def]
    cb, oyente, reloj = circuito
    backend = BackendFalso()

    for _ in range(3):
        with pytest.raises((RuntimeError, pybreaker.CircuitBreakerError)):
            cb.call(backend.fail)
    reloj.advance(RESET_TIMEOUT + 1)

    assert cb.call(backend.ok) == "ok"
    assert cb.current_state == pybreaker.STATE_CLOSED
    assert [e["to"] for e in oyente.events] == [
        pybreaker.STATE_OPEN,
        pybreaker.STATE_HALF_OPEN,
        pybreaker.STATE_CLOSED,
    ]


def test_07_half_open_fallido_vuelve_a_abrir(circuito):  # type: ignore[no-untyped-def]
    cb, oyente, reloj = circuito
    backend = BackendFalso()

    for _ in range(3):
        with pytest.raises((RuntimeError, pybreaker.CircuitBreakerError)):
            cb.call(backend.fail)
    reloj.advance(RESET_TIMEOUT + 1)

    with pytest.raises(pybreaker.CircuitBreakerError):
        cb.call(backend.fail)

    assert cb.current_state == pybreaker.STATE_OPEN
    assert oyente.events[-1]["to"] == pybreaker.STATE_OPEN


def test_08_operacion_tras_recuperacion(circuito):  # type: ignore[no-untyped-def]
    cb, _, reloj = circuito
    backend = BackendFalso()

    for _ in range(3):
        with pytest.raises((RuntimeError, pybreaker.CircuitBreakerError)):
            cb.call(backend.fail)
    reloj.advance(RESET_TIMEOUT + 1)
    cb.call(backend.ok)

    assert cb.call(backend.ok) == "ok"
    assert cb.current_state == pybreaker.STATE_CLOSED
    assert backend.llamadas == 5
