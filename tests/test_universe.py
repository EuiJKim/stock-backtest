import pandas as pd
from data.universe import match_codes


def _listing():
    return pd.DataFrame({
        "Symbol": ["360750", "381170", "999999"],
        "Name": ["TIGER 미국S&P500", "TIGER 미국테크TOP10 INDXX",
                 "기타 ETF"],
    })


def test_match_exact_ignoring_spaces():
    out = match_codes(["TIGER 미국S&P500"], _listing())
    assert out["TIGER 미국S&P500"] == "360750"


def test_match_handles_space_differences():
    out = match_codes(["TIGER 미국테크TOP10INDXX"], _listing())
    assert out["TIGER 미국테크TOP10INDXX"] == "381170"


def test_unmatched_name_returns_none():
    out = match_codes(["존재하지않는ETF"], _listing())
    assert out["존재하지않는ETF"] is None
