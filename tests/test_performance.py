import numpy as np
import pandas as pd
from metrics.performance import (total_return, cagr, max_drawdown,
                                 sharpe, summarize)


def test_total_return():
    s = pd.Series([100.0, 150.0])
    assert total_return(s) == 0.5


def test_cagr_two_years_doubling():
    idx = pd.to_datetime(["2020-01-01", "2022-01-01"])
    s = pd.Series([100.0, 400.0], index=idx)
    # 2년에 4배 → CAGR = 100%
    assert round(cagr(s), 4) == 1.0


def test_max_drawdown():
    s = pd.Series([100.0, 120.0, 60.0, 90.0])
    # 고점 120 → 저점 60 = -50%
    assert round(max_drawdown(s), 4) == -0.5


def test_sharpe_zero_when_no_volatility():
    idx = pd.date_range("2020-01-01", periods=10, freq="B")
    s = pd.Series(np.full(10, 100.0), index=idx)
    assert sharpe(s) == 0.0


def test_summarize_returns_expected_keys():
    idx = pd.date_range("2020-01-01", periods=300, freq="B")
    s = pd.Series(100.0 * (1.0 + 0.001) ** np.arange(300), index=idx)
    out = summarize(s, trades=[{"side": "BUY"}, {"side": "SELL"}])
    for key in ("total_return", "cagr", "max_drawdown", "sharpe",
                "sortino", "volatility", "num_trades"):
        assert key in out
    assert out["num_trades"] == 2
