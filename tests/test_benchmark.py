import numpy as np
import pandas as pd
from engine.backtest import benchmark_curve


def test_benchmark_is_normalized_buy_and_hold():
    idx = pd.date_range("2020-01-01", periods=4, freq="B")
    s = pd.Series([100.0, 110.0, 90.0, 120.0], index=idx)
    curve = benchmark_curve(s, initial_capital=1_000_000.0)
    assert curve.iloc[0] == 1_000_000.0
    assert curve.iloc[1] == 1_100_000.0
    assert curve.iloc[-1] == 1_200_000.0


def test_benchmark_drops_leading_nan():
    idx = pd.date_range("2020-01-01", periods=3, freq="B")
    s = pd.Series([np.nan, 100.0, 150.0], index=idx)
    curve = benchmark_curve(s, initial_capital=1_000_000.0)
    assert curve.iloc[0] == 1_000_000.0
    assert curve.iloc[-1] == 1_500_000.0
