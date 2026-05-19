import pandas as pd
from data.loader import load_prices, build_panels


def _fake_fetch(code, start, end):
    idx = pd.date_range("2020-01-01", periods=5, freq="B")
    base = 100.0 if code == "AAA" else 200.0
    return pd.DataFrame({"Open": base, "Close": base + 1}, index=idx)


def test_load_prices_filters_date_range(tmp_path):
    df = load_prices("AAA", "2020-01-02", "2020-01-03",
                     cache_dir=str(tmp_path), fetch_fn=_fake_fetch)
    assert df.index.min() >= pd.Timestamp("2020-01-02")
    assert df.index.max() <= pd.Timestamp("2020-01-03")


def test_load_prices_writes_and_reads_cache(tmp_path):
    load_prices("AAA", "2020-01-01", "2020-01-31",
                cache_dir=str(tmp_path), fetch_fn=_fake_fetch)
    assert (tmp_path / "AAA.csv").exists()

    def _boom(*a, **k):
        raise AssertionError("fetch must not be called when cache exists")

    df = load_prices("AAA", "2020-01-01", "2020-01-31",
                     cache_dir=str(tmp_path), fetch_fn=_boom)
    assert len(df) == 5


def test_build_panels_aligns_close_and_open(tmp_path):
    close, opens = build_panels(["AAA", "BBB"], "2020-01-01", "2020-01-31",
                                cache_dir=str(tmp_path), fetch_fn=_fake_fetch)
    assert list(close.columns) == ["AAA", "BBB"]
    assert close.index.equals(opens.index)
    assert close.loc[close.index[0], "AAA"] == 101.0
