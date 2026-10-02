"""적립식(DCA) 성과 지표. 자산곡선 기반 지표(CAGR 등)는 납입이 섞여 왜곡되므로
현금흐름 기반 지표(IRR)와 '납입 대비 평가' 지표를 쓴다."""
from datetime import date

import numpy as np
import pandas as pd


def xirr(cashflows, guess: float = 0.1, tol: float = 1e-9) -> float:
    """비정기 현금흐름의 연환산 내부수익률. cashflows: [(date, amount)], 납입은 음수,
    최종 평가액은 양수. 수렴 실패 시 이분법으로 보정."""
    if len(cashflows) < 2:
        return 0.0
    cf = sorted(cashflows, key=lambda x: x[0])
    t0 = pd.Timestamp(cf[0][0])
    years = np.array([(pd.Timestamp(d) - t0).days / 365.25 for d, _ in cf])
    amts = np.array([a for _, a in cf], dtype=float)
    if not (amts.min() < 0 < amts.max()):
        return 0.0

    def npv(r):
        return float(np.sum(amts / (1.0 + r) ** years))

    lo, hi = -0.9999, 10.0
    f_lo, f_hi = npv(lo), npv(hi)
    if f_lo * f_hi > 0:
        return 0.0
    for _ in range(300):
        mid = (lo + hi) / 2.0
        f_mid = npv(mid)
        if abs(f_mid) < tol or (hi - lo) < tol:
            return float(mid)
        if f_lo * f_mid < 0:
            hi, f_hi = mid, f_mid
        else:
            lo, f_lo = mid, f_mid
    return float((lo + hi) / 2.0)


def summarize_dca(value: pd.Series, invested: pd.Series, contributions: list) -> dict:
    """value: 일별 평가금액, invested: 일별 누적 납입액, contributions: [(date, amount>0)]"""
    final_value = float(value.iloc[-1])
    total_in = float(invested.iloc[-1])
    pnl_ratio = value / invested.replace(0, np.nan) - 1.0
    dd = value / value.cummax() - 1.0
    cfs = [(d, -a) for d, a in contributions] + [(value.index[-1], final_value)]
    years = (value.index[-1] - value.index[0]).days / 365.25
    return {
        "total_invested": total_in,
        "final_value": final_value,
        "profit": final_value - total_in,
        "profit_ratio": final_value / total_in - 1.0 if total_in else 0.0,
        "irr": xirr(cfs),
        "max_drawdown": float(dd.min()),
        "worst_pnl_ratio": float(pnl_ratio.min()),
        "worst_pnl_date": pnl_ratio.idxmin().date() if pnl_ratio.notna().any() else None,
        "months_underwater": int((pnl_ratio < 0).resample("ME").last().sum()),
        "years": years,
        "num_contributions": len(contributions),
    }


def yearly_dca_table(value: pd.Series, invested: pd.Series) -> pd.DataFrame:
    """연말 기준 누적 납입·평가·손익률."""
    v = value.resample("YE").last()
    i = invested.resample("YE").last()
    out = pd.DataFrame({"invested": i, "value": v})
    out["pnl_ratio"] = out["value"] / out["invested"] - 1.0
    out.index = out.index.year
    return out
