from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
from typing import Any, Callable

from tenacity import (
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger("retry-client.policy")


class TransientServiceError(Exception):
    """Fallo recuperable: 429, 5xx, timeout o error de conexion."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retry_after: float | None = None,
        response_body: Any = None,
        error_type: str = "transient_error",
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after
        self.response_body = response_body
        self.error_type = error_type


class NonRetryableServiceError(Exception):
    """Fallo que no se corrige reintentando: 400, 401, 403, etc."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response_body: Any = None,
        error_type: str = "non_retryable_error",
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body
        self.error_type = error_type


@dataclass
class BackendResponse:
    status_code: int
    body: Any


@dataclass
class AttemptRecord:
    attempt: int
    outcome: str
    http_status: int | None
    elapsed: float
    timestamp: float
    error: str | None = None
    retry_after: float | None = None
    response_body: Any = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "attempt": self.attempt,
            "outcome": self.outcome,
            "http_status": self.http_status,
            "elapsed": round(self.elapsed, 4),
            "timestamp": self.timestamp,
            "error": self.error,
            "retry_after": self.retry_after,
            "response_body": self.response_body,
        }


@dataclass
class RetryResult:
    success: bool
    attempts: list[AttemptRecord]
    waits: list[float]
    total_elapsed: float
    final_status_code: int | None = None
    final_body: Any = None
    error: Exception | None = None

    @property
    def attempt_count(self) -> int:
        return len(self.attempts)

    @property
    def retries(self) -> int:
        return max(0, len(self.attempts) - 1)

    @property
    def recovered(self) -> bool:
        return self.success and self.retries > 0

    @property
    def error_message(self) -> str | None:
        return str(self.error) if self.error is not None else None


class RetryAfterAwareExponentialWait:
    """Exponential backoff that honors Retry-After when present.

    The wait is never lower than the exponential backoff and never higher than
    ``max_wait``. This keeps 429/503 handling bounded.
    """

    def __init__(
        self,
        multiplier: float = 0.5,
        min_wait: float = 0.5,
        max_wait: float = 2.0,
    ) -> None:
        self._exponential = wait_exponential(
            multiplier=multiplier,
            min=min_wait,
            max=max_wait,
        )
        self.max_wait = max_wait

    def __call__(self, retry_state: Any) -> float:
        base = float(self._exponential(retry_state))
        outcome = getattr(retry_state, "outcome", None)
        exc = outcome.exception() if outcome is not None and outcome.failed else None
        retry_after = getattr(exc, "retry_after", None)
        if retry_after is None:
            return base
        return min(max(base, float(retry_after)), self.max_wait)


class JitteredExponentialWait:
    """Optional bounded jitter used by the extra test.

    The result is always within ``[initial, max_wait]``. This is useful when
    many clients could retry at the same time and we want to spread the load.
    """

    def __init__(
        self,
        initial: float = 0.5,
        max_wait: float = 2.0,
        jitter: float = 0.1,
        random_func: Callable[[], float] = random.random,
    ) -> None:
        self.initial = initial
        self.max_wait = max_wait
        self.jitter = jitter
        self.random_func = random_func

    def __call__(self, retry_state: Any) -> float:
        attempt_number = int(getattr(retry_state, "attempt_number", 1))
        base = min(self.max_wait, self.initial * (2 ** (attempt_number - 1)))
        delta = base * self.jitter
        return min(self.max_wait, base + self.random_func() * delta)


def execute_with_retry(
    call: Callable[[], Any],
    *,
    max_attempts: int = 3,
    initial_wait: float = 0.5,
    max_wait: float = 2.0,
    sleep: Callable[[float], None] = time.sleep,
    wait_strategy: Callable[[Any], float] | None = None,
) -> RetryResult:
    """Execute ``call`` with bounded retries.

    Only ``TransientServiceError`` is retried. ``NonRetryableServiceError`` and
    any other exception abort immediately. The sleeps are injected so tests can
    run without real delays.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts debe ser >= 1")

    attempts: list[AttemptRecord] = []
    waits: list[float] = []
    started = time.monotonic()

    def recording_sleep(seconds: float) -> None:
        waits.append(round(float(seconds), 4))
        sleep(seconds)

    policy = Retrying(
        stop=stop_after_attempt(max_attempts),
        wait=wait_strategy
        or wait_exponential(
            multiplier=initial_wait,
            min=initial_wait,
            max=max_wait,
        ),
        retry=retry_if_exception_type(TransientServiceError),
        reraise=True,
        sleep=recording_sleep,
    )

    try:
        for attempt in policy:
            with attempt:
                attempt_number = int(attempt.retry_state.attempt_number)
                attempt_started = time.monotonic()
                try:
                    response = call()
                except TransientServiceError as exc:
                    attempts.append(
                        AttemptRecord(
                            attempt=attempt_number,
                            outcome="retryable_error",
                            http_status=exc.status_code,
                            elapsed=time.monotonic() - attempt_started,
                            timestamp=time.time(),
                            error=str(exc),
                            retry_after=exc.retry_after,
                            response_body=exc.response_body,
                        )
                    )
                    logger.warning(
                        "attempt=%s outcome=retryable status=%s error=%s retry_after=%s",
                        attempt_number,
                        exc.status_code,
                        exc,
                        exc.retry_after,
                    )
                    raise
                except NonRetryableServiceError as exc:
                    attempts.append(
                        AttemptRecord(
                            attempt=attempt_number,
                            outcome="non_retryable_error",
                            http_status=exc.status_code,
                            elapsed=time.monotonic() - attempt_started,
                            timestamp=time.time(),
                            error=str(exc),
                            response_body=exc.response_body,
                        )
                    )
                    logger.error(
                        "attempt=%s outcome=non_retryable status=%s error=%s",
                        attempt_number,
                        exc.status_code,
                        exc,
                    )
                    raise
                else:
                    status_code = getattr(response, "status_code", None)
                    body = getattr(response, "body", response)
                    attempts.append(
                        AttemptRecord(
                            attempt=attempt_number,
                            outcome="success",
                            http_status=status_code,
                            elapsed=time.monotonic() - attempt_started,
                            timestamp=time.time(),
                            response_body=body,
                        )
                    )
                    logger.info(
                        "attempt=%s outcome=success status=%s",
                        attempt_number,
                        status_code,
                    )
                    return RetryResult(
                        success=True,
                        attempts=attempts,
                        waits=waits,
                        total_elapsed=time.monotonic() - started,
                        final_status_code=status_code,
                        final_body=body,
                    )
    except TransientServiceError as exc:
        return RetryResult(
            success=False,
            attempts=attempts,
            waits=waits,
            total_elapsed=time.monotonic() - started,
            final_status_code=exc.status_code,
            final_body=exc.response_body,
            error=exc,
        )
    except NonRetryableServiceError as exc:
        return RetryResult(
            success=False,
            attempts=attempts,
            waits=waits,
            total_elapsed=time.monotonic() - started,
            final_status_code=exc.status_code,
            final_body=exc.response_body,
            error=exc,
        )

    return RetryResult(
        success=False,
        attempts=attempts,
        waits=waits,
        total_elapsed=time.monotonic() - started,
        error=RuntimeError("La politica de reintentos termino sin resultado"),
    )
