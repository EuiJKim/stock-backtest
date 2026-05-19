import pandas as pd


def _norm(s: str) -> str:
    return str(s).replace(" ", "")


def match_codes(names, listing_df: pd.DataFrame) -> dict:
    """ETF 이름 리스트 → {이름: 종목코드 or None}. 공백 무시 매칭."""
    norm_names = listing_df["Name"].map(_norm)
    out = {}
    for name in names:
        target = _norm(name)
        exact = listing_df[norm_names == target]
        if len(exact) > 0:
            out[name] = str(exact.iloc[0]["Symbol"])
            continue
        contains = listing_df[norm_names.str.contains(target, regex=False)]
        out[name] = str(contains.iloc[0]["Symbol"]) if len(contains) else None
    return out


def load_listing() -> pd.DataFrame:
    import FinanceDataReader as fdr
    return fdr.StockListing("ETF/KR")
