from dataclasses import dataclass, field

ETF_UNIVERSE = [
    "TIGER 미국S&P500",
    "TIGER 미국테크TOP10 INDXX",
    "KODEX 미국AI반도체TOP3플러스",
    "TIGER 미국필라델피아AI반도체나스닥",
    "TIGER 미국필라델피아반도체나스닥",
    "TIGER 글로벌AI&로보틱스 INDXX",
    "TIGER 미국배당다우존스",
    "KODEX 인도Nifty50",
]


@dataclass
class BacktestConfig:
    universe: list = field(default_factory=lambda: list(ETF_UNIVERSE))
    benchmark_name: str = "TIGER 미국S&P500"
    start_date: str = "2016-01-01"
    end_date: str = ""  # "" → 실행일(today)
    initial_capital: float = 10_000_000.0
    top_k: int = 3
    momentum_lookback_months: int = 12
    momentum_skip_months: int = 1
    use_absolute_momentum: bool = True
    absolute_momentum_threshold: float = 0.0
    use_take_profit: bool = True
    take_profit_pct: float = 0.05
    commission_rate: float = 0.00015
    slippage_rate: float = 0.00035
    cache_dir: str = "data/cache"
