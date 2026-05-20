import time as _time


def with_backoff(callable_, delays=(0.5, 1.0, 2.0, 5.0), sleep=_time.sleep):
    """Retry callable_() up to len(delays)+1 attempts. Returns result or
    re-raises the last exception."""
    last = None
    for i, d in enumerate((0.0, *delays)):
        if d:
            sleep(d)
        try:
            return callable_()
        except Exception as e:  # noqa: BLE001
            last = e
    raise last
