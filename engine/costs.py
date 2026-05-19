def trade_cost(notional: float, commission_rate: float, slippage_rate: float) -> float:
    """매수·매도 양쪽에 적용되는 거래 1건의 총비용(KRW)."""
    return abs(notional) * (commission_rate + slippage_rate)
