"""고정 비중 포트폴리오 일봉 루프.

기존 `engine.backtest`와 같은 규칙을 따른다:
  - 신호는 종가에 산출, 체결은 **다음 거래일 시가** (look-ahead 방지)
  - 매수·매도 각각 수수료+슬리피지 비용 적용
  - 평가금액은 매일 종가 기준
"""
import numpy as np
import pandas as pd

from engine.backtest import _buy, _sell
from engine.portfolio import Portfolio
from strategy.fixed_weight import (band_breached, current_weights,
                                   normalize_weights, rebalance_flags)


def _all_available(row: pd.Series, codes) -> bool:
    return all(np.isfinite(row.get(c, np.nan)) and row.get(c) > 0
               for c in codes)


def _rebalance_to_target(pf, target, opens, config, trades, date, reason):
    """전량 매도 후 목표 비중으로 재매수 (단순·보수적)."""
    for code in list(pf.positions):
        _sell(pf, code, opens.get(code, np.nan), config, trades, date, reason)
    investable = pf.cash
    for code, w in target.items():
        px = opens.get(code, np.nan)
        if np.isfinite(px) and px > 0:
            _buy(pf, code, px, investable * w, config, trades, date, reason)


def run_fixed_weight(close_panel: pd.DataFrame, open_panel: pd.DataFrame,
                     weights: dict, config, rebalance: str = "monthly",
                     band: float = 0.0):
    """고정 비중 백테스트.

    weights  : {종목코드: 비중}, 합 1로 정규화됨
    rebalance: "none" | "monthly" | "quarterly" | "yearly"
    band     : 0이면 비활성. 예 0.05 → 목표 대비 5%p 이탈 시 추가 리밸런싱
    반환: (equity_curve, trades, weight_history: DataFrame)
    """
    target = normalize_weights(weights)
    codes = list(target)
    missing = [c for c in codes if c not in close_panel.columns]
    if missing:
        raise KeyError(f"price panel lacks columns: {missing}")

    # 모든 자산 가격이 존재하는 구간만 사용 (상장 전 구간 제외)
    avail = close_panel[codes].dropna(how="any")
    if avail.empty:
        raise ValueError("no overlapping price history for all assets")
    dates = avail.index
    close_panel = close_panel.loc[dates]
    open_panel = open_panel.reindex(dates)

    pf = Portfolio(cash=config.initial_capital)
    trades = []
    equity = {}
    weight_hist = {}
    flags = rebalance_flags(dates, rebalance)
    pending = None  # None | reason(str)

    for d in dates:
        opens = open_panel.loc[d]
        closes = close_panel.loc[d]

        # 1) 전일 신호 → 오늘 시가 체결 (시가 결측이면 종가로 대체)
        if pending is not None and _all_available(closes, codes):
            px = {c: (opens.get(c, np.nan)
                      if np.isfinite(opens.get(c, np.nan)) else closes[c])
                  for c in codes}
            _rebalance_to_target(pf, target, px, config, trades, d, pending)
            pending = None

        # 2) 종가 평가
        prices = {c: closes.get(c, np.nan) for c in codes}
        equity[d] = pf.equity(prices)
        pos_val = {c: (pf.positions[c].shares * prices[c]
                       if c in pf.positions else 0.0) for c in codes}
        w_now = current_weights(pos_val, pf.cash)
        weight_hist[d] = w_now

        # 3) 다음 거래일 신호
        if flags.loc[d]:
            pending = "initial" if not pf.positions else "rebalance"
        elif pf.positions and band_breached(w_now, target, band):
            pending = "band"

    curve = pd.Series(equity).sort_index()
    weight_df = pd.DataFrame(weight_hist).T.sort_index()
    return curve, trades, weight_df
