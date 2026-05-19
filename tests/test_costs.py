from engine.costs import trade_cost


def test_trade_cost_is_rate_times_notional():
    # 1,000,000원 거래, 수수료 0.015% + 슬리피지 0.035% = 0.05%
    assert trade_cost(1_000_000, 0.00015, 0.00035) == 500.0


def test_trade_cost_uses_absolute_notional():
    assert trade_cost(-1_000_000, 0.00015, 0.00035) == 500.0


def test_zero_notional_zero_cost():
    assert trade_cost(0, 0.00015, 0.00035) == 0.0
