"""Configuracion comun de las pruebas del laboratorio 01."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pybreaker
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class FakeDatetime:
    """Reloj controlado: PyBreaker usa datetime.now(UTC) para el timeout."""

    value = datetime(2026, 1, 1, tzinfo=timezone.utc)

    @classmethod
    def now(cls, tz=None):  # type: ignore[no-untyped-def]
        return cls.value

    @classmethod
    def advance(cls, seconds: int) -> None:
        cls.value += timedelta(seconds=seconds)


@pytest.fixture
def fake_clock(monkeypatch):  # type: ignore[no-untyped-def]
    FakeDatetime.value = datetime(2026, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(pybreaker, "datetime", FakeDatetime)
    return FakeDatetime


@pytest.fixture(autouse=True)
def reset_estado():
    """Cada prueba empieza con un circuito cerrado y contadores a cero."""
    from backend import main as backend_module
    from client import breaker as breaker_module

    breaker_module.breaker.close()
    breaker_module.breaker._state_storage.reset_counter()
    breaker_module.breaker._state_storage.reset_success_counter()
    breaker_module.listener.events.clear()
    backend_module.reset_stats()
    yield
