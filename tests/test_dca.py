import numpy as np
import pandas as pd

from config import FixedWeightConfig
from engine.dca_backtest import run_dca, run_lump_sum, _allocate
from metrics.dca import summarize_dca, xirr


def _cfg(**kw):
    base = dict(commission_rate=0.0, slippage_rate=0.0)
    base.update(kw)
    return FixedWeightConfig(**base)


def _panels(n=260, r=0.001):
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    close = pd.DataFrame({"A": 100.0 * (1 + r) ** np.arange(n)}, index=idx)
    return close, close.copy()


def test_xirr_known_values():
    # 1년 뒤 10% → IRR 10%
    r = xirr([(pd.Timestamp("2020-01-01"), -100.0),
              (pd.Timestamp("2021-01-01"), 110.0)])
    assert abs(r - 0.10) < 1e-3
    # 두 번 납입 후 원금 회수 → 0%
    r0 = xirr([(pd.Timestamp("2020-01-01"), -100.0),
               (pd.Timestamp("2020-07-01"), -100.0),
               (pd.Timestamp("2021-01-01"), 200.0)])
    assert abs(r0) < 1e-6
    assert xirr([(pd.Timestamp("2020-01-01"), -100.0)]) == 0.0


def test_allocate_fills_deficit_first():
    # 부족분(A 20, B 80)에 비례 배분 → 납입 후 정확히 50/50
    alloc = _allocate(100.0, {"A": 80.0, "B": 20.0}, {"A": 0.5, "B": 0.5})
    assert abs(alloc["A"] - 20.0) < 1e-9 and abs(alloc["B"] - 80.0) < 1e-9
    alloc2 = _allocate(100.0, {"A": 50.0, "B": 50.0}, {"A": 0.7, "B": 0.3})
    assert abs(alloc2["A"] - 90.0) < 1e-9 and abs(alloc2["B"] - 10.0) < 1e-9


def test_dca_contributions_and_invested():
    close, opens = _panels()
    value, invested, trades, contribs = run_dca(close, opens, {"A": 1.0}, _cfg(),
                                                monthly_amount=100_000.0)
    months = len(close.resample("ME").first())
    assert len(contribs) == months
    assert invested.iloc[-1] == months * 100_000.0
    assert all(t["reason"] == "dca" for t in trades)
    # 첫 매수는 둘째 거래일
    assert trades[0]["date"] == close.index[1]
    # 상승 자산 → 평가액 > 납입액
    assert value.iloc[-1] > invested.iloc[-1]


def test_dca_flat_price_equals_invested():
    close, opens = _panels(r=0.0)
    value, invested, _, _ = run_dca(close, opens, {"A": 1.0}, _cfg(),
                                    monthly_amount=50_000.0)
    assert abs(value.iloc[-1] - invested.iloc[-1]) < 1e-6


def test_lump_sum_single_buy():
    close, opens = _panels()
    value, invested, trades, contribs = run_lump_sum(close, opens, {"A": 1.0},
                                                     _cfg(), 1_200_000.0)
    assert len(trades) == 1 and len(contribs) == 1
    assert invested.iloc[-1] == 1_200_000.0
    expected = 1_200_000.0 * close["A"].iloc[-1] / close["A"].iloc[1]
    assert abs(value.iloc[-1] - expected) < 1e-6


def test_summarize_dca_fields():
    close, opens = _panels()
    value, invested, _, contribs = run_dca(close, opens, {"A": 1.0}, _cfg(),
                                           monthly_amount=100_000.0)
    s = summarize_dca(value, invested, contribs)
    assert s["total_invested"] == invested.iloc[-1]
    assert abs(s["profit_ratio"] - (s["final_value"] / s["total_invested"] - 1)) < 1e-12
    assert s["irr"] > 0 and s["max_drawdown"] <= 0
    assert s["num_contributions"] == len(contribs)


def test_invested_counts_only_executed_cash():
    close, opens = _panels()
    value, invested, _, _ = run_dca(close, opens, {"A": 1.0}, _cfg(),
                                    monthly_amount=100_000.0)
    # 첫날: 신호만 발생, 아직 매수 전 → 납입 0, 평가 0
    assert invested.iloc[0] == 0.0 and value.iloc[0] == 0.0
    # 둘째날: 체결 → 납입 10만원, 평가 10만원 (비용 0)
    assert invested.iloc[1] == 100_000.0
    assert abs(value.iloc[1] - 100_000.0) < 1e-6
    s = summarize_dca(value, invested, [(close.index[1], 100_000.0)])
    assert s["worst_pnl_ratio"] > -0.5
