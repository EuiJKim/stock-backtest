import os

import pandas as pd


def _cache_path(cache_dir: str, code: str) -> str:
    return os.path.join(cache_dir, f"{code}.csv")


def fdr_fetch(code: str, start: str, end: str) -> pd.DataFrame:
    import FinanceDataReader as fdr
    return fdr.DataReader(code, start, end)


def load_prices(code, start, end, cache_dir, fetch_fn=fdr_fetch) -> pd.DataFrame:
    path = _cache_path(cache_dir, code)
    if os.path.exists(path):
        df = pd.read_csv(path, index_col=0, parse_dates=True)
    else:
        df = fetch_fn(code, start, end)
        os.makedirs(cache_dir, exist_ok=True)
        df.to_csv(path)
    mask = (df.index >= pd.Timestamp(start)) & (df.index <= pd.Timestamp(end))
    return df.loc[mask]


def build_panels(codes, start, end, cache_dir, fetch_fn=fdr_fetch):
    closes, opens = {}, {}
    for code in codes:
        df = load_prices(code, start, end, cache_dir, fetch_fn)
        closes[code] = df["Close"]
        opens[code] = df["Open"]
    close_panel = pd.DataFrame(closes).sort_index()
    open_panel = pd.DataFrame(opens).reindex(close_panel.index)
    return close_panel, open_panel
