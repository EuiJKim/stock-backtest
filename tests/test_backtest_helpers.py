import pandas as pd
from config import BacktestConfig
from engine.portfolio import Portfolio, Position
from engine.backtest import _buy, _sell, _rebalance


def _cfg():
    return BacktestConfig(commission_rate=0.0, slippage_rate=0.0)


def test_buy_creates_position_and_deducts_cash():
    pf = Portfolio(cash=1_000_000.0)
    trades = []
    _buy(pf, "A", price=1000.0, notional=300_000.0, config=_cfg(),
         trades=trades, date=pd.Timestamp("2020-01-02"), reason="rebalance")
    assert pf.positions["A"].shares == 300.0
    assert pf.positions["A"].entry_price == 1000.0
    assert pf.cash == 700_000.0
    assert trades[0]["side"] == "BUY"


def test_sell_closes_position_and_adds_cash():
    pf = Portfolio(cash=0.0)
    pf.positions["A"] = Position(shares=100.0, entry_price=1000.0)
    trades = []
    _sell(pf, "A", price=1200.0, config=_cfg(), trades=trades,
          date=pd.Timestamp("2020-02-01"), reason="take_profit")
    assert "A" not in pf.positions
    assert pf.cash == 120_000.0
    assert trades[0]["side"] == "SELL" and trades[0]["reason"] == "take_profit"


def test_cost_reduces_proceeds_and_cash():
    cfg = BacktestConfig(commission_rate=0.001, slippage_rate=0.0)
    pf = Portfolio(cash=0.0)
    pf.positions["A"] = Position(shares=100.0, entry_price=1000.0)
    _sell(pf, "A", price=1000.0, config=cfg, trades=[],
          date=pd.Timestamp("2020-02-01"), reason="rebalance")
    # 100,000 - 0.1% = 100,000 - 100
    assert pf.cash == 99_900.0


def test_rebalance_resets_to_target_weights_at_open():
    cfg = _cfg()
    pf = Portfolio(cash=0.0)
    pf.positions["OLD"] = Position(shares=100.0, entry_price=1000.0)
    opens = pd.Series({"OLD": 1000.0, "A": 500.0, "B": 250.0})
    trades = []
    _rebalance(pf, {"A": 1 / 3, "B": 1 / 3}, opens, cfg, trades,
               pd.Timestamp("2020-03-02"))
    # OLD 매도 → 현금 100,000. A에 1/3, B에 1/3 투입.
    assert "OLD" not in pf.positions
    assert round(pf.positions["A"].shares, 6) == round((100_000 / 3) / 500.0, 6)
    assert round(pf.positions["B"].shares, 6) == round((100_000 / 3) / 250.0, 6)


def test_rebalance_entry_price_uses_rebalance_fill_not_stale():
    """Fix 1 regression: entry_price must equal the rebalance fill (open) price,
    not the stale pre-rebalance entry_price."""
    cfg = _cfg()
    pf = Portfolio(cash=0.0)
    # Hold A with a stale entry_price of 1000
    pf.positions["A"] = Position(shares=100.0, entry_price=1000.0)
    opens = pd.Series({"A": 2000.0})
    trades = []
    _rebalance(pf, {"A": 1.0}, opens, cfg, trades, pd.Timestamp("2020-03-02"))
    # After rebalance, A's entry_price must be 2000 (the rebalance open price),
    # not the stale 1000.
    assert pf.positions["A"].entry_price == 2000.0
