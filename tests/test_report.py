import numpy as np
import pandas as pd
from report.report import format_summary_table, format_yearly_table, write_report


def test_format_summary_table_contains_metrics():
    summary = {"total_return": 0.42, "cagr": 0.15, "max_drawdown": -0.2,
               "sharpe": 1.1, "sortino": 1.4, "volatility": 0.18,
               "num_trades": 12}
    txt = format_summary_table(summary)
    assert "CAGR" in txt
    assert "15.00%" in txt
    assert "12" in txt


def test_yearly_table_in_write_report(tmp_path):
    # Build a curve that exactly doubles over calendar year 2020 (Jan 1 → Dec 31)
    # then stays flat in 2021 — the 2020 yearly return should be ~+100%.
    idx_2020 = pd.date_range("2020-01-01", "2020-12-31", freq="B")
    idx_2021 = pd.date_range("2021-01-01", "2021-12-31", freq="B")
    n_2020 = len(idx_2020)
    n_2021 = len(idx_2021)
    # linearly ramp from 1_000_000 → 2_000_000 over 2020, hold at 2_000_000 in 2021
    vals_2020 = np.linspace(1_000_000.0, 2_000_000.0, n_2020)
    vals_2021 = np.full(n_2021, 2_000_000.0)
    idx = idx_2020.append(idx_2021)
    vals = np.concatenate([vals_2020, vals_2021])
    strat = pd.Series(vals, index=idx)
    trades = []
    summary = {"total_return": 1.0, "cagr": 0.5, "max_drawdown": -0.01,
               "sharpe": 1.0, "sortino": 1.2, "volatility": 0.1,
               "num_trades": 0}
    text = write_report(strat, None, trades, summary, str(tmp_path))
    # The 2020 return is (2_000_000 / 1_000_000) - 1 = 100%; assert "100" appears
    assert "2020" in text
    assert "100" in text


def test_write_report_creates_files(tmp_path):
    idx = pd.date_range("2020-01-01", periods=50, freq="B")
    strat = pd.Series(1_000_000.0 * (1.0 + 0.001) ** np.arange(50), index=idx)
    bench = pd.Series(1_000_000.0 * (1.0 + 0.0005) ** np.arange(50), index=idx)
    trades = [{"date": idx[0], "code": "A", "side": "BUY", "shares": 1.0,
               "price": 100.0, "cost": 0.0, "reason": "rebalance"}]
    summary = {"total_return": 0.05, "cagr": 0.05, "max_drawdown": -0.01,
               "sharpe": 1.0, "sortino": 1.2, "volatility": 0.1,
               "num_trades": 1}
    out = write_report(strat, bench, trades, summary, str(tmp_path))
    assert (tmp_path / "equity_curve.png").exists()
    assert (tmp_path / "trades.csv").exists()
    assert (tmp_path / "summary.html").exists()
    assert "CAGR" in out
