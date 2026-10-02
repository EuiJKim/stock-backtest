"""고정 비중 포트폴리오 백테스트 CLI.

기본: TIGER 미국나스닥100 70% + TIGER 미국필라델피아반도체나스닥 30%,
매월 첫 거래일 리밸런싱. 비교군으로 각 자산 100% 보유, 매수후보유(리밸런싱 없음),
벤치마크(TIGER 미국S&P500)를 함께 출력한다.

예)
  python run_portfolio.py
  python run_portfolio.py --rebalance quarterly
  python run_portfolio.py --weights "TIGER 미국나스닥100:0.6,TIGER 미국필라델피아반도체나스닥:0.4"
  python run_portfolio.py --codes "133690:0.7,381180:0.3" --offline   # 리스팅 조회 없이
  python run_portfolio.py --compare-rebalance                          # 규칙별 비교
  python run_portfolio.py --monthly 500000 --weights "TIGER 미국나스닥100:1"  # 매월 50만원 적립식

오프라인 데이터: data/cache/<코드>.csv (Date 인덱스, Open/Close 열) 가 있으면
네트워크 없이 그대로 사용한다 (data.loader 캐시 포맷과 동일).
"""
import argparse
import os
from datetime import date

from config import KNOWN_CODES, FixedWeightConfig
from data.loader import build_panels
from engine.backtest import benchmark_curve
from engine.dca_backtest import run_dca, run_lump_sum
from engine.fixed_weight_backtest import run_fixed_weight
from metrics.dca import summarize_dca
from report.dca_report import write_dca_report
from metrics.performance import summarize
from report.compare import write_compare_report
from strategy.fixed_weight import REBALANCE_RULES


def parse_pairs(text: str) -> dict:
    """'A:0.7,B:0.3' → {'A': 0.7, 'B': 0.3}"""
    out = {}
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        name, _, w = part.rpartition(":")
        if not name:
            raise ValueError(f"bad weight spec: {part!r} (expected NAME:WEIGHT)")
        out[name.strip()] = float(w)
    if not out:
        raise ValueError("empty weight spec")
    return out


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="고정 비중 포트폴리오 백테스트")
    p.add_argument("--weights", default=None,
                   help="'이름:비중,이름:비중' (기본: 나스닥100 0.7 / 필라델피아반도체 0.3)")
    p.add_argument("--codes", default=None,
                   help="'코드:비중,...' — 이름 대신 종목코드로 직접 지정")
    p.add_argument("--rebalance", default="monthly", choices=REBALANCE_RULES)
    p.add_argument("--band", type=float, default=0.0,
                   help="목표 대비 이탈 허용폭(%%p, 0.05=5%%p). 0이면 비활성")
    p.add_argument("--compare-rebalance", action="store_true",
                   help="none/monthly/quarterly/yearly 4개 규칙을 한 표로 비교")
    p.add_argument("--benchmark", default="TIGER 미국S&P500")
    p.add_argument("--start", default="2016-01-01")
    p.add_argument("--end", default="")
    p.add_argument("--capital", type=float, default=10_000_000.0)
    p.add_argument("--monthly", type=float, default=0.0,
                   help="적립식 모드: 매월 첫 거래일 납입액(원). 0이면 거치식 비중 백테스트")
    p.add_argument("--initial", type=float, default=0.0,
                   help="적립식 모드 첫 달 추가 납입(초기 투자금)")
    p.add_argument("--no-cash-rebalance", action="store_true",
                   help="적립식: 납입금을 목표 비중대로만 매수 (부족 자산 우선 배분 끄기)")
    p.add_argument("--offline", action="store_true",
                   help="fdr 리스팅 조회 생략, config.KNOWN_CODES만 사용")
    p.add_argument("--cache-dir", default="data/cache",
                   help="시세 CSV 캐시 디렉터리 (<코드>.csv)")
    p.add_argument("--out", default="report_output_portfolio")
    return p.parse_args(argv)


def resolve_codes(names, offline: bool) -> dict:
    """이름 → 코드. KNOWN_CODES 우선, 없으면 fdr 리스팅 조회."""
    out = {n: KNOWN_CODES.get(n) for n in names}
    unresolved = [n for n, c in out.items() if not c]
    if unresolved and not offline:
        from data.universe import load_listing, match_codes
        out.update(match_codes(unresolved, load_listing()))
    still = [n for n, c in out.items() if not c]
    if still:
        raise SystemExit(f"종목코드를 찾을 수 없음: {still} "
                         f"(--codes 로 직접 지정하거나 config.KNOWN_CODES에 추가)")
    return out


def _label(code_weights: dict, name_by_code: dict) -> str:
    return " / ".join(f"{name_by_code.get(c, c)} {w * 100:.0f}%"
                      for c, w in code_weights.items())


