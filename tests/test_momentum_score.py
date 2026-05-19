import numpy as np
import pandas as pd
from strategy.momentum import momentum_score, _price_asof


def _series():
    idx = pd.date_range("2020-01-01", "2021-06-30", freq="D")
    # 가격: 100에서 매일 +0.1, 단조 증가
    return pd.Series(100.0 + 0.1 * np.arange(len(idx)), index=idx)


def test_price_asof_returns_last_value_on_or_before():
    s = _series()
    assert _price_asof(s, pd.Timestamp("2020-01-01")) == 100.0
    # 2020-01-11 = 인덱스 10 → 100 + 1.0
    assert _price_asof(s, pd.Timestamp("2020-01-11")) == 101.0


def test_price_asof_nan_when_before_start():
    s = _series()
    assert np.isnan(_price_asof(s, pd.Timestamp("2019-01-01")))


def test_momentum_score_12_1():
    s = _series()
    as_of = pd.Timestamp("2021-06-30")
    p_recent = _price_asof(s, as_of - pd.DateOffset(months=1))
    p_old = _price_asof(s, as_of - pd.DateOffset(months=12))
    expected = p_recent / p_old - 1.0
    assert momentum_score(s, as_of, 12, 1) == expected


def test_momentum_score_nan_when_insufficient_history():
    s = _series()
    # 시작 직후 → 12개월 전 데이터 없음
    assert np.isnan(momentum_score(s, pd.Timestamp("2020-02-01"), 12, 1))
