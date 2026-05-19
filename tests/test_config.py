from config import BacktestConfig, ETF_UNIVERSE


def test_default_config_invariants():
    c = BacktestConfig()
    assert c.top_k == 3
    assert 0 < c.take_profit_pct < 1
    assert c.momentum_lookback_months > c.momentum_skip_months
    assert c.initial_capital > 0
    assert len(c.universe) == 8
    assert c.benchmark_name in ETF_UNIVERSE
    assert c.universe is not ETF_UNIVERSE  # 복사본이어야 함 (전역 오염 방지)
