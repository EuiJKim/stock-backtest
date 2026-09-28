import numpy as np
import pandas as pd
import pytest

import run_portfolio
from config import FixedWeightConfig
from report.compare import format_compare_table, format_yearly_compare


def test_parse_pairs():
    assert run_portfolio.parse_pairs("A:0.7, B:0.3") == {"A": 0.7, "B": 0.3}
    assert run_portfolio.parse_pairs("TIGER 미국S&P500:1") == {"TIGER 미국S&P500": 1.0}
    with pytest.raises(ValueError):
        run_portfolio.parse_pairs(":0.5")
    with pytest.raises(ValueError):
        run_portfolio.parse_pairs("")


def test_resolve_codes_offline_known():
    out = run_portfolio.resolve_codes(["TIGER 미국나스닥100"], offline=True)
    assert out == {"TIGER 미국나스닥100": "133690"}
    with pytest.raises(SystemExit):
        run_portfolio.resolve_codes(["없는 ETF"], offline=True)


def test_build_scenarios_and_tables(tmp_path):
    idx = pd.date_range("2021-01-01", periods=400, freq="B")
    n = len(idx)
    close = pd.DataFrame({
        "133690": 100.0 * (1.003) ** np.arange(n),
        "381180": 100.0 * (1.001) ** np.arange(n),
        "360750": 100.0 * (1.002) ** np.arange(n),
    }, index=idx)
    cfg = FixedWeightConfig(commission_rate=0.0, slippage_rate=0.0)
    names = {"133690": "NDX", "381180": "SOX", "360750": "SPX"}
    curves, summaries, wh = run_portfolio.build_scenarios(
        close, close.copy(), {"133690": 0.7, "381180": 0.3}, cfg, names,
        "360750", ["monthly", "none"])
    assert set(curves) == {"70/30 monthly", "70/30 none", "100% NDX",
                           "100% SOX", "Bench SPX"}
    assert list(wh.columns) == ["NDX", "SOX"]
    table = format_compare_table(summaries)
    assert "70/30 monthly" in table and "CAGR" in table
    yearly = format_yearly_compare(curves)
    assert "2021" in yearly and "2022" in yearly
