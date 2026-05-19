import os

import matplotlib
matplotlib.use("Agg")  # 헤드리스 백엔드
import matplotlib.pyplot as plt
import pandas as pd

_ROWS = [
    ("total_return", "Total Return", "pct"),
    ("cagr", "CAGR", "pct"),
    ("max_drawdown", "Max Drawdown", "pct"),
    ("sharpe", "Sharpe", "num"),
    ("sortino", "Sortino", "num"),
    ("volatility", "Volatility", "pct"),
    ("num_trades", "Num Trades", "int"),
]


def _fmt(value, kind: str) -> str:
    if kind == "pct":
        return f"{value * 100:.2f}%"
    if kind == "int":
        return f"{int(value)}"
    return f"{value:.2f}"


def format_summary_table(summary: dict) -> str:
    lines = ["=" * 36, f"{'Metric':<18}{'Value':>18}", "-" * 36]
    for key, label, kind in _ROWS:
        lines.append(f"{label:<18}{_fmt(summary[key], kind):>18}")
    lines.append("=" * 36)
    return "\n".join(lines)


def write_report(strategy_curve, benchmark_curve, trades, summary,
                  out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    ax1.plot(strategy_curve.index, strategy_curve.values, label="Strategy")
    if benchmark_curve is not None and len(benchmark_curve) > 0:
        ax1.plot(benchmark_curve.index, benchmark_curve.values,
                 label="Benchmark", alpha=0.7)
    ax1.set_title("Equity Curve")
    ax1.legend()
    dd = strategy_curve / strategy_curve.cummax() - 1.0
    ax2.fill_between(dd.index, dd.values, 0, color="red", alpha=0.3)
    ax2.set_title("Drawdown")
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "equity_curve.png"), dpi=120)
    plt.close(fig)

    pd.DataFrame(trades).to_csv(os.path.join(out_dir, "trades.csv"),
                                index=False, encoding="utf-8-sig")

    table = format_summary_table(summary)
    html = (f"<html><head><meta charset='utf-8'></head><body>"
            f"<h1>Backtest Summary</h1><pre>{table}</pre>"
            f"<img src='equity_curve.png' style='max-width:900px'>"
            f"</body></html>")
    with open(os.path.join(out_dir, "summary.html"), "w",
              encoding="utf-8") as f:
        f.write(html)

    return table
