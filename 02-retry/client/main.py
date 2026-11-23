from __future__ import annotations

import logging
import os
import time
import uuid
from typing import Any

import httpx
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

try:  # Paquete (pytest) o modulo plano (uvicorn dentro del contenedor).
    from .retry_policy import (
        BackendResponse,
        NonRetryableServiceError,
        RetryAfterAwareExponentialWait,
        TransientServiceError,
        execute_with_retry,
    )
except ImportError:  # pragma: no cover - depende del contexto de ejecucion
    from retry_policy import (
        BackendResponse,
        NonRetryableServiceError,
        RetryAfterAwareExponentialWait,
        TransientServiceError,
        execute_with_retry,
    )

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("retry-client")

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8001").rstrip("/")
HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "2.0"))
MAX_ATTEMPTS = int(os.getenv("RETRY_MAX_ATTEMPTS", "3"))
INITIAL_WAIT = float(os.getenv("RETRY_INITIAL_WAIT", "0.5"))
MAX_WAIT = float(os.getenv("RETRY_MAX_WAIT", "2.0"))

SCENARIOS = ("success", "transient", "permanent", "bad_request", "rate_limit")
SLEEP = time.sleep  # tests replace this to avoid real waits

app = FastAPI(
    title="Retry Client",
    description=(
        "Cliente HTTP que aplica el patron Retry con Tenacity, exponential "
        "backoff y clasificacion explicita de errores."
    ),
    version="1.0.0",
)

_started_at = time.time()


def http_client_factory() -> httpx.Client:
    return httpx.Client(timeout=HTTP_TIMEOUT)


HTTP_CLIENT_FACTORY = http_client_factory


def _parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        seconds = float(value.strip())
    except ValueError:
        return None
    return max(0.0, seconds)


def _json_or_text(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return response.text


def call_backend(scenario: str, run_id: str) -> BackendResponse:
    """Call the backend and translate HTTP results into retry semantics.

    Only 429, 500, 502, 503, 504, timeouts and connection errors are converted
    into ``TransientServiceError``. Explicit 4xx client errors are converted
    into ``NonRetryableServiceError`` so Tenacity never retries them.
    """
    url = f"{BACKEND_URL}/work"
    params = {"scenario": scenario, "run_id": run_id}

    with HTTP_CLIENT_FACTORY() as client:
        try:
            response = client.get(url, params=params)
        except httpx.TimeoutException as exc:
            raise TransientServiceError(
                f"timeout al llamar al backend: {exc}",
                error_type="timeout",
            ) from exc
        except httpx.TransportError as exc:
            raise TransientServiceError(
                f"error de conexion con el backend: {exc}",
                error_type="connection_error",
            ) from exc

    body = _json_or_text(response)

    if 200 <= response.status_code < 300:
        return BackendResponse(status_code=response.status_code, body=body)

    if response.status_code in {429, 500, 502, 503, 504}:
        retry_after = _parse_retry_after(response.headers.get("Retry-After"))
        raise TransientServiceError(
            f"HTTP {response.status_code} del backend",
            status_code=response.status_code,
            retry_after=retry_after,
            response_body=body,
            error_type="retryable_http_error",
        )

    if response.status_code in {400, 401, 403, 404, 409, 422}:
        raise NonRetryableServiceError(
            f"HTTP {response.status_code} del backend (no reintentable)",
            status_code=response.status_code,
            response_body=body,
            error_type="non_retryable_http_error",
        )

    raise NonRetryableServiceError(
        f"HTTP {response.status_code} no clasificado; no se reintenta",
        status_code=response.status_code,
        response_body=body,
        error_type="unclassified_http_error",
    )


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "retry-client",
        "backend_url": BACKEND_URL,
        "retry_policy": {
            "max_attempts": MAX_ATTEMPTS,
            "retries": MAX_ATTEMPTS - 1,
            "initial_wait_seconds": INITIAL_WAIT,
            "max_wait_seconds": MAX_WAIT,
            "http_timeout_seconds": HTTP_TIMEOUT,
            "strategy": "exponential_backoff",
            "retry_on": [429, 500, 502, 503, 504, "timeout", "connection_error"],
            "no_retry_on": [400, 401, 403, 404, 409, 422],
        },
        "uptime_seconds": round(time.time() - _started_at, 3),
    }


@app.get("/request")
def request(
    scenario: str = Query("success", description="Escenario a ejecutar"),
    run_id: str | None = Query(None, description="Identificador de la ejecucion"),
) -> JSONResponse:
    if scenario not in SCENARIOS:
        return JSONResponse(
            status_code=400,
            content={
                "status": "failed",
                "service": "retry-client",
                "error": "unsupported_scenario",
                "message": f"Escenario no soportado: {scenario}",
                "allowed_scenarios": list(SCENARIOS),
                "attempts": 0,
                "retries": 0,
                "recovered": False,
            },
        )

    run_id = run_id or f"client-{uuid.uuid4().hex[:12]}"

    wait_strategy = RetryAfterAwareExponentialWait(
        multiplier=INITIAL_WAIT,
        min_wait=INITIAL_WAIT,
        max_wait=MAX_WAIT,
    )

    result = execute_with_retry(
        lambda: call_backend(scenario, run_id),
        max_attempts=MAX_ATTEMPTS,
        initial_wait=INITIAL_WAIT,
        max_wait=MAX_WAIT,
        sleep=SLEEP,
        wait_strategy=wait_strategy,
    )

    payload = {
        "status": "success" if result.success else "failed",
        "service": "retry-client",
        "run_id": run_id,
        "scenario": scenario,
        "attempts": result.attempt_count,
        "retries": result.retries,
        "recovered": result.recovered,
        "http_status": result.final_status_code,
        "waits": result.waits,
        "total_elapsed": round(result.total_elapsed, 3),
        "attempt_details": [attempt.as_dict() for attempt in result.attempts],
        "backend_response": result.final_body,
        "error": result.error_message,
    }

    if result.success:
        return JSONResponse(status_code=200, content=payload)

    status_code = result.final_status_code or 503
    headers = {"Retry-After": "1"} if status_code == 429 else {}
    return JSONResponse(status_code=status_code, content=payload, headers=headers)


@app.get("/backend/stats")
def backend_stats(
    run_id: str | None = Query(None, description="Filtrar por run_id"),
) -> JSONResponse:
    """Read backend counters without applying retries.

    This endpoint is used by the demo to prove that the number of backend
    requests matches the number of client attempts.
    """
    url = f"{BACKEND_URL}/stats"
    params = {"run_id": run_id} if run_id else None

    try:
        with HTTP_CLIENT_FACTORY() as client:
            response = client.get(url, params=params)
    except httpx.HTTPError as exc:
        return JSONResponse(
            status_code=502,
            content={
                "status": "error",
                "error": "backend_unreachable",
                "message": str(exc),
            },
        )

    body = _json_or_text(response)
    content = body if isinstance(body, (dict, list)) else {"raw": body}
    return JSONResponse(status_code=response.status_code, content=content)