def build_scenarios(close, opens, code_weights, cfg, name_by_code,
                    bench_code, rebalance_rules):
    """메인 전략 + 비교군 자산곡선/요약 산출."""
    curves, summaries = {}, {}
    weight_hist = None
    for rule in rebalance_rules:
        label = f"{'/'.join(f'{w * 100:.0f}' for w in code_weights.values())} {rule}"
        curve, trades, wh = run_fixed_weight(close, opens, code_weights, cfg,
                                             rebalance=rule, band=cfg.band)
        curves[label] = curve
        summaries[label] = summarize(curve, trades)
        if weight_hist is None:
            weight_hist = wh.rename(columns=name_by_code)
    # 단일 자산 100% 보유 (동일 구간·동일 비용)
    for code in code_weights:
        curve, trades, _ = run_fixed_weight(close, opens, {code: 1.0}, cfg,
                                            rebalance="none")
        label = f"100% {name_by_code.get(code, code)}"
        curves[label] = curve
        summaries[label] = summarize(curve, trades)
    # 벤치마크: 가격수익률 매수후보유 (비용 없음, 기존 엔진과 동일 정의)
    if bench_code and bench_code in close.columns:
        first = next(iter(curves.values())).index
        b = benchmark_curve(close.loc[first, bench_code], cfg.initial_capital)
        if len(b):
            label = f"Bench {name_by_code.get(bench_code, bench_code)}"
            curves[label] = b
            summaries[label] = summarize(b, [])
    return curves, summaries, weight_hist


def run_dca_mode(args, cfg, close, opens, code_weights, name_by_code):
    """매월 적립식 + 동일 총액 거치식 비교."""
    value, invested, trades, contribs = run_dca(
        close, opens, code_weights, cfg, monthly_amount=args.monthly,
        rebalance_with_cash=not args.no_cash_rebalance, initial_amount=args.initial)
    label = f"적립식 매월 {args.monthly / 1e4:,.0f}만원"
    summaries = {label: summarize_dca(value, invested, contribs)}
    total = invested.iloc[-1]
    ls_value, ls_inv, _, ls_contribs = run_lump_sum(close, opens, code_weights, cfg, total)
    summaries["거치식 (동일 총액)"] = summarize_dca(ls_value, ls_inv, ls_contribs)

    title = f"DCA — {_label(code_weights, name_by_code)}"
    print(f"\n{title}")
    print(f"기간: {value.index[0].date()} ~ {value.index[-1].date()}  "
          f"납입 {len(contribs)}회")
    print(write_dca_report(value, invested, summaries, args.out, title,
                           extra_curves={"거치식 평가금액": ls_value}))
    print(f"\n리포트: {args.out}/summary.html")
    return summaries


def main(argv=None):
    args = parse_args(argv)
    cfg = FixedWeightConfig(rebalance=args.rebalance, band=args.band,
                            benchmark_name=args.benchmark,
                            start_date=args.start, end_date=args.end,
                            initial_capital=args.capital,
                            cache_dir=args.cache_dir)

    if args.codes:
        code_weights = parse_pairs(args.codes)
        name_by_code = {v: k for k, v in KNOWN_CODES.items()}
    else:
        name_weights = parse_pairs(args.weights) if args.weights else cfg.weights
        code_by_name = resolve_codes(list(name_weights), args.offline)
        code_weights = {code_by_name[n]: w for n, w in name_weights.items()}
        name_by_code = {v: k for k, v in code_by_name.items()}

    bench_code = KNOWN_CODES.get(cfg.benchmark_name)
    if bench_code is None and not args.offline:
        bench_code = resolve_codes([cfg.benchmark_name], False)[cfg.benchmark_name]
    if bench_code and args.offline and not os.path.exists(
            os.path.join(cfg.cache_dir, f"{bench_code}.csv")):
        bench_code = None  # 오프라인에서 캐시 없는 벤치마크는 조회하지 않음
    if bench_code:
        name_by_code.setdefault(bench_code, cfg.benchmark_name)

    end = cfg.end_date or date.today().isoformat()
    codes = list(code_weights) + ([bench_code] if bench_code else [])
    close, opens = build_panels(codes, cfg.start_date, end, cfg.cache_dir)
    missing = [c for c in code_weights if c not in close.columns]
    if missing:
        raise SystemExit(f"시세 없음: {missing}. 네트워크 또는 {cfg.cache_dir}/<코드>.csv 확인")

    if args.monthly > 0:
        return run_dca_mode(args, cfg, close, opens, code_weights, name_by_code)

    rules = list(REBALANCE_RULES) if args.compare_rebalance else [args.rebalance]
    if not args.compare_rebalance and args.rebalance != "none":
        rules.append("none")  # 매수후보유 비교군
    curves, summaries, weight_hist = build_scenarios(
        close, opens, code_weights, cfg, name_by_code, bench_code, rules)

    title = f"Fixed Weight — {_label(code_weights, name_by_code)}"
    first = next(iter(curves.values()))
    print(f"\n{title}")
    print(f"기간: {first.index[0].date()} ~ {first.index[-1].date()} "
          f"(모든 자산 시세가 존재하는 공통 구간)")
    print(write_compare_report(curves, summaries, weight_hist, args.out, title))
    print(f"\n리포트: {args.out}/summary.html")
    return summaries


if __name__ == "__main__":
    main()
