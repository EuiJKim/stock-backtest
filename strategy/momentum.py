import numpy as np
import pandas as pd


def _price_asof(series: pd.Series, date: pd.Timestamp) -> float:
    """date 이전(포함) 마지막 유효 가격. 없으면 NaN."""
    s = series.dropna()
    if s.empty:
        return np.nan
    idx = s.index[s.index <= date]
    if len(idx) == 0:
        return np.nan
    return float(s.loc[idx[-1]])


def momentum_score(prices: pd.Series, as_of, lookback_months: int,
                    skip_months: int) -> float:
    """(t - skip) 가격 / (t - lookback) 가격 - 1. 데이터 부족 시 NaN."""
    as_of = pd.Timestamp(as_of)
    p_recent = _price_asof(prices, as_of - pd.DateOffset(months=skip_months))
    p_old = _price_asof(prices, as_of - pd.DateOffset(months=lookback_months))
    if not np.isfinite(p_recent) or not np.isfinite(p_old) or p_old == 0:
        return np.nan
    return p_recent / p_old - 1.0
