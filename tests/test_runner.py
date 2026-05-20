from datetime import date
import numpy as np
import pandas as pd

from live.runner import Order, Decision, decide
from live.state import Holding, TraderState, TraderParams


def _panel():
    idx = pd.date_range("2024-01-01", "2026-05-20", freq="B")
    n = len(idx)
    return pd.DataFrame({
        "A": 100.0 * (1.005) ** np.arange(n),
        "B": 100.0 * (1.001) ** np.arange(n),
        "C": 100.0 * (0.999) ** np.arange(n),
    }, index=idx)


def test_rebalance_when_new_month():
    panel = _panel()
    state = TraderState(mode="paper", cash=10_000_000.0, holdings={},
                        last_rebalance_date="")
    params = TraderParams(top_k=1, use_take_profit=False,
                          use_absolute_momentum=False)
    d = decide(panel, date(2026, 5, 20), {}, 10_000_000.0, params, state)
    assert d.action == "REBALANCE"
    # 상승률이 가장 큰 A가 선택되어야 함
    buy_codes = [o.code for o in d.orders if o.side == "BUY"]
    assert buy_codes == ["A"]


def test_noop_when_same_month_and_no_tp():
    panel = _panel()
    state = TraderState(mode="paper", cash=10_000_000.0,
                        last_rebalance_date="2026-05-01")
    params = TraderParams(top_k=1, use_take_profit=False)
    d = decide(panel, date(2026, 5, 20), {}, 10_000_000.0, params, state)
    assert d.action == "NOOP"
    assert d.orders == []


def test_take_profit_triggers_sell():
    panel = _panel()
    # 보유: A를 매우 낮은 진입가로 → 현재가 대비 5% 초과
    holdings = {"A": Holding(shares=10, entry_price=1.0,
                              bought_at="2024-01-01")}
    state = TraderState(mode="paper", holdings=holdings,
                        last_rebalance_date="2026-05-01")
    params = TraderParams(top_k=1, use_take_profit=True,
                          take_profit_pct=0.05)
    d = decide(panel, date(2026, 5, 20), holdings, 0.0, params, state)
    assert d.action == "TAKE_PROFIT"
    assert any(o.code == "A" and o.side == "SELL" for o in d.orders)


def test_rebalance_includes_sell_of_existing_holdings():
    panel = _panel()
    holdings = {"C": Holding(shares=10, entry_price=100.0)}
    state = TraderState(mode="paper", holdings=holdings,
                        last_rebalance_date="2026-04-01")
    params = TraderParams(top_k=1, use_take_profit=False,
                          use_absolute_momentum=False)
    d = decide(panel, date(2026, 5, 20), holdings,
               5_000_000.0, params, state)
    assert d.action == "REBALANCE"
    sides = {o.side for o in d.orders}
    assert "SELL" in sides and "BUY" in sides
