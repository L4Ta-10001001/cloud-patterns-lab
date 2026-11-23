from __future__ import annotations

from typing import Any

import pytest

from client.retry_policy import (
    BackendResponse,
    JitteredExponentialWait,
    NonRetryableServiceError,
    RetryAfterAwareExponentialWait,
    TransientServiceError,
    execute_with_retry,
)


class FakeBackend:
    """Callable that returns/raises a scripted sequence of outcomes."""

    def __init__(self, outcomes: list[Any]) -> None:
        self.outcomes = list(outcomes)
        self.calls = 0

    def __call__(self) -> BackendResponse:
        self.calls += 1
        if not self.outcomes:
            raise AssertionError("El backend falso no tiene mas resultados")
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return BackendResponse(status_code=int(outcome), body={"call": self.calls})


class FakeRetryState:
    def __init__(self, attempt_number: int) -> None:
        self.attempt_number = attempt_number


def test_01_success_on_first_attempt() -> None:
    backend = FakeBackend([200])
    waits: list[float] = []

    result = execute_with_retry(backend, sleep=waits.append)

    assert result.success is True
    assert result.attempt_count == 1
    assert result.retries == 0
    assert result.recovered is False
    assert result.final_status_code == 200
    assert waits == []
    assert backend.calls == 1


def test_02_one_failure_then_success() -> None:
    backend = FakeBackend(
        [TransientServiceError("503", status_code=503), 200]
    )
    waits: list[float] = []

    result = execute_with_retry(backend, sleep=waits.append)

    assert result.success is True
    assert result.attempt_count == 2
    assert result.retries == 1
    assert result.recovered is True
    assert waits == [0.5]
    assert backend.calls == 2


def test_03_two_failures_then_success() -> None:
    backend = FakeBackend(
        [
            TransientServiceError("503", status_code=503),
            TransientServiceError("503", status_code=503),
            200,
        ]
    )
    waits: list[float] = []

    result = execute_with_retry(backend, sleep=waits.append)

    assert result.success is True
    assert result.attempt_count == 3
    assert result.retries == 2
    assert result.recovered is True
    assert waits == [0.5, 1.0]
    assert backend.calls == 3


def test_04_permanent_failure_stops_after_three_attempts() -> None:
    backend = FakeBackend(
        [TransientServiceError("503", status_code=503) for _ in range(3)]
    )
    waits: list[float] = []

    result = execute_with_retry(backend, sleep=waits.append)

    assert result.success is False
    assert result.attempt_count == 3
    assert result.retries == 2
    assert result.final_status_code == 503
    assert waits == [0.5, 1.0]
    assert backend.calls == 3


def test_05_bad_request_is_not_retried() -> None:
    backend = FakeBackend(
        [NonRetryableServiceError("400", status_code=400)]
    )
    waits: list[float] = []

    result = execute_with_retry(backend, sleep=waits.append)

    assert result.success is False
    assert result.attempt_count == 1
    assert result.retries == 0
    assert result.final_status_code == 400
    assert waits == []
    assert backend.calls == 1


def test_06_503_triggers_retries() -> None:
    backend = FakeBackend(
        [TransientServiceError("503", status_code=503) for _ in range(3)]
    )

    result = execute_with_retry(backend, sleep=lambda _: None)

    assert result.attempt_count == 3
    assert result.retries == 2
    assert result.final_status_code == 503


def test_07_no_fourth_attempt() -> None:
    backend = FakeBackend(
        [TransientServiceError("503", status_code=503) for _ in range(10)]
    )

    result = execute_with_retry(backend, sleep=lambda _: None, max_attempts=3)

    assert backend.calls == 3
    assert result.attempt_count == 3
    assert result.retries == 2


def test_08_exponential_backoff_waits() -> None:
    backend = FakeBackend(
        [
            TransientServiceError("503", status_code=503),
            TransientServiceError("503", status_code=503),
            200,
        ]
    )
    waits: list[float] = []

    result = execute_with_retry(backend, sleep=waits.append)

    assert waits == [0.5, 1.0]
    assert result.attempts[0].timestamp <= result.attempts[1].timestamp


def test_09_rate_limit_honors_retry_after_with_cap() -> None:
    backend = FakeBackend(
        [
            TransientServiceError("429", status_code=429, retry_after=1.0),
            TransientServiceError("429", status_code=429, retry_after=1.0),
            200,
        ]
    )
    waits: list[float] = []
    wait_strategy = RetryAfterAwareExponentialWait(
        multiplier=0.5,
        min_wait=0.5,
        max_wait=2.0,
    )

    result = execute_with_retry(
        backend,
        sleep=waits.append,
        wait_strategy=wait_strategy,
    )

    assert result.success is True
    assert result.attempt_count == 3
    assert waits == [1.0, 1.0]
    assert all(0.5 <= wait <= 2.0 for wait in waits)


def test_10_attempt_records_match_backend_calls() -> None:
    backend = FakeBackend(
        [TransientServiceError("503", status_code=503), 200]
    )

    result = execute_with_retry(backend, sleep=lambda _: None)

    assert [attempt.http_status for attempt in result.attempts] == [503, 200]
    assert len(result.attempts) == backend.calls


def test_11_jitter_stays_within_bounds() -> None:
    wait = JitteredExponentialWait(
        initial=0.5,
        max_wait=2.0,
        jitter=0.1,
        random_func=lambda: 0.5,
    )

    assert wait(FakeRetryState(1)) == pytest.approx(0.525)
    assert wait(FakeRetryState(2)) == pytest.approx(1.05)
    assert wait(FakeRetryState(3)) == pytest.approx(2.0)

    upper = JitteredExponentialWait(
        initial=0.5,
        max_wait=2.0,
        jitter=0.1,
        random_func=lambda: 1.0,
    )
    for attempt_number in range(1, 6):
        assert 0.5 <= upper(FakeRetryState(attempt_number)) <= 2.0
