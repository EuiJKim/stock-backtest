import numpy as np
import pandas as pd
from strategy.momentum import compute_scores, select_top_k, target_weights


def test_compute_scores_per_column():
    idx = pd.date_range("2020-01-01", "2021-06-30", freq="D")
    n = len(idx)
    panel = pd.DataFrame({
        "A": 100.0 + 0.2 * np.arange(n),   # 가파른 상승
        "B": 100.0 + 0.05 * np.arange(n),  # 완만한 상승
    }, index=idx)
    scores = compute_scores(panel, pd.Timestamp("2021-06-30"), 12, 1)
    assert set(scores.keys()) == {"A", "B"}
    assert scores["A"] > scores["B"]


def test_select_top_k_drops_nan_and_orders_desc():
    scores = {"A": 0.3, "B": np.nan, "C": 0.5, "D": 0.1}
    assert select_top_k(scores, 2) == ["C", "A"]


def test_target_weights_equal_when_absolute_off():
    scores = {"A": 0.3, "C": 0.5}
    w = target_weights(["C", "A"], scores, top_k=3, use_absolute=False,
                        abs_threshold=0.0)
    assert w == {"C": 1 / 3, "A": 1 / 3}  # 슬롯 3개 중 2개만 채움 → 나머지 현금


def test_target_weights_absolute_filter_drops_negative():
    scores = {"A": 0.3, "C": -0.1}
    w = target_weights(["C", "A"], scores, top_k=3, use_absolute=True,
                        abs_threshold=0.0)
    assert w == {"A": 1 / 3}  # C는 절대모멘텀 음수 → 현금
