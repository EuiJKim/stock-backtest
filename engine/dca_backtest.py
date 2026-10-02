"""적립식(DCA) 고정 비중 백테스트.

매월 첫 거래일 종가에 '납입 신호' → 다음 거래일 시가에 매수 (기존 엔진과 동일한 look-ahead 규칙).
매수 방식:
  - rebalance_with_cash=True : 새 납입금을 목표 비중 대비 부족한 자산에 우선 배분 (매도 없음)
  - rebalance_with_cash=False: 납입금을 목표 비중대로 그대로 나눠 매수
비교용 거치식(lump sum)은 같은 총액을 첫 매수일에 한 번에 투입한다.
"""
import numpy as np
import pandas as pd

from engine.backtest import _buy
from engine.portfolio import Portfolio
from strategy.fixed_weight import normalize_weights, rebalance_flags


def _allocate(cash: float, pos_value: dict, target: dict) -> dict:
    """납입금 cash를 '목표 비중까지 가장 부족한 자산부터' 채우는 배분 (매도 없음)."""
    total_after = sum(pos_value.values()) + cash
    desired = {c: target[c] * total_after for c in target}
    deficit = {c: max(desired[c] - pos_value.get(c, 0.0), 0.0) for c in target}
    s = sum(deficit.values())
    if s <= 0:
        return {c: cash * target[c] for c in target}
    alloc = {c: cash * deficit[c] / s for c in target}
    return alloc


def run_dca(close_panel: pd.DataFrame, open_panel: pd.DataFrame, weights: dict,
            config, monthly_amount: float, rebalance_with_cash: bool = True,
            initial_amount: float = 0.0):
    """반환: (value: Series, invested: Series, trades: list, contributions: list[(date, amt)])"""
    target = normalize_weights(weights)
    codes = list(target)
    avail = close_panel[codes].dropna(how="any")
    if avail.empty:
        raise ValueError("no overlapping price history for all assets")
    dates = avail.index
    close_panel = close_panel.loc[dates]
    open_panel = open_panel.reindex(dates)

    pf = Portfolio(cash=0.0)
    trades, contributions = [], []
    value, invested = {}, {}
    cum_in = 0.0
    flags = rebalance_flags(dates, "monthly")
    pending_cash = 0.0

    for i, d in enumerate(dates):
        opens, closes = open_panel.loc[d], close_panel.loc[d]
        # 1) 전일 납입 신호 → 오늘 시가 매수
        if pending_cash > 0:
            px = {c: (opens.get(c, np.nan) if np.isfinite(opens.get(c, np.nan))
                      else closes[c]) for c in codes}
            pos_value = {c: pf.positions[c].shares * px[c] if c in pf.positions else 0.0
                         for c in codes}
            alloc = (_allocate(pending_cash, pos_value, target) if rebalance_with_cash
                     else {c: pending_cash * target[c] for c in codes})
            pf.cash += pending_cash
            for c, amt in alloc.items():
                if amt <= 0:
                    continue
                prev = pf.positions.get(c)
                before_shares = prev.shares if prev else 0.0
                _buy(pf, c, px[c], amt, config, trades, d, "dca")
                if prev is not None:  # _buy는 포지션을 덮어쓰므로 수량 합산
                    pf.positions[c].shares += before_shares
                    pf.positions[c].entry_price = prev.entry_price
            pending_cash = 0.0
        # 2) 종가 평가 (누적 납입은 실제 매수 체결된 금액 기준)
        value[d] = pf.equity({c: closes.get(c, np.nan) for c in codes})
        invested[d] = cum_in
        # 3) 납입 신호 (매월 첫 거래일, 마지막 날엔 체결일이 없으므로 생략)
        if flags.loc[d] and i < len(dates) - 1:
            amt = monthly_amount + (initial_amount if i == 0 else 0.0)
            if amt > 0:
                pending_cash = amt
                cum_in += amt
                contributions.append((dates[i + 1], amt))

    return (pd.Series(value).sort_index(), pd.Series(invested).sort_index(),
            trades, contributions)


def run_lump_sum(close_panel, open_panel, weights, config, total_amount: float):
    """비교용 거치식: 첫 거래일 신호 → 둘째 날 시가에 전액 매수."""
    return run_dca(close_panel, open_panel, weights, config,
                   monthly_amount=0.0, initial_amount=total_amount)
