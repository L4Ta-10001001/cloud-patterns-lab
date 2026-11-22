"""Configuracion del Circuit Breaker y registro de transiciones.

Se usa una sola instancia global para que el estado sea consistente durante
todas las peticiones atendidas por el proceso del cliente.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import pybreaker

FAIL_MAX = 3
RESET_TIMEOUT = 10
SUCCESS_THRESHOLD = 1
HTTP_TIMEOUT = 2.0

log = logging.getLogger("lab01.breaker")


class TransitionListener(pybreaker.CircuitBreakerListener):
    """Guarda cada cambio de estado para poder mostrarlo como evidencia."""

    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def state_change(self, cb, old_state, new_state) -> None:  # type: ignore[no-untyped-def]
        event = {
            "from": old_state.name if old_state else None,
            "to": new_state.name,
            "at": datetime.now(timezone.utc).isoformat(),
            "fail_counter": cb.fail_counter,
        }
        self.events.append(event)
        log.info("circuit transition %s -> %s", event["from"], event["to"])

    def failure(self, cb, exc) -> None:  # type: ignore[no-untyped-def]
        log.info("circuit failure: %s", type(exc).__name__)

    def success(self, cb) -> None:  # type: ignore[no-untyped-def]
        log.info("circuit success")


def build_breaker(listener: TransitionListener | None = None) -> pybreaker.CircuitBreaker:
    """Construye un breaker con los parametros de la practica."""
    return pybreaker.CircuitBreaker(
        fail_max=FAIL_MAX,
        reset_timeout=RESET_TIMEOUT,
        success_threshold=SUCCESS_THRESHOLD,
        name="backend",
        listeners=[listener] if listener else [],
    )


listener = TransitionListener()
breaker = build_breaker(listener)


def state() -> str:
    """Devuelve el estado en mayusculas, como se muestra en la documentacion."""
    return breaker.current_state.upper()
