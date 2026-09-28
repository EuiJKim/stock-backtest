"""여러 시나리오(전략·벤치마크) 성과를 나란히 비교하는 표·차트."""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import font_manager

# 한글 라벨용 폰트 (설치된 것 중 첫 번째). 없으면 기본 폰트 유지 (경고만 발생).
_KO_FONTS = ("Malgun Gothic", "AppleGothic", "NanumGothic", "Noto Sans CJK KR",
             "Noto Sans KR", "Pretendard")
_installed = {f.name for f in font_manager.fontManager.ttflist}
for _name in _KO_FONTS:
    if _name in _installed:
        matplotlib.rcParams["font.family"] = _name
        break
matplotlib.rcParams["axes.unicode_minus"] = False

from metrics.performance import yearly_returns
from report.report import _ROWS, _fmt


def format_compare_table(summaries: dict) -> str:
    """{시나리오명: summary dict} → 열이 시나리오인 고정폭 표."""
    names = list(summaries)
    w = max(14, max(len(n) for n in names) + 2)
    header = f"{'Metric':<16}" + "".join(f"{n:>{w}}" for n in names)
    lines = ["=" * len(header), header, "-" * len(header)]
    for key, label, kind in _ROWS:
        row = f"{label:<16}"
        for n in names:
            v = summaries[n].get(key)
            row += f"{(_fmt(v, kind) if v is not None else '-'):>{w}}"
        lines.append(row)
    lines.append("=" * len(header))
    return "\n".join(lines)


def format_yearly_compare(curves: dict) -> str:
    """{시나리오명: equity curve} → 연도별 수익률 비교표."""
    table = pd.DataFrame({n: yearly_returns(c) for n, c in curves.items()})
    names = list(table.columns)
    w = max(14, max(len(n) for n in names) + 2)
    header = f"{'Year':<8}" + "".join(f"{n:>{w}}" for n in names)
    lines = ["=" * len(header), header, "-" * len(header)]
    for year, row in table.iterrows():
        line = f"{year:<8}"
        for n in names:
            v = row[n]
            line += f"{(f'{v * 100:.2f}%' if pd.notna(v) else '-'):>{w}}"
        lines.append(line)
    lines.append("=" * len(header))
    return "\n".join(lines)


def write_compare_report(curves: dict, summaries: dict, weight_hist,
                         out_dir: str, title: str) -> str:
    os.makedirs(out_dir, exist_ok=True)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 9), sharex=True,
                                   gridspec_kw={"height_ratios": [3, 1.4]})
    for i, (name, c) in enumerate(curves.items()):
        base = c / c.iloc[0]
        ax1.plot(base.index, base.values, label=name,
                 linewidth=2.2 if i == 0 else 1.2,
                 alpha=1.0 if i == 0 else 0.75)
    ax1.set_yscale("log")
    ax1.set_title(f"{title} — Growth of 1 (log)")
    ax1.legend(loc="upper left")
    ax1.grid(alpha=0.3)
    for i, (name, c) in enumerate(curves.items()):
        dd = c / c.cummax() - 1.0
        ax2.plot(dd.index, dd.values, label=name,
                 linewidth=1.8 if i == 0 else 0.9,
                 alpha=1.0 if i == 0 else 0.6)
    ax2.set_title("Drawdown")
    ax2.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "compare.png"), dpi=120)
    plt.close(fig)

    if weight_hist is not None and len(weight_hist) > 0:
        fig, ax = plt.subplots(figsize=(11, 3.5))
        ax.stackplot(weight_hist.index, *[weight_hist[c].values
                                          for c in weight_hist.columns],
                     labels=list(weight_hist.columns), alpha=0.85)
        ax.set_ylim(0, 1)
        ax.set_title("Portfolio weights")
        ax.legend(loc="upper left", fontsize=8)
        fig.tight_layout()
        fig.savefig(os.path.join(out_dir, "weights.png"), dpi=120)
        plt.close(fig)
        weight_hist.to_csv(os.path.join(out_dir, "weights.csv"))

    pd.DataFrame(curves).to_csv(os.path.join(out_dir, "equity_curves.csv"))

    table = format_compare_table(summaries)
    yearly = format_yearly_compare(curves)
    html = (f"<html><head><meta charset='utf-8'></head><body>"
            f"<h1>{title}</h1><pre>{table}</pre>"
            f"<h2>연도별 수익률</h2><pre>{yearly}</pre>"
            f"<img src='compare.png' style='max-width:1000px'>"
            f"<img src='weights.png' style='max-width:1000px'>"
            f"</body></html>")
    with open(os.path.join(out_dir, "summary.html"), "w",
              encoding="utf-8") as f:
        f.write(html)
    return table + "\n\n" + yearly
