import argparse
from datetime import date

from config import BacktestConfig
from data.loader import build_panels
from data.universe import load_listing, match_codes
from engine.backtest import run_backtest, benchmark_curve
from metrics.performance import summarize
from report.report import write_report


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="ETF 듀얼 모멘텀 백테스트")
    p.add_argument("--no-take-profit", action="store_true")
    p.add_argument("--compare-tp", action="store_true",
                   help="익절 ON/OFF 두 시나리오 비교")
    p.add_argument("--top-k", type=int, default=3)
    p.add_argument("--start", default="2016-01-01")
    p.add_argument("--end", default="")
    p.add_argument("--out", default="report_output")
    return p.parse_args(argv)


def build_config(args) -> BacktestConfig:
    return BacktestConfig(
        top_k=args.top_k,
        start_date=args.start,
        end_date=args.end,
        use_take_profit=not args.no_take_profit,
    )


def _run_once(cfg, codes, name_by_code, out_dir):
    end = cfg.end_date or date.today().isoformat()
    close, opens = build_panels(codes, cfg.start_date, end, cfg.cache_dir)
    curve, trades = run_backtest(close, opens, cfg)
    bench_code = name_by_code.get(cfg.benchmark_name)
    bench = (benchmark_curve(close[bench_code], cfg.initial_capital)
             if bench_code in close.columns else None)
    summary = summarize(curve, trades)
    table = write_report(curve, bench, trades, summary, out_dir)
    print(table)
    return summary


def main(argv=None):
    args = parse_args(argv)
    cfg = build_config(args)
    listing = load_listing()
    code_by_name = match_codes(cfg.universe, listing)
    codes = [c for c in code_by_name.values() if c]
    name_by_code = {v: k for k, v in code_by_name.items() if v}

    if args.compare_tp:
        on = BacktestConfig(**{**cfg.__dict__, "use_take_profit": True})
        off = BacktestConfig(**{**cfg.__dict__, "use_take_profit": False})
        print("\n=== 익절 ON ===")
        _run_once(on, codes, name_by_code, f"{args.out}_tp_on")
        print("\n=== 익절 OFF ===")
        _run_once(off, codes, name_by_code, f"{args.out}_tp_off")
    else:
        _run_once(cfg, codes, name_by_code, args.out)


if __name__ == "__main__":
    main()
