import numpy as np
import pandas as pd
import pytest

from config import FixedWeightConfig
from engine.fixed_weight_backtest import run_fixed_weight
from strategy.fixed_weight import (band_breached, current_weights,
                                   normalize_weights, rebalance_flags)


def test_normalize_weights():
    assert normalize_weights({"A": 7, "B": 3}) == {"A": 0.7, "B": 0.3}
    with pytest.raises(ValueError):
        normalize_weights({})
    with pytest.raises(ValueError):
        normalize_weights({"A": -1, "B": 2})


def test_rebalance_flags_rules():
    dates = pd.to_datetime(["2020-01-02", "2020-01-03", "2020-02-03",
                            "2020-04-01", "2020-07-01", "2021-01-04"])
    assert list(rebalance_flags(dates, "none")) == [True] + [False] * 5
    assert list(rebalance_flags(dates, "monthly")) == [True, False, True,
                                                        True, True, True]
    assert list(rebalance_flags(dates, "quarterly")) == [True, False, False,
                                                          True, True, True]
    assert list(rebalance_flags(dates, "yearly")) == [True, False, False,
                                                       False, False, True]
    with pytest.raises(ValueError):
        rebalance_flags(dates, "weekly")


def test_current_weights_and_band():
    w = current_weights({"A": 80.0, "B": 20.0}, cash=0.0)
    assert w == {"A": 0.8, "B": 0.2}
    target = {"A": 0.7, "B": 0.3}
    assert band_breached(w, target, 0.05)
    assert not band_breached(w, target, 0.15)
    assert not band_breached(w, target, 0.0)


def _panels(n=300, ra=0.004, rb=0.0):
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    close = pd.DataFrame({
        "A": 100.0 * (1.0 + ra) ** np.arange(n),
        "B": 100.0 * (1.0 + rb) ** np.arange(n),
    }, index=idx)
    return close, close.copy()


def _cfg(**kw):
    base = dict(commission_rate=0.0, slippage_rate=0.0,
                initial_capital=1_000_000.0)
    base.update(kw)
    return FixedWeightConfig(**base)


def test_initial_buy_next_day_and_target_weights():
    close, opens = _panels()
    curve, trades, wh = run_fixed_weight(close, opens, {"A": 0.7, "B": 0.3},
                                         _cfg(), rebalance="none")
    # 첫날은 현금 보유 → 둘째 날 시가 체결 (look-ahead 방지)
    assert curve.iloc[0] == 1_000_000.0
    assert trades[0]["date"] == close.index[1]
    assert all(t["reason"] == "initial" for t in trades)
    assert len(trades) == 2
    # 체결 직후 비중은 목표와 일치
    w1 = wh.iloc[1]
    assert abs(w1["A"] - 0.7) < 1e-9 and abs(w1["B"] - 0.3) < 1e-9
    # 매수후보유 → A 상승으로 A 비중이 드리프트
    assert wh.iloc[-1]["A"] > 0.7


def test_monthly_rebalance_resets_weights():
    close, opens = _panels()
    curve, trades, wh = run_fixed_weight(close, opens, {"A": 0.7, "B": 0.3},
                                         _cfg(), rebalance="monthly")
    rebal_dates = sorted({t["date"] for t in trades if t["reason"] == "rebalance"})
    assert len(rebal_dates) >= 10
    for d in rebal_dates:
        assert abs(wh.loc[d, "A"] - 0.7) < 1e-9
    # 리밸런싱 사이 마지막 날에는 드리프트가 존재
    d_prev = wh.index[wh.index.get_loc(rebal_dates[1]) - 1]
    assert wh.loc[d_prev, "A"] > 0.7


def test_band_triggers_rebalance():
    close, opens = _panels(ra=0.01)
    _, trades, wh = run_fixed_weight(close, opens, {"A": 0.7, "B": 0.3},
                                     _cfg(), rebalance="none", band=0.03)
    assert any(t["reason"] == "band" for t in trades)
    # 밴드 이탈 상태가 감지된 다음 날 체결되어 비중이 복원됨
    assert wh["A"].max() < 0.7 + 0.03 + 0.02


def test_costs_reduce_equity():
    close, opens = _panels()
    w = {"A": 0.7, "B": 0.3}
    c0, _, _ = run_fixed_weight(close, opens, w, _cfg(), rebalance="monthly")
    c1, _, _ = run_fixed_weight(close, opens, w,
                                _cfg(commission_rate=0.001, slippage_rate=0.001),
                                rebalance="monthly")
    assert c1.iloc[-1] < c0.iloc[-1]


def test_single_asset_matches_price_return():
    close, opens = _panels()
    curve, _, _ = run_fixed_weight(close, opens, {"A": 1.0}, _cfg(),
                                   rebalance="none")
    expected = 1_000_000.0 * close["A"].iloc[-1] / close["A"].iloc[1]
    assert abs(curve.iloc[-1] - expected) < 1e-6


def test_trims_to_common_history():
    close, opens = _panels()
    close.loc[close.index[:50], "B"] = np.nan
    opens.loc[opens.index[:50], "B"] = np.nan
    curve, _, _ = run_fixed_weight(close, opens, {"A": 0.7, "B": 0.3}, _cfg())
    assert curve.index[0] == close.index[50]
    with pytest.raises(KeyError):
        run_fixed_weight(close, opens, {"A": 0.5, "Z": 0.5}, _cfg())


def test_rebalance_trades_only_the_difference():
    close, opens = _panels()
    cfg = _cfg(commission_rate=0.001, slippage_rate=0.0)
    _, trades, _ = run_fixed_weight(close, opens, {"A": 0.7, "B": 0.3}, cfg,
                                    rebalance="monthly")
    rebal = [t for t in trades if t["reason"] == "rebalance"]
    # A만 상승 → 매달 A 일부 매도, B 일부 매수 (전량 매도 아님)
    assert rebal and all(t["code"] == "A" for t in rebal if t["side"] == "SELL")
    assert all(t["code"] == "B" for t in rebal if t["side"] == "BUY")
    turnover = sum(t["shares"] * t["price"] for t in rebal)
    assert turnover < 0.2 * 1_000_000.0 * 12


def test_cash_never_negative_after_initial_buy():
    close, opens = _panels()
    cfg = _cfg(commission_rate=0.001, slippage_rate=0.001)
    curve, trades, wh = run_fixed_weight(close, opens, {"A": 0.7, "B": 0.3}, cfg,
                                         rebalance="monthly")
    # 비용을 포함해도 현금 비중이 음수가 되지 않음
    cash_w = 1.0 - wh[["A", "B"]].sum(axis=1)
    assert (cash_w > -1e-9).all()
