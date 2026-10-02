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


def test_cli_dca_mode_offline(tmp_path):
    idx = pd.date_range("2021-01-01", periods=300, freq="B")
    n = len(idx)
    cache = tmp_path / "cache"
    cache.mkdir()
    for code, r in [("133690", 0.002), ("360750", 0.001)]:
        px = 100.0 * (1 + r) ** np.arange(n)
        df = pd.DataFrame({"Open": px, "Close": px}, index=idx)
        df.index.name = "Date"
        df.to_csv(cache / f"{code}.csv")
    out = run_portfolio.main(["--offline", "--monthly", "100000",
                              "--codes", "133690:1",
                              "--cache-dir", str(cache),
                              "--out", str(tmp_path / "out")])
    assert any(k.startswith("적립식") for k in out)
    assert "거치식 (동일 총액)" in out
    assert (tmp_path / "out" / "summary.html").exists()
