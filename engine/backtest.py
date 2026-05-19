import numpy as np
import pandas as pd

from engine.costs import trade_cost
from engine.portfolio import Portfolio, Position
from strategy.momentum import compute_scores, select_top_k, target_weights


def _buy(pf, code, price, notional, config, trades, date, reason):
    if notional <= 0 or not np.isfinite(price) or price <= 0:
        return
    shares = notional / price
    cost = trade_cost(notional, config.commission_rate, config.slippage_rate)
    pf.cash -= notional + cost
    pf.positions[code] = Position(shares=shares, entry_price=price)
    trades.append({"date": date, "code": code, "side": "BUY",
                   "shares": shares, "price": price, "cost": cost,
                   "reason": reason})


def _sell(pf, code, price, config, trades, date, reason):
    if code not in pf.positions or not np.isfinite(price):
        return
    pos = pf.positions.pop(code)
    proceeds = pos.shares * price
    cost = trade_cost(proceeds, config.commission_rate, config.slippage_rate)
    pf.cash += proceeds - cost
    trades.append({"date": date, "code": code, "side": "SELL",
                   "shares": pos.shares, "price": price, "cost": cost,
                   "reason": reason})


def _rebalance(pf, weights, opens, config, trades, date):
    # 기존 포지션의 entry_price 보존 (동일 종목 리밸런싱 시 익절 기준 유지)
    old_entries = {code: pos.entry_price for code, pos in pf.positions.items()}
    for code in list(pf.positions):
        _sell(pf, code, opens.get(code, np.nan), config, trades, date,
              "rebalance")
    investable = pf.cash
    for code, w in weights.items():
        px = opens.get(code, np.nan)
        if np.isfinite(px) and px > 0:
            _buy(pf, code, px, investable * w, config, trades, date,
                 "rebalance")
            # 동일 종목 재진입 시 원래 entry_price 복원
            if code in old_entries and code in pf.positions:
                pf.positions[code].entry_price = old_entries[code]


def _first_trading_day_of_month(dates) -> pd.Series:
    seen = set()
    flags = []
    for d in dates:
        key = (d.year, d.month)
        flags.append(key not in seen)
        seen.add(key)
    return pd.Series(flags, index=dates)


def run_backtest(close_panel, open_panel, config):
    """일봉 루프. 신호는 종가에 산출, 체결은 다음 거래일 시가.

    반환: (equity_curve: pd.Series, trades: list[dict])
    """
    dates = close_panel.index
    pf = Portfolio(cash=config.initial_capital)
    pending = None  # None | ("rebalance", weights) | ("sell", [codes])
    trades = []
    equity = {}
    is_rebal = _first_trading_day_of_month(dates)

    for d in dates:
        opens = open_panel.loc[d]
        closes = close_panel.loc[d]

        # 1) 전일 산출 신호를 오늘 시가에 체결
        if pending is not None:
            kind = pending[0]
            if kind == "sell":
                for code in pending[1]:
                    _sell(pf, code, opens.get(code, np.nan), config,
                          trades, d, "take_profit")
            elif kind == "rebalance":
                _rebalance(pf, pending[1], opens, config, trades, d)
            pending = None

        # 2) 종가 기준 평가금액 기록
        equity[d] = pf.equity({c: closes.get(c, np.nan)
                               for c in close_panel.columns})

        # 3) 다음 거래일 체결할 신호 산출
        if config.use_take_profit:
            tp = []
            for code, pos in pf.positions.items():
                px = closes.get(code, np.nan)
                if (np.isfinite(px)
                        and px / pos.entry_price - 1.0
                        >= config.take_profit_pct):
                    tp.append(code)
            if tp:
                pending = ("sell", tp)
        if is_rebal.loc[d]:
            scores = compute_scores(close_panel.loc[:d], d,
                                    config.momentum_lookback_months,
                                    config.momentum_skip_months)
            selected = select_top_k(scores, config.top_k)
            weights = target_weights(selected, scores, config.top_k,
                                     config.use_absolute_momentum,
                                     config.absolute_momentum_threshold)
            pending = ("rebalance", weights)

    return pd.Series(equity).sort_index(), trades


def benchmark_curve(close_series: pd.Series, initial_capital: float) -> pd.Series:
    """벤치마크 ETF 매수후보유 가격수익률 곡선."""
    s = close_series.dropna()
    if s.empty:
        return pd.Series(dtype=float)
    return initial_capital * s / s.iloc[0]
