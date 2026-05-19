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
    for code in list(pf.positions):
        _sell(pf, code, opens.get(code, np.nan), config, trades, date,
              "rebalance")
    investable = pf.cash
    for code, w in weights.items():
        px = opens.get(code, np.nan)
        if np.isfinite(px) and px > 0:
            _buy(pf, code, px, investable * w, config, trades, date,
                 "rebalance")
