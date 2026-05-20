import pytest
from live.retry import with_backoff


def test_returns_result_immediately_no_sleep():
    """If first call succeeds, result is returned and sleep is never called."""
    sleep_calls = []
    result = with_backoff(lambda: 42, delays=(0.5, 1.0), sleep=sleep_calls.append)
    assert result == 42
    assert sleep_calls == []


def test_retries_with_delays_on_early_failures():
    """Retries using the provided delays when early calls raise."""
    calls = []
    sleep_calls = []

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise ValueError("not yet")
        return "ok"

    result = with_backoff(flaky, delays=(0.1, 0.2, 0.5),
                          sleep=sleep_calls.append)
    assert result == "ok"
    assert len(calls) == 3
    # First attempt uses delay 0.0 (no sleep), subsequent ones use provided delays.
    assert sleep_calls == [0.1, 0.2]


def test_raises_last_exception_after_all_attempts_fail():
    """Re-raises the last exception when all attempts are exhausted."""
    attempts = []

    def always_fail():
        attempts.append(1)
        raise RuntimeError(f"fail #{len(attempts)}")

    with pytest.raises(RuntimeError, match="fail #5"):
        with_backoff(always_fail, delays=(0.0, 0.0, 0.0, 0.0),
                     sleep=lambda d: None)
    assert len(attempts) == 5  # 1 initial + 4 retries
