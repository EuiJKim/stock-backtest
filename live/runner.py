from dataclasses import dataclass, field
import pandas as pd

from strategy.momentum import compute_scores, select_top_k, target_weights


@dataclass
class Order:
    code: str
    side: str   # "BUY" | "SELL"
    qty: int
    reason: str


@dataclass
class Decision:
    action: str  # "REBALANCE" | "TAKE_PROFIT" | "NOOP"
    orders: list = field(default_factory=list)
    reason: str = ""


def _is_first_action_of_month(today, last_rebalance_str: str) -> bool:
    if not last_rebalance_str:
        return True
    last = pd.Timestamp(last_rebalance_str).date()
    return (today.year, today.month) != (last.year, last.month)


def decide(close_panel: pd.DataFrame, today,
           holdings_state: dict, cash: float,
           params, state) -> Decision:
    latest = close_panel.iloc[-1]

    # 1) 월이 바뀌었으면 리밸런싱 (익절보다 우선)
    if _is_first_action_of_month(today, state.last_rebalance_date):
        scores = compute_scores(close_panel, pd.Timestamp(today),
                                params.momentum_lookback_months,
                                params.momentum_skip_months)
        selected = select_top_k(scores, params.top_k)
        weights = target_weights(selected, scores, params.top_k,
                                 params.use_absolute_momentum,
                                 params.absolute_momentum_threshold)
        equity = cash + sum(
            h.shares * float(latest.get(c, 0) or 0)
            for c, h in holdings_state.items()
        )
        orders = []
        for code, h in holdings_state.items():
            orders.append(Order(code=code, side="SELL", qty=h.shares,
                                reason="rebalance"))
        for code, w in weights.items():
            px = float(latest.get(code, 0) or 0)
            if px > 0:
                qty = int((equity * w) // px)
                if qty > 0:
                    orders.append(Order(code=code, side="BUY", qty=qty,
                                        reason="rebalance"))
        return Decision(action="REBALANCE", orders=orders,
                        reason=f"monthly rebalance: target={list(weights)}")

    # 2) 같은 달이면 익절만 검사
    if params.use_take_profit:
        tp_orders = []
        for code, h in holdings_state.items():
            px = float(latest.get(code, 0) or 0)
            if px > 0 and px / h.entry_price - 1.0 >= params.take_profit_pct:
                tp_orders.append(Order(code=code, side="SELL",
                                       qty=h.shares, reason="take_profit"))
        if tp_orders:
            return Decision(action="TAKE_PROFIT", orders=tp_orders,
                            reason=f"+{params.take_profit_pct:.0%} reached")

    return Decision(action="NOOP", orders=[], reason="no signal today")
