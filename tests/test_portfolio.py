import numpy as np
from engine.portfolio import Portfolio, Position


def test_equity_cash_only():
    pf = Portfolio(cash=1_000_000.0)
    assert pf.equity({}) == 1_000_000.0


def test_equity_with_positions():
    pf = Portfolio(cash=500_000.0)
    pf.positions["X"] = Position(shares=10.0, entry_price=10_000.0)
    # 종가 12,000 → 평가 120,000 + 현금 500,000
    assert pf.equity({"X": 12_000.0}) == 620_000.0


def test_equity_ignores_nan_price():
    pf = Portfolio(cash=100_000.0)
    pf.positions["X"] = Position(shares=10.0, entry_price=10_000.0)
    assert pf.equity({"X": np.nan}) == 100_000.0
