"""API mínima reutilizable en Docker local y Amazon ECS."""
from fastapi import FastAPI

app = FastAPI(title="Cloud Patterns Lab - Docker/ECS", version="1.0.0")


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "Hola desde la API de contenedores",
        "runtime": "docker",
        "project": "cloud-patterns-lab",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/info")
def info() -> dict[str, str]:
    return {
        "technology": "FastAPI + Docker",
        "target": "Amazon ECS",
        "purpose": "Demostracion academica de contenedores",
    }
