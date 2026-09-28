"""고정 비중(정적 배분) 포트폴리오 전략 — 순수 함수만 둔다.

예: 나스닥100 70% / 필라델피아반도체 30%.
리밸런싱 규칙:
  - "none"      : 최초 1회 매수 후 보유 (비중 드리프트 허용)
  - "monthly"   : 매월 첫 거래일
  - "quarterly" : 매 분기 첫 거래일 (1·4·7·10월)
  - "yearly"    : 매년 첫 거래일
추가로 band(예: 0.05)를 주면 목표 비중에서 5%p 이상 벗어난 날에도 리밸런싱 신호.
"""
import numpy as np
import pandas as pd

REBALANCE_RULES = ("none", "monthly", "quarterly", "yearly")


def normalize_weights(weights: dict) -> dict:
    """비중 합이 1이 되도록 정규화. 음수·빈 입력은 거부."""
    if not weights:
        raise ValueError("weights must not be empty")
    if any(w < 0 for w in weights.values()):
        raise ValueError("weights must be non-negative")
    total = float(sum(weights.values()))
    if total <= 0:
        raise ValueError("weights must sum to a positive number")
    return {k: float(v) / total for k, v in weights.items()}


def rebalance_flags(dates, rule: str) -> pd.Series:
    """각 날짜가 리밸런싱 신호일인지 표시. 첫 날짜는 항상 True(최초 매수)."""
    if rule not in REBALANCE_RULES:
        raise ValueError(f"unknown rebalance rule: {rule}")
    dates = pd.DatetimeIndex(dates)
    flags = []
    seen = set()
    for i, d in enumerate(dates):
        if rule == "none":
            key = "once"
        elif rule == "monthly":
            key = (d.year, d.month)
        elif rule == "quarterly":
            key = (d.year, (d.month - 1) // 3)
        else:  # yearly
            key = d.year
        flags.append(i == 0 or key not in seen)
        seen.add(key)
    return pd.Series(flags, index=dates)


def current_weights(positions_value: dict, cash: float) -> dict:
    """보유 평가금액·현금 → 현재 비중."""
    total = cash + sum(v for v in positions_value.values() if np.isfinite(v))
    if total <= 0:
        return {k: 0.0 for k in positions_value}
    return {k: (v / total if np.isfinite(v) else 0.0)
            for k, v in positions_value.items()}


def band_breached(weights_now: dict, target: dict, band: float) -> bool:
    """어느 한 자산이라도 목표 비중에서 band(절대값, %p) 이상 벗어났는가."""
    if band is None or band <= 0:
        return False
    for code, w in target.items():
        if abs(weights_now.get(code, 0.0) - w) >= band:
            return True
    return False
