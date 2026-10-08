"""월 150만원 적립 포트폴리오 월간 점검 리포트.

python research/plan150/monthly_report.py                      # 기본: 공격형
python research/plan150/monthly_report.py --weights "나스닥100:0.5,코스피:0.25,필라델피아반도체:0.15,현금CD:0.1"
출력: 콘솔 표 + <out>/report_<날짜>.md + <out>/history.csv (회차별 지표 누적)
"""
import argparse, os, sys
from datetime import date
import numpy as np, pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from metrics.dca import xirr  # noqa: E402

PRESETS = {
    "공격형": {"나스닥100": .5, "코스피": .25, "필라델피아반도체": .15, "현금CD": .1},
    "균형형": {"나스닥100": .4, "코스피": .25, "배당다우존스": .15, "금": .1, "현금CD": .1},
    "현재70/30": {"나스닥100": .7, "필라델피아반도체": .3},
    "나스닥100": {"나스닥100": 1.0},
}
RATE = 0.0005


def parse_w(s):
    return {k.strip(): float(v) for k, v in (x.split(":") for x in s.split(","))}


def dca(px, w, monthly, months=None):
    dates = px.index; sh = {c: 0.0 for c in w}; cash = inv = pend = 0.0; cfs = []; vals = []; invs = []; seen = set(); n = 0
    for i, d in enumerate(dates):
        p = px.loc[d]
        if pend > 0:
            cash += pend; pv = {c: sh[c] * p[c] for c in w}; eq = cash + sum(pv.values())
            df = {c: max(eq * w[c] - pv[c], 0) for c in w}; s = sum(df.values())
            al = {c: cash * df[c] / s for c in w} if s > 0 else {c: cash * w[c] for c in w}
            for c, amt in al.items():
                if amt > 0: sh[c] += amt / p[c] / (1 + RATE); cash -= amt
            pend = 0.0
        vals.append(cash + sum(sh[c] * p[c] for c in w)); invs.append(inv)
        key = (d.year, d.month)
        if key not in seen and i < len(dates) - 1 and (months is None or n < months):
            pend = monthly; inv += monthly; cfs.append((dates[i + 1], -monthly)); seen.add(key); n += 1
    v = pd.Series(vals, index=dates); iv = pd.Series(invs, index=dates); cfs.append((dates[-1], v.iloc[-1]))
    return v, iv, cfs


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data", default="data/plan150/universe_krw.csv")
    p.add_argument("--out", default="data/plan150")
    p.add_argument("--weights", default=None, help="'자산:비중,...' (기본 공격형)")
    p.add_argument("--monthly", type=float, default=1_500_000)
    p.add_argument("--start", default="2014-07-16")
    a = p.parse_args()
    k = pd.read_csv(a.data, index_col=0, parse_dates=True).loc[a.start:].ffill()
    k["현금CD"] = pd.Series(np.cumprod(1 + np.full(len(k), 0.03 / 252)), index=k.index) * 100
    end = k.index[-1]
    ports = dict(PRESETS)
    if a.weights:
        ports = {"지정": parse_w(a.weights), **ports}
    lines = [f"# 월간 점검 {date.today()}  (데이터 마지막 {end.date()})", ""]

    def ret(s, x, y):
        s = s.dropna(); x = pd.Timestamp(x); y = pd.Timestamp(y)
        return s.loc[:y].iloc[-1] / s.loc[:x].iloc[-1] - 1 if len(s.loc[:x]) else np.nan
    lines += ["## 자산별 (원화)", "", "| 자산 | 1개월 | 3개월 | YTD | 1년 | 52주 고점 대비 |", "|---|---|---|---|---|---|"]
    for c in ["나스닥100", "S&P500", "코스피", "필라델피아반도체", "배당다우존스", "금", "미국채7-10년", "달러현금(환율)"]:
        s = k[c].dropna(); hi = s.loc[end - pd.DateOffset(years=1):].max()
        lines.append(f"| {c} | {ret(s, end - pd.DateOffset(months=1), end)*100:+.1f}% | {ret(s, end - pd.DateOffset(months=3), end)*100:+.1f}% | "
                     f"{ret(s, str(end.year - 1) + '-12-31', end)*100:+.1f}% | {ret(s, end - pd.DateOffset(years=1), end)*100:+.1f}% | {(s.iloc[-1]/hi-1)*100:+.1f}% |")
    core = ["나스닥100", "코스피", "필라델피아반도체", "배당다우존스", "금", "달러현금(환율)"]
    corr = k[core].loc[end - pd.DateOffset(years=1):].pct_change().dropna().corr()
    lines += ["", f"나스닥100·코스피 1년 상관계수: {corr.loc['나스닥100','코스피']:.2f} / 나스닥100·반도체: {corr.loc['나스닥100','필라델피아반도체']:.2f} / 나스닥100·금: {corr.loc['나스닥100','금']:.2f}", ""]
    lines += ["## 포트폴리오별", "", "| 포트폴리오 | 최근 1개월 | 최근 3개월 | 4개월 적립 중간/하위10%/최악 | 손실확률 | 2014~ 연수익 | 최대낙폭 |", "|---|---|---|---|---|---|---|"]
    hist = []
    starts = pd.date_range("2014-08-01", end - pd.DateOffset(months=5), freq="MS")
    for name, w in ports.items():
        cols = list(w); px = k[cols].dropna(); r = px.pct_change().fillna(0); pr = (r * pd.Series(w)).sum(axis=1)
        m1 = (1 + pr.loc[end - pd.DateOffset(months=1):]).prod() - 1; m3 = (1 + pr.loc[end - pd.DateOffset(months=3):]).prod() - 1
        out = []
        for s0 in starts:
            sub = px.loc[s0:s0 + pd.DateOffset(months=4) + pd.DateOffset(days=3)]
            if len(sub) < 80: continue
            v, iv, _ = dca(sub, w, a.monthly, months=4); out.append(v.iloc[-1] / iv.iloc[-1] - 1)
        rr = pd.Series(out); v, iv, cfs = dca(px, w, a.monthly); dd = (v / v.cummax() - 1).min(); irr = xirr(cfs)
        lines.append(f"| {name} | {m1*100:+.1f}% | {m3*100:+.1f}% | {rr.median()*100:+.1f}% / {rr.quantile(.1)*100:+.1f}% / {rr.min()*100:+.1f}% | {(rr<0).mean()*100:.0f}% | {irr*100:.1f}% | {dd*100:.1f}% |")
        hist.append({"run_date": str(date.today()), "data_end": str(end.date()), "portfolio": name, "m1": m1, "m3": m3, "irr": irr, "mdd": dd, "dca4_median": rr.median(), "dca4_p10": rr.quantile(.1)})
    os.makedirs(a.out, exist_ok=True)
    md = "\n".join(lines); print(md)
    open(f"{a.out}/report_{date.today()}.md", "w", encoding="utf-8").write(md)
    hpath = f"{a.out}/history.csv"
    pd.concat([pd.read_csv(hpath), pd.DataFrame(hist)]).to_csv(hpath, index=False) if os.path.exists(hpath) else pd.DataFrame(hist).to_csv(hpath, index=False)


if __name__ == "__main__":
    main()
