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


# 이름 → 종목코드 확정 매핑 캐시 (spec §3: 리스팅 조회 실패·오프라인 시 fallback).
# 새 종목은 fdr.StockListing('ETF/KR')로 확인 후 추가한다.
KNOWN_CODES = {
    "TIGER 미국나스닥100": "133690",
    "TIGER 미국필라델피아반도체나스닥": "381180",
    "TIGER 미국S&P500": "360750",
}


@dataclass
class FixedWeightConfig:
    """고정 비중 포트폴리오 백테스트 설정. 기본: 나스닥100 70 / 필라델피아반도체 30."""
    weights: dict = field(default_factory=lambda: {
        "TIGER 미국나스닥100": 0.7,
        "TIGER 미국필라델피아반도체나스닥": 0.3,
    })
    rebalance: str = "monthly"   # none | monthly | quarterly | yearly
    band: float = 0.0            # 0 → 비활성. 0.05 → 5%p 이탈 시 리밸런싱
    benchmark_name: str = "TIGER 미국S&P500"
    start_date: str = "2016-01-01"
    end_date: str = ""
    initial_capital: float = 10_000_000.0
    commission_rate: float = 0.00015
    slippage_rate: float = 0.00035
    cache_dir: str = "data/cache"
