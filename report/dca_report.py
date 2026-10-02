import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from metrics.dca import yearly_dca_table


def _won(v: float) -> str:
    return f"{v:,.0f}원"


def format_dca_table(summaries: dict) -> str:
    rows = [
        ("total_invested", "총 납입", "won"),
        ("final_value", "최종 평가", "won"),
        ("profit", "손익", "won"),
        ("profit_ratio", "납입 대비 수익률", "pct"),
        ("irr", "연환산 수익률(IRR)", "pct"),
        ("max_drawdown", "최대 낙폭(평가액)", "pct"),
        ("worst_pnl_ratio", "최저 손익률", "pct"),
        ("worst_pnl_date", "최저 손익 시점", "str"),
        ("months_underwater", "손실 상태 월수", "int"),
        ("num_contributions", "납입 횟수", "int"),
    ]
    names = list(summaries)
    w = max(18, max(len(n) for n in names) + 2)
    header = f"{'항목':<20}" + "".join(f"{n:>{w}}" for n in names)
    lines = ["=" * len(header), header, "-" * len(header)]
    for key, label, kind in rows:
        line = f"{label:<20}"
        for n in names:
            v = summaries[n].get(key)
            if v is None:
                s = "-"
            elif kind == "won":
                s = _won(v)
            elif kind == "pct":
                s = f"{v * 100:.2f}%"
            elif kind == "int":
                s = f"{int(v)}"
            else:
                s = str(v)
            line += f"{s:>{w}}"
        lines.append(line)
    lines.append("=" * len(header))
    return "\n".join(lines)


def format_dca_yearly(value: pd.Series, invested: pd.Series) -> str:
    t = yearly_dca_table(value, invested)
    header = f"{'연도':<8}{'누적 납입':>16}{'평가금액':>16}{'손익률':>10}"
    lines = ["=" * len(header), header, "-" * len(header)]
    for year, r in t.iterrows():
        lines.append(f"{year:<8}{_won(r['invested']):>16}{_won(r['value']):>16}"
                     f"{r['pnl_ratio'] * 100:>9.1f}%")
    lines.append("=" * len(header))
    return "\n".join(lines)


def write_dca_report(value: pd.Series, invested: pd.Series, summaries: dict,
                     out_dir: str, title: str, extra_curves: dict = None) -> str:
    os.makedirs(out_dir, exist_ok=True)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 8.5), sharex=True,
                                   gridspec_kw={"height_ratios": [3, 1.3]})
    ax1.plot(invested.index, invested.values / 1e4, label="누적 납입",
             color="#888", linewidth=1.5)
    ax1.plot(value.index, value.values / 1e4, label="평가금액", linewidth=2.2)
    for name, c in (extra_curves or {}).items():
        ax1.plot(c.index, c.values / 1e4, label=name, linewidth=1.2, alpha=0.7)
    ax1.set_ylabel("만원")
    ax1.set_title(title)
    ax1.legend(loc="upper left")
    ax1.grid(alpha=0.3)
    pnl = value / invested.replace(0, float("nan")) - 1.0
    ax2.fill_between(pnl.index, pnl.values * 100, 0,
                     where=(pnl.values >= 0), color="#2a7", alpha=0.4)
    ax2.fill_between(pnl.index, pnl.values * 100, 0,
                     where=(pnl.values < 0), color="#c33", alpha=0.5)
    ax2.set_ylabel("납입 대비 손익률 %")
    ax2.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "dca.png"), dpi=120)
    plt.close(fig)

    pd.DataFrame({"invested": invested, "value": value}).to_csv(
        os.path.join(out_dir, "dca_curve.csv"))
    table = format_dca_table(summaries)
    yearly = format_dca_yearly(value, invested)
    html = (f"<html><head><meta charset='utf-8'></head><body><h1>{title}</h1>"
            f"<pre>{table}</pre><h2>연도별</h2><pre>{yearly}</pre>"
            f"<img src='dca.png' style='max-width:1000px'></body></html>")
    with open(os.path.join(out_dir, "summary.html"), "w", encoding="utf-8") as f:
        f.write(html)
    return table + "\n\n" + yearly
