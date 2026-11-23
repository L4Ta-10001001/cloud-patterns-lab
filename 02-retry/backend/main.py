from __future__ import annotations

import logging
import os
import threading
import time
import uuid
from typing import Any

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("retry-backend")

app = FastAPI(
    title="Retry Backend",
    description=(
        "Backend que simula fallos transitorios, fallos permanentes, "
        "errores no reintentables y rate limiting."
    ),
    version="1.0.0",
)

SCENARIOS = ("success", "transient", "permanent", "bad_request", "rate_limit")
TRANSIENT_FAILURES = 2

_lock = threading.Lock()
_runs: dict[str, dict[str, Any]] = {}
_started_at = time.time()


def _new_run(run_id: str) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "total_requests": 0,
        "failed_requests": 0,
        "successful_requests": 0,
        "attempts": [],
        "created_at": time.time(),
    }


def _status_for(scenario: str, request_number: int) -> int:
    if scenario == "success":
        return 200
    if scenario == "transient":
        return 503 if request_number <= TRANSIENT_FAILURES else 200
    if scenario == "permanent":
        return 503
    if scenario == "bad_request":
        return 400
    if scenario == "rate_limit":
        return 429
    return 400


def _snapshot(run_id: str) -> dict[str, Any] | None:
    with _lock:
        run = _runs.get(run_id)
        if run is None:
            return None
        return {
            **run,
            "attempts": [dict(attempt) for attempt in run["attempts"]],
        }


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "retry-backend",
        "uptime_seconds": round(time.time() - _started_at, 3),
        "scenarios": list(SCENARIOS),
    }


@app.get("/work")
def work(
    scenario: str = Query("success", description="Escenario a simular"),
    run_id: str | None = Query(None, description="Identificador de la ejecucion"),
) -> JSONResponse:
    if scenario not in SCENARIOS:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "error": "unsupported_scenario",
                "message": f"Escenario no soportado: {scenario}",
                "allowed_scenarios": list(SCENARIOS),
            },
        )

    run_id = run_id or f"anonymous-{uuid.uuid4().hex[:12]}"

    # La decision y el registro se hacen bajo el mismo lock para que la
    # secuencia del escenario "transient" sea determinista incluso si llegan
    # peticiones concurrentes con el mismo run_id.
    with _lock:
        run = _runs.setdefault(run_id, _new_run(run_id))
        request_number = run["total_requests"] + 1
        status_code = _status_for(scenario, request_number)

        run["total_requests"] = request_number
        if 200 <= status_code < 400:
            run["successful_requests"] += 1
        else:
            run["failed_requests"] += 1

        run["attempts"].append(
            {
                "attempt": request_number,
                "scenario": scenario,
                "status_code": status_code,
                "timestamp": time.time(),
            }
        )

    payload: dict[str, Any] = {
        "status": "ok" if status_code == 200 else "error",
        "service": "retry-backend",
        "run_id": run_id,
        "scenario": scenario,
        "request_number": request_number,
        "http_status": status_code,
        "timestamp": time.time(),
    }

    if scenario == "transient":
        if status_code == 503:
            payload["message"] = (
                f"Fallo transitorio {request_number}/{TRANSIENT_FAILURES}"
            )
        else:
            payload["message"] = "Recuperado despues de fallos transitorios"
        payload["failures_remaining"] = max(0, TRANSIENT_FAILURES - request_number)
    elif scenario == "permanent":
        payload["message"] = "Fallo permanente simulado"
    elif scenario == "bad_request":
        payload["message"] = "Solicitud invalida: no reintentar"
    elif scenario == "rate_limit":
        payload["message"] = "Limite de solicitudes temporal"
    else:
        payload["message"] = "Operacion exitosa"

    headers = {"X-Backend-Request": str(request_number)}
    if status_code == 429:
        headers["Retry-After"] = "1"

    logger.info(
        "run_id=%s scenario=%s request=%s status=%s",
        run_id,
        scenario,
        request_number,
        status_code,
    )
    return JSONResponse(status_code=status_code, content=payload, headers=headers)


@app.get("/stats")
def stats(run_id: str | None = Query(None)) -> dict[str, Any]:
    if run_id is not None:
        snapshot = _snapshot(run_id)
        if snapshot is None:
            return {
                "run_id": run_id,
                "total_requests": 0,
                "failed_requests": 0,
                "successful_requests": 0,
                "attempts": [],
            }
        return snapshot

    with _lock:
        runs = {
            rid: {
                **run,
                "attempts": [dict(attempt) for attempt in run["attempts"]],
            }
            for rid, run in _runs.items()
        }

    return {
        "runs": runs,
        "total_requests": sum(run["total_requests"] for run in runs.values()),
        "run_count": len(runs),
    }
