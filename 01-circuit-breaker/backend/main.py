"""Backend simulado para la demostracion del patron Circuit Breaker.

Expone /work?scenario=ok|fail para generar respuestas controladas 200/500 y
/stats para comprobar cuantas peticiones llegan realmente al servicio.
"""

from collections import Counter

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="Lab01 - Backend simulado")

requests: Counter[str] = Counter()


def reset_stats() -> None:
    """Reinicia el contador; se usa desde las pruebas automatizadas."""
    requests.clear()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "backend"}


@app.get("/work", response_model=None)
def work(scenario: str = "ok") -> JSONResponse | dict[str, str]:
    requests[scenario] += 1
    requests["total"] += 1

    if scenario == "fail":
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "Fallo simulado del backend",
                "scenario": "fail",
            },
        )

    return {
        "status": "ok",
        "message": "Trabajo completado",
        "scenario": "ok",
    }


@app.get("/stats")
def stats() -> dict[str, int]:
    return {
        "total": requests["total"],
        "ok": requests["ok"],
        "fail": requests["fail"],
    }
