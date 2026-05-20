from datetime import datetime, time

from live.errors import SafetyError

KRX_OPEN = time(9, 0)
KRX_CLOSE = time(15, 30)


def is_market_open(now: datetime) -> bool:
    if now.weekday() >= 5:  # 토(5), 일(6)
        return False
    t = now.time()
    return KRX_OPEN <= t <= KRX_CLOSE


def within_position_limit(notional: float, equity: float,
                          max_pct: float) -> bool:
    if equity <= 0:
        return False
    return notional / equity <= max_pct


def daily_loss_kill(equity_now: float, equity_start: float,
                    max_loss_pct: float) -> bool:
    if equity_start <= 0:
        return False
    loss = (equity_start - equity_now) / equity_start
    return loss >= max_loss_pct


def order_size_ok(notional: float, min_amount: float) -> bool:
    return notional >= min_amount


def holdings_drift_ok(state_holdings: dict, broker_holdings: dict,
                      tolerance: float) -> bool:
    codes = set(state_holdings.keys()) | set(broker_holdings.keys())
    for code in codes:
        s_shares = (state_holdings[code].shares
                    if code in state_holdings else 0)
        b_shares = int(broker_holdings.get(code, {}).get("shares", 0))
        if s_shares == 0 and b_shares == 0:
            continue
        max_shares = max(s_shares, b_shares)
        if max_shares == 0:
            continue
        if abs(s_shares - b_shares) / max_shares > tolerance:
            return False
    return True


def validate_paper_mode(mode: str) -> None:
    if mode != "paper":
        raise SafetyError(f"paper 모드만 허용; got mode={mode!r}")
