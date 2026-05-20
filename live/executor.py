from datetime import datetime

from live.errors import SafetyError
from live.safety import (within_position_limit, daily_loss_kill,
                          order_size_ok, validate_paper_mode)
from live.state import Holding


def execute(decision, broker, state, safety_params, log, now=None) -> bool:
    """
    Decision을 실제 주문으로 실행한다.
    안전검사 실패·주문거부·예외 시 state.halted=True로 설정하고 False 반환.
    """
    if decision.action == "NOOP":
        return True

    now = now or datetime.now()

    # 1) 모드 검사
    try:
        validate_paper_mode(state.mode)
    except SafetyError as e:
        log.error(f"mode violation: {e}")
        state.halted = True
        return False

    # 2) 일일 손실 킬스위치
    try:
        equity_now = broker.get_balance().get("equity", 0.0)
    except Exception as e:
        log.error(f"balance fetch failed: {e}")
        state.halted = True
        return False
    if daily_loss_kill(equity_now, state.equity_start_of_day,
                       safety_params["max_daily_loss"]):
        log.warning("daily loss kill-switch triggered")
        state.halted = True
        return False

    # 3) 매도 먼저
    for order in decision.orders:
        if order.side != "SELL":
            continue
        try:
            oid = broker.place_order(order.code, "SELL", order.qty)
            status = broker.get_order_status(oid)
        except Exception as e:
            log.error(f"SELL {order.code} 실패: {e}")
            state.halted = True
            return False
        if str(status.get("status", "")).upper() != "FILLED":
            log.error(f"SELL {order.code} 미체결: {status}")
            state.halted = True
            return False
        state.cash += status["filled_qty"] * status["fill_price"]
        state.holdings.pop(order.code, None)
        log.info(f"SELL {order.code} x{status['filled_qty']} @ "
                 f"{status['fill_price']} ({order.reason})")

    # 4) 매수
    for order in decision.orders:
        if order.side != "BUY":
            continue
        try:
            quote = broker.get_quote(order.code)
        except Exception as e:
            log.error(f"quote {order.code} 실패: {e}")
            state.halted = True
            return False
        notional = order.qty * quote
        equity_now = broker.get_balance().get("equity", 0.0)
        if not within_position_limit(notional, equity_now,
                                     safety_params["max_position_pct"]):
            log.warning(
                f"BUY {order.code} 한도초과 (notional={notional:.0f} "
                f"> {safety_params['max_position_pct']:.0%} of equity); 건너뜀")
            continue
        if not order_size_ok(notional, safety_params["min_order_amount"]):
            log.info(f"BUY {order.code} 최소금액 미달; 건너뜀")
            continue
        try:
            oid = broker.place_order(order.code, "BUY", order.qty)
            status = broker.get_order_status(oid)
        except Exception as e:
            log.error(f"BUY {order.code} 실패: {e}")
            state.halted = True
            return False
        if str(status.get("status", "")).upper() != "FILLED":
            log.error(f"BUY {order.code} 미체결: {status}")
            state.halted = True
            return False
        state.cash -= status["filled_qty"] * status["fill_price"]
        state.holdings[order.code] = Holding(
            shares=int(status["filled_qty"]),
            entry_price=float(status["fill_price"]),
            bought_at=now.date().isoformat(),
        )
        log.info(f"BUY {order.code} x{status['filled_qty']} @ "
                 f"{status['fill_price']} ({order.reason})")

    # 5) 액션 기록
    today_str = now.date().isoformat()
    state.last_action_date = today_str
    if decision.action == "REBALANCE":
        state.last_rebalance_date = today_str
    return True
