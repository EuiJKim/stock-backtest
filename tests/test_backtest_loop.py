import numpy as np
import pandas as pd
from config import BacktestConfig
from engine.backtest import run_backtest, _first_trading_day_of_month


def test_first_trading_day_flags():
    dates = pd.to_datetime(["2020-01-02", "2020-01-03", "2020-02-03",
                            "2020-02-04", "2020-03-02"])
    flags = _first_trading_day_of_month(dates)
    assert list(flags.values) == [True, False, True, False, True]


def _panels():
    # 18개월 일봉. A는 강한 상승, B는 횡보, C는 하락.
    idx = pd.date_range("2020-01-01", "2021-06-30", freq="B")
    n = len(idx)
    close = pd.DataFrame({
        "A": 100.0 * (1.0 + 0.0015) ** np.arange(n),
        "B": np.full(n, 100.0),
        "C": 100.0 * (1.0 - 0.0010) ** np.arange(n),
    }, index=idx)
    # 시가 = 전일 종가 근사 (간단화: 종가와 동일하게 둠)
    return close, close.copy()


def test_run_backtest_returns_curve_and_trades():
    close, opens = _panels()
    cfg = BacktestConfig(top_k=1, use_take_profit=False,
                         use_absolute_momentum=False,
                         commission_rate=0.0, slippage_rate=0.0,
                         initial_capital=1_000_000.0)
    curve, trades = run_backtest(close, opens, cfg)
    assert isinstance(curve, pd.Series)
    assert curve.index.is_monotonic_increasing
    assert curve.iloc[0] == 1_000_000.0
    # 강한 상승 A를 골라야 하므로 최종 자산 > 초기 자산
    assert curve.iloc[-1] > curve.iloc[0]
    assert len(trades) > 0
    assert all(t["side"] in ("BUY", "SELL") for t in trades)


def test_take_profit_triggers_sell_with_reason():
    close, opens = _panels()
    cfg = BacktestConfig(top_k=1, use_take_profit=True,
                         take_profit_pct=0.05,
                         use_absolute_momentum=False,
                         commission_rate=0.0, slippage_rate=0.0)
    _, trades = run_backtest(close, opens, cfg)
    assert any(t["reason"] == "take_profit" for t in trades)


def test_absolute_momentum_goes_to_cash_when_all_negative():
    idx = pd.date_range("2020-01-01", "2021-06-30", freq="B")
    n = len(idx)
    # 모든 종목 하락 → 절대 모멘텀 음수 → 전량 현금 유지
    close = pd.DataFrame({
        "A": 100.0 * (1.0 - 0.001) ** np.arange(n),
        "B": 100.0 * (1.0 - 0.002) ** np.arange(n),
    }, index=idx)
    cfg = BacktestConfig(top_k=2, use_take_profit=False,
                         use_absolute_momentum=True,
                         absolute_momentum_threshold=0.0,
                         commission_rate=0.0, slippage_rate=0.0,
                         initial_capital=1_000_000.0)
    curve, _ = run_backtest(close, close.copy(), cfg)
    # 현금만 보유 → 자산곡선 평탄
    assert curve.iloc[-1] == 1_000_000.0
