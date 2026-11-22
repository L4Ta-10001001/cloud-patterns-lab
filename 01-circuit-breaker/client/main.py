"""Cliente del laboratorio 01: protege la llamada al backend con un breaker."""

from __future__ import annotations

import os

import httpx
import pybreaker
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

try:  # importado como paquete desde tests/
    from .breaker import (
        FAIL_MAX,
        HTTP_TIMEOUT,
        RESET_TIMEOUT,
        SUCCESS_THRESHOLD,
        breaker,
        listener,
        state,
    )
except ImportError:  # ejecutado por uvicorn dentro del contenedor
    from breaker import (  # type: ignore[no-redef]
        FAIL_MAX,
        HTTP_TIMEOUT,
        RESET_TIMEOUT,
        SUCCESS_THRESHOLD,
        breaker,
        listener,
        state,
    )

app = FastAPI(title="Lab01 - Cliente con Circuit Breaker")

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8001").rstrip("/")


class BackendError(Exception):
    """El backend respondio con un error del lado del servidor."""


def call_backend(scenario: str) -> dict[str, object]:
    """Llamada real al backend. Las respuestas 500 se convierten en excepcion."""
    with httpx.Client(timeout=HTTP_TIMEOUT) as client:
        response = client.get(f"{BACKEND_URL}/work", params={"scenario": scenario})

    if response.status_code >= 500:
        raise BackendError(f"backend devolvio HTTP {response.status_code}")

    response.raise_for_status()
    return response.json()  # type: ignore[no-any-return]


def open_reason(error: pybreaker.CircuitBreakerError) -> str:
    """Distingue el momento en que se abrio el circuito de un rechazo posterior."""
    message = str(error)
    if "Timeout not elapsed" in message:
        return "timeout_not_elapsed"
    if "Trial call failed" in message:
        return "trial_call_failed"
    if "threshold reached" in message:
        return "threshold_reached"
    return "circuit_open"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "client", "breaker": state()}


@app.get("/request", response_model=None)
def request(scenario: str = "ok") -> JSONResponse | dict[str, object]:
    try:
        result = breaker.call(call_backend, scenario)
    except pybreaker.CircuitBreakerError as exc:
        return JSONResponse(
            status_code=503,
            content={
                "error": "circuit_open",
                "reason": open_reason(exc),
                "breaker": state(),
                "detail": str(exc),
            },
        )
    except (BackendError, httpx.HTTPError) as exc:
        return JSONResponse(
            status_code=502,
            content={
                "error": "backend_failure",
                "message": str(exc),
                "breaker": state(),
            },
        )

    return {
        "status": "ok",
        "message": "Solicitud completada",
        "breaker": state(),
        "backend": result,
    }


@app.get("/breaker/status")
def breaker_status() -> dict[str, object]:
    return {
        "state": state(),
        "fail_counter": breaker.fail_counter,
        "success_counter": breaker.success_counter,
        "fail_max": FAIL_MAX,
        "reset_timeout": RESET_TIMEOUT,
        "success_threshold": SUCCESS_THRESHOLD,
        "events": list(listener.events),
    }


@app.get("/backend/stats")
def backend_stats() -> dict[str, int]:
    """Diagnostico de la demo: consulta /stats sin pasar por el breaker."""
    with httpx.Client(timeout=HTTP_TIMEOUT) as client:
        response = client.get(f"{BACKEND_URL}/stats")
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]
