"""Tests for run_trader_tick (Fix 8: extracted tick function)."""
import logging
import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from run_trader import run_trader_tick
from live.state import TraderState, TraderParams, Holding


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _log():
    return logging.getLogger("test_tick")


def _weekday_market_hours():
    """A datetime that is inside KRX market hours on a weekday."""
    # 2026-05-19 is a Tuesday; 10:00 KST is inside 09:00-15:30.
    return datetime(2026, 5, 19, 10, 0, 0)


def _weekday_after_hours():
    """A datetime that is outside KRX market hours on a weekday."""
    return datetime(2026, 5, 19, 17, 0, 0)


def _fake_panels_loader(codes):
    """Return a minimal two-row close-price DataFrame."""
    idx = pd.date_range("2026-01-01", periods=2, freq="MS")
    data = {c: [10000.0, 11000.0] for c in codes} if codes else {}
    return pd.DataFrame(data, index=idx)


class FakeBroker:
    def __init__(self, equity=10_000_000.0, holdings=None, raise_on=None):
        self.equity = equity
        self._holdings = holdings or {}
        self.placed = []
        self._next_id = 0
        self.raise_on = raise_on or set()

    def get_balance(self):
        if "get_balance" in self.raise_on:
            raise RuntimeError("balance error")
        return {"cash": self.equity * 0.5, "equity": self.equity}

    def get_holdings(self):
        if "get_holdings" in self.raise_on:
            raise RuntimeError("holdings error")
        return dict(self._holdings)

    def get_quote(self, code):
        return 10000.0

    def place_order(self, code, side, qty):
        self._next_id += 1
        oid = f"ORD-{self._next_id}"
        self.placed.append((oid, code, side, qty))
        return oid

    def get_order_status(self, order_id):
        _, code, side, qty = next(p for p in self.placed if p[0] == order_id)
        return {"order_id": order_id, "status": "FILLED",
                "filled_qty": qty, "fill_price": 10000.0}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_market_closed_returns_market_closed(tmp_path):
    """Tick outside KRX hours returns 'market_closed', broker never called."""
    broker = FakeBroker()
    state = TraderState()
    params = TraderParams()

    result = run_trader_tick(
        broker=broker, state=state, params=params,
        universe_codes=[], log=_log(),
        state_path=tmp_path / "state.json",
        now=_weekday_after_hours(),
        panels_loader=_fake_panels_loader,
    )

    assert result == "market_closed"
    assert broker.placed == []
    assert state.halted is False


def test_drift_detected_halts_state(tmp_path):
    """Tick where broker holdings diverge from state holdings -> drift_halt."""
    state = TraderState(holdings={"360750": Holding(shares=100,
                                                    entry_price=10000.0)})
    broker_holdings = {"360750": {"shares": 50}}
    broker = FakeBroker(holdings=broker_holdings)
    params = TraderParams(drift_tolerance=0.05)

    result = run_trader_tick(
        broker=broker, state=state, params=params,
        universe_codes=["360750"], log=_log(),
        state_path=tmp_path / "state.json",
        now=_weekday_market_hours(),
        panels_loader=_fake_panels_loader,
    )

    assert result == "drift_halt"
    assert state.halted is True
    assert (tmp_path / "state.json").exists()


def test_first_run_of_day_snapshots_equity(tmp_path):
    """First tick of a new day snapshots equity_start_of_day."""
    state = TraderState(last_action_date="2026-05-18",
                        equity_start_of_day=0.0)
    broker = FakeBroker(equity=12_000_000.0)
    params = TraderParams()

    run_trader_tick(
        broker=broker, state=state, params=params,
        universe_codes=[],
        log=_log(),
        state_path=tmp_path / "state.json",
        now=_weekday_market_hours(),
        panels_loader=_fake_panels_loader,
    )

    assert state.equity_start_of_day == 12_000_000.0


def test_noop_path_returns_noop(tmp_path):
    """When there is no signal and no drift the tick returns 'NOOP'."""
    today = _weekday_market_hours()
    state = TraderState(
        last_rebalance_date=today.date().isoformat(),
        equity_start_of_day=10_000_000.0,
    )
    broker = FakeBroker()
    params = TraderParams(use_take_profit=False)

    result = run_trader_tick(
        broker=broker, state=state, params=params,
        universe_codes=[],
        log=_log(),
        state_path=tmp_path / "state.json",
        now=today,
        panels_loader=_fake_panels_loader,
    )

    assert result == "NOOP"
    assert state.halted is False
