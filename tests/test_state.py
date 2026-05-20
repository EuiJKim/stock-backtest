from live.state import Holding, TraderState, TraderParams


def test_state_default_paper_no_holdings():
    s = TraderState()
    assert s.mode == "paper"
    assert s.holdings == {}
    assert s.halted is False


def test_state_roundtrip_json(tmp_path):
    s = TraderState(mode="paper", cash=1_000_000.0,
                    holdings={"360750": Holding(shares=10,
                                                entry_price=15000.0,
                                                bought_at="2026-05-20")},
                    last_rebalance_date="2026-05-01",
                    last_action_date="2026-05-20",
                    halted=False, equity_start_of_day=11_000_000.0)
    p = tmp_path / "state.json"
    s.save(p)
    s2 = TraderState.load(p)
    assert s2.cash == 1_000_000.0
    assert s2.holdings["360750"].shares == 10
    assert s2.holdings["360750"].entry_price == 15000.0
    assert s2.last_rebalance_date == "2026-05-01"


def test_state_load_missing_file_returns_default(tmp_path):
    s = TraderState.load(tmp_path / "nope.json")
    assert s.mode == "paper" and s.holdings == {}


def test_state_save_is_atomic(tmp_path):
    """save() writes via temp+rename — no partial file on a target dir."""
    p = tmp_path / "deep" / "state.json"
    TraderState().save(p)
    assert p.exists()
    # no stray .tmp left behind
    assert not list((tmp_path / "deep").glob("*.tmp"))


def test_params_defaults_match_backtest():
    p = TraderParams()
    assert p.top_k == 3
    assert p.take_profit_pct == 0.05
    assert p.use_absolute_momentum is True
    assert p.target_time_hhmm == "15:15"
    assert 0 < p.max_position_pct < 1
    assert p.min_order_amount > 0


def test_params_roundtrip_json(tmp_path):
    p = TraderParams(top_k=2, take_profit_pct=0.10)
    f = tmp_path / "params.json"
    p.save(f)
    p2 = TraderParams.load(f)
    assert p2.top_k == 2
    assert p2.take_profit_pct == 0.10
