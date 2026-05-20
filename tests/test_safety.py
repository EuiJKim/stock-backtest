from datetime import datetime
import pytest
from live.safety import (is_market_open, within_position_limit,
                          daily_loss_kill, order_size_ok,
                          holdings_drift_ok, validate_paper_mode)
from live.state import Holding
from live.errors import SafetyError


def test_market_open_weekday_inside():
    # 2026-05-20은 수요일
    assert is_market_open(datetime(2026, 5, 20, 10, 0)) is True


def test_market_closed_weekend():
    assert is_market_open(datetime(2026, 5, 23, 10, 0)) is False


def test_market_closed_outside_hours():
    assert is_market_open(datetime(2026, 5, 20, 8, 0)) is False
    assert is_market_open(datetime(2026, 5, 20, 16, 0)) is False


def test_within_position_limit_under():
    assert within_position_limit(3_000_000, 10_000_000, 0.40) is True


def test_within_position_limit_over():
    assert within_position_limit(5_000_000, 10_000_000, 0.40) is False


def test_within_position_limit_zero_equity():
    assert within_position_limit(1.0, 0.0, 0.40) is False


def test_daily_loss_kill_triggers():
    # -5% 초과 손실
    assert daily_loss_kill(equity_now=9_400_000,
                           equity_start=10_000_000,
                           max_loss_pct=0.05) is True


def test_daily_loss_kill_does_not_trigger():
    assert daily_loss_kill(9_700_000, 10_000_000, 0.05) is False


def test_order_size_ok():
    assert order_size_ok(20_000, min_amount=10_000) is True
    assert order_size_ok(5_000, min_amount=10_000) is False


def test_holdings_drift_ok_within_tolerance():
    state = {"360750": Holding(shares=100, entry_price=15000.0)}
    broker = {"360750": {"shares": 102, "avg_price": 15000.0}}
    assert holdings_drift_ok(state, broker, 0.05) is True


def test_holdings_drift_detects_difference():
    state = {"360750": Holding(shares=100, entry_price=15000.0)}
    broker = {"360750": {"shares": 50, "avg_price": 15000.0}}
    assert holdings_drift_ok(state, broker, 0.05) is False


def test_holdings_drift_detects_missing_position():
    state = {"360750": Holding(shares=100, entry_price=15000.0)}
    broker = {}  # 브로커에 없음
    assert holdings_drift_ok(state, broker, 0.05) is False


def test_validate_paper_mode_passes():
    validate_paper_mode("paper")  # 예외 없음


def test_validate_paper_mode_rejects_live():
    with pytest.raises(SafetyError):
        validate_paper_mode("live")
