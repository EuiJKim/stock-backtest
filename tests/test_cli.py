from config import BacktestConfig
from run_backtest import build_config, parse_args


def test_parse_args_defaults():
    args = parse_args([])
    assert args.no_take_profit is False
    assert args.compare_tp is False
    assert args.top_k == 3


def test_build_config_applies_overrides():
    args = parse_args(["--no-take-profit", "--top-k", "5",
                       "--start", "2018-01-01"])
    cfg = build_config(args)
    assert isinstance(cfg, BacktestConfig)
    assert cfg.use_take_profit is False
    assert cfg.top_k == 5
    assert cfg.start_date == "2018-01-01"
