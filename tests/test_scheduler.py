import logging
from datetime import datetime, time
import threading

from live.scheduler import should_trigger, Scheduler


def test_should_not_trigger_before_target():
    now = datetime(2026, 5, 20, 14, 0)
    assert should_trigger(now, target_time=time(15, 15),
                          last_action_date="") is False


def test_should_trigger_after_target_unprocessed():
    now = datetime(2026, 5, 20, 15, 20)
    assert should_trigger(now, target_time=time(15, 15),
                          last_action_date="") is True


def test_should_not_trigger_if_already_processed_today():
    now = datetime(2026, 5, 20, 15, 20)
    assert should_trigger(now, target_time=time(15, 15),
                          last_action_date="2026-05-20") is False


def test_should_not_trigger_on_weekend():
    now = datetime(2026, 5, 23, 15, 20)  # 토요일
    assert should_trigger(now, target_time=time(15, 15),
                          last_action_date="") is False


def test_scheduler_calls_on_trigger():
    calls = []
    s = Scheduler(target_time=time(0, 0),  # 항상 지난 시각
                  on_trigger=lambda: calls.append(1),
                  tick_seconds=0.05,
                  clock=lambda: datetime(2026, 5, 20, 10, 0))
    state = type("S", (), {"halted": False, "last_action_date": ""})()
    s.start(state_provider=lambda: state)
    # 한두 tick 안에 호출됐는지 확인
    deadline = threading.Event()
    deadline.wait(0.3)
    s.stop()
    assert len(calls) >= 1


def test_scheduler_respects_halted():
    calls = []
    s = Scheduler(target_time=time(0, 0),
                  on_trigger=lambda: calls.append(1),
                  tick_seconds=0.05,
                  clock=lambda: datetime(2026, 5, 20, 10, 0))
    state = type("S", (), {"halted": True, "last_action_date": ""})()
    s.start(state_provider=lambda: state)
    threading.Event().wait(0.2)
    s.stop()
    assert calls == []


def test_scheduler_logs_on_trigger_exception(caplog):
    def _boom():
        raise RuntimeError("kaboom")
    logger = logging.getLogger("test_scheduler_boom")
    s = Scheduler(target_time=time(0, 0),
                  on_trigger=_boom, tick_seconds=0.05,
                  clock=lambda: datetime(2026, 5, 20, 10, 0),
                  logger=logger)
    state = type("S", (), {"halted": False, "last_action_date": ""})()
    with caplog.at_level(logging.ERROR, logger="test_scheduler_boom"):
        s.start(state_provider=lambda: state)
        threading.Event().wait(0.2)
        s.stop()
    assert any("kaboom" in r.getMessage() or "crashed" in r.getMessage()
                for r in caplog.records)
