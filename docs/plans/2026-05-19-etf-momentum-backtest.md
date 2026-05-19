# ETF 듀얼 모멘텀 로테이션 백테스트 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 한국 상장 미국·테마 ETF 유니버스에 듀얼 모멘텀 로테이션 + 익절 전략을 적용해 과거 시세로 성과를 검증하는 CLI 백테스트 프로그램을 구축한다.

**Architecture:** 순수 함수형 신호 로직(`strategy`)과 상태 컨테이너(`engine.portfolio`)를 분리하고, 일봉 루프 엔진(`engine.backtest`)이 "신호일 → 다음 거래일 시가 체결" 규칙으로 look-ahead bias 없이 시뮬레이션한다. 데이터 IO(`data`)는 fetch 함수를 주입 가능하게 만들어 네트워크 없이 테스트한다.

**Tech Stack:** Python 3.11+, pandas, numpy, FinanceDataReader, matplotlib, pytest

프로젝트 루트: `C:\Users\ASUS\Desktop\stock-backtest` (모든 경로는 이 루트 기준 상대경로)

---

## File Structure

| 파일 | 책임 |
|---|---|
| `config.py` | 유니버스 상수 + `BacktestConfig` 데이터클래스 (모든 파라미터의 단일 진실 공급원) |
| `data/loader.py` | ETF 일봉 OHLC 로드 + CSV 캐시, fetch 함수 주입 |
| `data/universe.py` | ETF 이름→종목코드 매핑 (listing DataFrame 주입) |
| `strategy/momentum.py` | 모멘텀 점수·랭킹·절대모멘텀·목표비중 (순수 함수) |
| `engine/costs.py` | 거래비용 계산 (순수 함수) |
| `engine/portfolio.py` | `Position`, `Portfolio` 상태 + 평가금액 |
| `engine/backtest.py` | 일봉 루프 엔진 + 벤치마크 곡선 |
| `metrics/performance.py` | CAGR·MDD·Sharpe·Sortino·변동성·연도별·요약 |
| `report/report.py` | 콘솔 요약표·차트 PNG·거래 CSV·요약 HTML |
| `run_backtest.py` | argparse CLI 진입점, 익절 ON/OFF 비교 모드 |
| `tests/` | 각 모듈 pytest |

각 파일은 단일 책임을 가지며, `strategy`·`engine.costs`·`metrics`는 순수 함수로 IO를 모른다. `engine.backtest`만이 look-ahead 방지 체결 규칙을 소유한다.

---

### Task 0: 프로젝트 스캐폴딩

**Files:**
- Create: `requirements.txt`
- Create: `pytest.ini`
- Create: `.gitignore`
- Create: `README.md`
- Create: `config/__init__.py` → (사용 안 함, 대신 단일 모듈) — 아래 대신 패키지 `__init__.py`들 생성
- Create: `data/__init__.py`, `strategy/__init__.py`, `engine/__init__.py`, `metrics/__init__.py`, `report/__init__.py`, `tests/__init__.py`

- [ ] **Step 1: requirements.txt 작성**

```
finance-datareader>=0.9.96
pandas>=2.2
numpy>=1.26
matplotlib>=3.8
pytest>=8.0
```

- [ ] **Step 2: pytest.ini 작성** (프로젝트 루트를 import 경로로)

```ini
[pytest]
pythonpath = .
testpaths = tests
```

- [ ] **Step 3: .gitignore 작성**

```
__pycache__/
*.pyc
.venv/
venv/
data/cache/
report_output/
.pytest_cache/
```

- [ ] **Step 4: README.md 작성**

```markdown
# stock-backtest

ETF 듀얼 모멘텀 로테이션 + 익절 전략 백테스트.

## 설치

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 실행

```bash
python run_backtest.py                 # 기본 설정
python run_backtest.py --no-take-profit # 익절 끄기
python run_backtest.py --compare-tp     # 익절 ON/OFF 비교
```

설계: `docs/specs/2026-05-19-etf-momentum-backtest-design.md`
```

- [ ] **Step 5: 빈 패키지 초기화 파일 생성**

각 파일 내용은 빈 문자열 한 줄:
`data/__init__.py`, `strategy/__init__.py`, `engine/__init__.py`, `metrics/__init__.py`, `report/__init__.py`, `tests/__init__.py`
(내용: `# package` 한 줄)

- [ ] **Step 6: 의존성 설치**

Run: `pip install -r requirements.txt`
Expected: 모든 패키지 설치 성공 (이미 설치 시 "Requirement already satisfied")

- [ ] **Step 7: Commit**

```bash
git add requirements.txt pytest.ini .gitignore README.md data/__init__.py strategy/__init__.py engine/__init__.py metrics/__init__.py report/__init__.py tests/__init__.py
git commit -m "chore: 프로젝트 스캐폴딩 (패키지·pytest·의존성)"
```

---

### Task 1: config.py — 설정 데이터클래스

**Files:**
- Create: `config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_config.py
from config import BacktestConfig, ETF_UNIVERSE


def test_default_config_invariants():
    c = BacktestConfig()
    assert c.top_k == 3
    assert 0 < c.take_profit_pct < 1
    assert c.momentum_lookback_months > c.momentum_skip_months
    assert c.initial_capital > 0
    assert len(c.universe) == 8
    assert c.benchmark_name in ETF_UNIVERSE
    assert c.universe is not ETF_UNIVERSE  # 복사본이어야 함 (전역 오염 방지)
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'config'`

- [ ] **Step 3: 최소 구현**

```python
# config.py
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add config.py tests/test_config.py
git commit -m "feat: BacktestConfig 설정 데이터클래스"
```

---

### Task 2: engine/costs.py — 거래비용

**Files:**
- Create: `engine/costs.py`
- Test: `tests/test_costs.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_costs.py
from engine.costs import trade_cost


def test_trade_cost_is_rate_times_notional():
    # 1,000,000원 거래, 수수료 0.015% + 슬리피지 0.035% = 0.05%
    assert trade_cost(1_000_000, 0.00015, 0.00035) == 500.0


def test_trade_cost_uses_absolute_notional():
    assert trade_cost(-1_000_000, 0.00015, 0.00035) == 500.0


def test_zero_notional_zero_cost():
    assert trade_cost(0, 0.00015, 0.00035) == 0.0
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_costs.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'engine.costs'`

- [ ] **Step 3: 최소 구현**

```python
# engine/costs.py
def trade_cost(notional: float, commission_rate: float, slippage_rate: float) -> float:
    """매수·매도 양쪽에 적용되는 거래 1건의 총비용(KRW)."""
    return abs(notional) * (commission_rate + slippage_rate)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_costs.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add engine/costs.py tests/test_costs.py
git commit -m "feat: 거래비용 모델 trade_cost"
```

---

### Task 3: strategy/momentum.py — 모멘텀 점수

**Files:**
- Create: `strategy/momentum.py`
- Test: `tests/test_momentum_score.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_momentum_score.py
import numpy as np
import pandas as pd
from strategy.momentum import momentum_score, _price_asof


def _series():
    idx = pd.date_range("2020-01-01", "2021-06-30", freq="D")
    # 가격: 100에서 매일 +0.1, 단조 증가
    return pd.Series(100.0 + 0.1 * np.arange(len(idx)), index=idx)


def test_price_asof_returns_last_value_on_or_before():
    s = _series()
    assert _price_asof(s, pd.Timestamp("2020-01-01")) == 100.0
    # 2020-01-11 = 인덱스 10 → 100 + 1.0
    assert _price_asof(s, pd.Timestamp("2020-01-11")) == 101.0


def test_price_asof_nan_when_before_start():
    s = _series()
    assert np.isnan(_price_asof(s, pd.Timestamp("2019-01-01")))


def test_momentum_score_12_1():
    s = _series()
    as_of = pd.Timestamp("2021-06-30")
    p_recent = _price_asof(s, as_of - pd.DateOffset(months=1))
    p_old = _price_asof(s, as_of - pd.DateOffset(months=12))
    expected = p_recent / p_old - 1.0
    assert momentum_score(s, as_of, 12, 1) == expected


def test_momentum_score_nan_when_insufficient_history():
    s = _series()
    # 시작 직후 → 12개월 전 데이터 없음
    assert np.isnan(momentum_score(s, pd.Timestamp("2020-02-01"), 12, 1))
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_momentum_score.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'strategy.momentum'`

- [ ] **Step 3: 최소 구현**

```python
# strategy/momentum.py
import numpy as np
import pandas as pd


def _price_asof(series: pd.Series, date: pd.Timestamp) -> float:
    """date 이전(포함) 마지막 유효 가격. 없으면 NaN."""
    s = series.dropna()
    if s.empty:
        return np.nan
    idx = s.index[s.index <= date]
    if len(idx) == 0:
        return np.nan
    return float(s.loc[idx[-1]])


def momentum_score(prices: pd.Series, as_of, lookback_months: int,
                    skip_months: int) -> float:
    """(t - skip) 가격 / (t - lookback) 가격 - 1. 데이터 부족 시 NaN."""
    as_of = pd.Timestamp(as_of)
    p_recent = _price_asof(prices, as_of - pd.DateOffset(months=skip_months))
    p_old = _price_asof(prices, as_of - pd.DateOffset(months=lookback_months))
    if not np.isfinite(p_recent) or not np.isfinite(p_old) or p_old == 0:
        return np.nan
    return p_recent / p_old - 1.0
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_momentum_score.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add strategy/momentum.py tests/test_momentum_score.py
git commit -m "feat: 모멘텀 점수 momentum_score + _price_asof"
```

---

### Task 4: strategy/momentum.py — 점수 집계·랭킹·목표비중

**Files:**
- Modify: `strategy/momentum.py` (함수 추가)
- Test: `tests/test_momentum_select.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_momentum_select.py
import numpy as np
import pandas as pd
from strategy.momentum import compute_scores, select_top_k, target_weights


def test_compute_scores_per_column():
    idx = pd.date_range("2020-01-01", "2021-06-30", freq="D")
    n = len(idx)
    panel = pd.DataFrame({
        "A": 100.0 + 0.2 * np.arange(n),   # 가파른 상승
        "B": 100.0 + 0.05 * np.arange(n),  # 완만한 상승
    }, index=idx)
    scores = compute_scores(panel, pd.Timestamp("2021-06-30"), 12, 1)
    assert set(scores.keys()) == {"A", "B"}
    assert scores["A"] > scores["B"]


def test_select_top_k_drops_nan_and_orders_desc():
    scores = {"A": 0.3, "B": np.nan, "C": 0.5, "D": 0.1}
    assert select_top_k(scores, 2) == ["C", "A"]


def test_target_weights_equal_when_absolute_off():
    scores = {"A": 0.3, "C": 0.5}
    w = target_weights(["C", "A"], scores, top_k=3, use_absolute=False,
                        abs_threshold=0.0)
    assert w == {"C": 1 / 3, "A": 1 / 3}  # 슬롯 3개 중 2개만 채움 → 나머지 현금


def test_target_weights_absolute_filter_drops_negative():
    scores = {"A": 0.3, "C": -0.1}
    w = target_weights(["C", "A"], scores, top_k=3, use_absolute=True,
                        abs_threshold=0.0)
    assert w == {"A": 1 / 3}  # C는 절대모멘텀 음수 → 현금
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_momentum_select.py -v`
Expected: FAIL — `ImportError: cannot import name 'compute_scores'`

- [ ] **Step 3: 최소 구현 (strategy/momentum.py 끝에 추가)**

```python
def compute_scores(panel: pd.DataFrame, as_of, lookback_months: int,
                   skip_months: int) -> dict:
    return {
        col: momentum_score(panel[col], as_of, lookback_months, skip_months)
        for col in panel.columns
    }


def select_top_k(scores: dict, top_k: int) -> list:
    valid = {c: s for c, s in scores.items()
             if s is not None and np.isfinite(s)}
    ranked = sorted(valid.items(), key=lambda kv: kv[1], reverse=True)
    return [c for c, _ in ranked[:top_k]]


def target_weights(selected: list, scores: dict, top_k: int,
                   use_absolute: bool, abs_threshold: float) -> dict:
    weights = {}
    for c in selected:
        if use_absolute and not (
            np.isfinite(scores[c]) and scores[c] >= abs_threshold
        ):
            continue  # 슬롯 → 현금
        weights[c] = 1.0 / top_k
    return weights
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_momentum_select.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add strategy/momentum.py tests/test_momentum_select.py
git commit -m "feat: compute_scores·select_top_k·target_weights"
```

---

### Task 5: engine/portfolio.py — 포지션·포트폴리오 상태

**Files:**
- Create: `engine/portfolio.py`
- Test: `tests/test_portfolio.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_portfolio.py
import numpy as np
from engine.portfolio import Portfolio, Position


def test_equity_cash_only():
    pf = Portfolio(cash=1_000_000.0)
    assert pf.equity({}) == 1_000_000.0


def test_equity_with_positions():
    pf = Portfolio(cash=500_000.0)
    pf.positions["X"] = Position(shares=10.0, entry_price=10_000.0)
    # 종가 12,000 → 평가 120,000 + 현금 500,000
    assert pf.equity({"X": 12_000.0}) == 620_000.0


def test_equity_ignores_nan_price():
    pf = Portfolio(cash=100_000.0)
    pf.positions["X"] = Position(shares=10.0, entry_price=10_000.0)
    assert pf.equity({"X": np.nan}) == 100_000.0
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_portfolio.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'engine.portfolio'`

- [ ] **Step 3: 최소 구현**

```python
# engine/portfolio.py
from dataclasses import dataclass, field

import numpy as np


@dataclass
class Position:
    shares: float
    entry_price: float


@dataclass
class Portfolio:
    cash: float
    positions: dict = field(default_factory=dict)  # code -> Position

    def equity(self, prices: dict) -> float:
        total = self.cash
        for code, pos in self.positions.items():
            px = prices.get(code, np.nan)
            if px is not None and np.isfinite(px):
                total += pos.shares * px
        return total
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_portfolio.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add engine/portfolio.py tests/test_portfolio.py
git commit -m "feat: Portfolio·Position 상태 컨테이너"
```

---

### Task 6: engine/backtest.py — 체결 헬퍼 (_buy/_sell/_rebalance)

**Files:**
- Create: `engine/backtest.py`
- Test: `tests/test_backtest_helpers.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_backtest_helpers.py
import numpy as np
import pandas as pd
from config import BacktestConfig
from engine.portfolio import Portfolio, Position
from engine.backtest import _buy, _sell, _rebalance


def _cfg():
    return BacktestConfig(commission_rate=0.0, slippage_rate=0.0)


def test_buy_creates_position_and_deducts_cash():
    pf = Portfolio(cash=1_000_000.0)
    trades = []
    _buy(pf, "A", price=1000.0, notional=300_000.0, config=_cfg(),
         trades=trades, date=pd.Timestamp("2020-01-02"), reason="rebalance")
    assert pf.positions["A"].shares == 300.0
    assert pf.positions["A"].entry_price == 1000.0
    assert pf.cash == 700_000.0
    assert trades[0]["side"] == "BUY"


def test_sell_closes_position_and_adds_cash():
    pf = Portfolio(cash=0.0)
    pf.positions["A"] = Position(shares=100.0, entry_price=1000.0)
    trades = []
    _sell(pf, "A", price=1200.0, config=_cfg(), trades=trades,
          date=pd.Timestamp("2020-02-01"), reason="take_profit")
    assert "A" not in pf.positions
    assert pf.cash == 120_000.0
    assert trades[0]["side"] == "SELL" and trades[0]["reason"] == "take_profit"


def test_cost_reduces_proceeds_and_cash():
    cfg = BacktestConfig(commission_rate=0.001, slippage_rate=0.0)
    pf = Portfolio(cash=0.0)
    pf.positions["A"] = Position(shares=100.0, entry_price=1000.0)
    _sell(pf, "A", price=1000.0, config=cfg, trades=[],
          date=pd.Timestamp("2020-02-01"), reason="rebalance")
    # 100,000 - 0.1% = 100,000 - 100
    assert pf.cash == 99_900.0


def test_rebalance_resets_to_target_weights_at_open():
    cfg = _cfg()
    pf = Portfolio(cash=0.0)
    pf.positions["OLD"] = Position(shares=100.0, entry_price=1000.0)
    opens = pd.Series({"OLD": 1000.0, "A": 500.0, "B": 250.0})
    trades = []
    _rebalance(pf, {"A": 1 / 3, "B": 1 / 3}, opens, cfg, trades,
               pd.Timestamp("2020-03-02"))
    # OLD 매도 → 현금 100,000. A에 1/3, B에 1/3 투입.
    assert "OLD" not in pf.positions
    assert round(pf.positions["A"].shares, 6) == round((100_000 / 3) / 500.0, 6)
    assert round(pf.positions["B"].shares, 6) == round((100_000 / 3) / 250.0, 6)
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_backtest_helpers.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'engine.backtest'`

- [ ] **Step 3: 최소 구현**

```python
# engine/backtest.py
import numpy as np
import pandas as pd

from engine.costs import trade_cost
from engine.portfolio import Portfolio, Position
from strategy.momentum import compute_scores, select_top_k, target_weights


def _buy(pf, code, price, notional, config, trades, date, reason):
    if notional <= 0 or not np.isfinite(price) or price <= 0:
        return
    shares = notional / price
    cost = trade_cost(notional, config.commission_rate, config.slippage_rate)
    pf.cash -= notional + cost
    pf.positions[code] = Position(shares=shares, entry_price=price)
    trades.append({"date": date, "code": code, "side": "BUY",
                   "shares": shares, "price": price, "cost": cost,
                   "reason": reason})


def _sell(pf, code, price, config, trades, date, reason):
    if code not in pf.positions or not np.isfinite(price):
        return
    pos = pf.positions.pop(code)
    proceeds = pos.shares * price
    cost = trade_cost(proceeds, config.commission_rate, config.slippage_rate)
    pf.cash += proceeds - cost
    trades.append({"date": date, "code": code, "side": "SELL",
                   "shares": pos.shares, "price": price, "cost": cost,
                   "reason": reason})


def _rebalance(pf, weights, opens, config, trades, date):
    for code in list(pf.positions):
        _sell(pf, code, opens.get(code, np.nan), config, trades, date,
              "rebalance")
    investable = pf.cash
    for code, w in weights.items():
        px = opens.get(code, np.nan)
        if np.isfinite(px) and px > 0:
            _buy(pf, code, px, investable * w, config, trades, date,
                 "rebalance")
```

> 참고: `opens`는 `pd.Series` (인덱스=종목코드). `opens.get(code, np.nan)`은 결측·미상장 종목에 NaN을 돌려주어 `_buy`/`_sell`이 자동 스킵한다.

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_backtest_helpers.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add engine/backtest.py tests/test_backtest_helpers.py
git commit -m "feat: 체결 헬퍼 _buy·_sell·_rebalance"
```

---

### Task 7: engine/backtest.py — 일봉 루프 run_backtest

**Files:**
- Modify: `engine/backtest.py` (함수 추가)
- Test: `tests/test_backtest_loop.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_backtest_loop.py
import numpy as np
import pandas as pd
from config import BacktestConfig
from engine.backtest import run_backtest, _first_trading_day_of_month


def test_first_trading_day_flags():
    dates = pd.to_datetime(["2020-01-02", "2020-01-03", "2020-02-03",
                            "2020-02-04", "2020-03-02"])
    flags = _first_trading_day_of_month(dates)
    assert list(flags.values) == [True, False, True, False, True]


def _panels():
    # 18개월 일봉. A는 강한 상승, B는 횡보, C는 하락.
    idx = pd.date_range("2020-01-01", "2021-06-30", freq="B")
    n = len(idx)
    close = pd.DataFrame({
        "A": 100.0 * (1.0 + 0.0015) ** np.arange(n),
        "B": np.full(n, 100.0),
        "C": 100.0 * (1.0 - 0.0010) ** np.arange(n),
    }, index=idx)
    # 시가 = 전일 종가 근사 (간단화: 종가와 동일하게 둠)
    return close, close.copy()


def test_run_backtest_returns_curve_and_trades():
    close, opens = _panels()
    cfg = BacktestConfig(top_k=1, use_take_profit=False,
                         use_absolute_momentum=False,
                         commission_rate=0.0, slippage_rate=0.0,
                         initial_capital=1_000_000.0)
    curve, trades = run_backtest(close, opens, cfg)
    assert isinstance(curve, pd.Series)
    assert curve.index.is_monotonic_increasing
    assert curve.iloc[0] == 1_000_000.0
    # 강한 상승 A를 골라야 하므로 최종 자산 > 초기 자산
    assert curve.iloc[-1] > curve.iloc[0]
    assert len(trades) > 0
    assert all(t["side"] in ("BUY", "SELL") for t in trades)


def test_take_profit_triggers_sell_with_reason():
    close, opens = _panels()
    cfg = BacktestConfig(top_k=1, use_take_profit=True,
                         take_profit_pct=0.05,
                         use_absolute_momentum=False,
                         commission_rate=0.0, slippage_rate=0.0)
    _, trades = run_backtest(close, opens, cfg)
    assert any(t["reason"] == "take_profit" for t in trades)


def test_absolute_momentum_goes_to_cash_when_all_negative():
    idx = pd.date_range("2020-01-01", "2021-06-30", freq="B")
    n = len(idx)
    # 모든 종목 하락 → 절대 모멘텀 음수 → 전량 현금 유지
    close = pd.DataFrame({
        "A": 100.0 * (1.0 - 0.001) ** np.arange(n),
        "B": 100.0 * (1.0 - 0.002) ** np.arange(n),
    }, index=idx)
    cfg = BacktestConfig(top_k=2, use_take_profit=False,
                         use_absolute_momentum=True,
                         absolute_momentum_threshold=0.0,
                         commission_rate=0.0, slippage_rate=0.0,
                         initial_capital=1_000_000.0)
    curve, _ = run_backtest(close, close.copy(), cfg)
    # 현금만 보유 → 자산곡선 평탄
    assert curve.iloc[-1] == 1_000_000.0
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_backtest_loop.py -v`
Expected: FAIL — `ImportError: cannot import name 'run_backtest'`

- [ ] **Step 3: 최소 구현 (engine/backtest.py 끝에 추가)**

```python
def _first_trading_day_of_month(dates) -> pd.Series:
    seen = set()
    flags = []
    for d in dates:
        key = (d.year, d.month)
        flags.append(key not in seen)
        seen.add(key)
    return pd.Series(flags, index=dates)


def run_backtest(close_panel, open_panel, config):
    """일봉 루프. 신호는 종가에 산출, 체결은 다음 거래일 시가.

    반환: (equity_curve: pd.Series, trades: list[dict])
    """
    dates = close_panel.index
    pf = Portfolio(cash=config.initial_capital)
    pending = None  # None | ("rebalance", weights) | ("sell", [codes])
    trades = []
    equity = {}
    is_rebal = _first_trading_day_of_month(dates)

    for d in dates:
        opens = open_panel.loc[d]
        closes = close_panel.loc[d]

        # 1) 전일 산출 신호를 오늘 시가에 체결
        if pending is not None:
            kind = pending[0]
            if kind == "sell":
                for code in pending[1]:
                    _sell(pf, code, opens.get(code, np.nan), config,
                          trades, d, "take_profit")
            elif kind == "rebalance":
                _rebalance(pf, pending[1], opens, config, trades, d)
            pending = None

        # 2) 종가 기준 평가금액 기록
        equity[d] = pf.equity({c: closes.get(c, np.nan)
                               for c in close_panel.columns})

        # 3) 다음 거래일 체결할 신호 산출
        if is_rebal.loc[d]:
            scores = compute_scores(close_panel.loc[:d], d,
                                    config.momentum_lookback_months,
                                    config.momentum_skip_months)
            selected = select_top_k(scores, config.top_k)
            weights = target_weights(selected, scores, config.top_k,
                                     config.use_absolute_momentum,
                                     config.absolute_momentum_threshold)
            pending = ("rebalance", weights)
        elif config.use_take_profit:
            tp = []
            for code, pos in pf.positions.items():
                px = closes.get(code, np.nan)
                if (np.isfinite(px)
                        and px / pos.entry_price - 1.0
                        >= config.take_profit_pct):
                    tp.append(code)
            if tp:
                pending = ("sell", tp)

    return pd.Series(equity).sort_index(), trades
```

> 마지막 거래일에 산출된 `pending`은 "다음 거래일"이 없어 체결되지 않고 버려진다 (의도된 동작, 설계 문서 §6.3).

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_backtest_loop.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add engine/backtest.py tests/test_backtest_loop.py
git commit -m "feat: 일봉 루프 run_backtest (월 리밸런싱 + 익절 + 절대모멘텀)"
```

---

### Task 8: engine/backtest.py — 벤치마크 곡선

**Files:**
- Modify: `engine/backtest.py` (함수 추가)
- Test: `tests/test_benchmark.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_benchmark.py
import numpy as np
import pandas as pd
from engine.backtest import benchmark_curve


def test_benchmark_is_normalized_buy_and_hold():
    idx = pd.date_range("2020-01-01", periods=4, freq="B")
    s = pd.Series([100.0, 110.0, 90.0, 120.0], index=idx)
    curve = benchmark_curve(s, initial_capital=1_000_000.0)
    assert curve.iloc[0] == 1_000_000.0
    assert curve.iloc[1] == 1_100_000.0
    assert curve.iloc[-1] == 1_200_000.0


def test_benchmark_drops_leading_nan():
    idx = pd.date_range("2020-01-01", periods=3, freq="B")
    s = pd.Series([np.nan, 100.0, 150.0], index=idx)
    curve = benchmark_curve(s, initial_capital=1_000_000.0)
    assert curve.iloc[0] == 1_000_000.0
    assert curve.iloc[-1] == 1_500_000.0
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_benchmark.py -v`
Expected: FAIL — `ImportError: cannot import name 'benchmark_curve'`

- [ ] **Step 3: 최소 구현 (engine/backtest.py 끝에 추가)**

```python
def benchmark_curve(close_series: pd.Series, initial_capital: float) -> pd.Series:
    """벤치마크 ETF 매수후보유 가격수익률 곡선."""
    s = close_series.dropna()
    if s.empty:
        return pd.Series(dtype=float)
    return initial_capital * s / s.iloc[0]
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_benchmark.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add engine/backtest.py tests/test_benchmark.py
git commit -m "feat: 벤치마크 매수후보유 곡선 benchmark_curve"
```

---

### Task 9: metrics/performance.py — 성과 지표

**Files:**
- Create: `metrics/performance.py`
- Test: `tests/test_performance.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_performance.py
import numpy as np
import pandas as pd
from metrics.performance import (total_return, cagr, max_drawdown,
                                 sharpe, summarize)


def test_total_return():
    s = pd.Series([100.0, 150.0])
    assert total_return(s) == 0.5


def test_cagr_two_years_doubling():
    idx = pd.to_datetime(["2020-01-01", "2022-01-01"])
    s = pd.Series([100.0, 400.0], index=idx)
    # 2년에 4배 → CAGR = 100%
    assert round(cagr(s), 4) == 1.0


def test_max_drawdown():
    s = pd.Series([100.0, 120.0, 60.0, 90.0])
    # 고점 120 → 저점 60 = -50%
    assert round(max_drawdown(s), 4) == -0.5


def test_sharpe_zero_when_no_volatility():
    idx = pd.date_range("2020-01-01", periods=10, freq="B")
    s = pd.Series(np.full(10, 100.0), index=idx)
    assert sharpe(s) == 0.0


def test_summarize_returns_expected_keys():
    idx = pd.date_range("2020-01-01", periods=300, freq="B")
    s = pd.Series(100.0 * (1.0 + 0.001) ** np.arange(300), index=idx)
    out = summarize(s, trades=[{"side": "BUY"}, {"side": "SELL"}])
    for key in ("total_return", "cagr", "max_drawdown", "sharpe",
                "sortino", "volatility", "num_trades"):
        assert key in out
    assert out["num_trades"] == 2
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_performance.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'metrics.performance'`

- [ ] **Step 3: 최소 구현**

```python
# metrics/performance.py
import numpy as np
import pandas as pd

_PPY = 252  # 연간 거래일


def total_return(equity: pd.Series) -> float:
    return float(equity.iloc[-1] / equity.iloc[0] - 1.0)


def cagr(equity: pd.Series) -> float:
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    if years <= 0:
        return 0.0
    return float((equity.iloc[-1] / equity.iloc[0]) ** (1.0 / years) - 1.0)


def max_drawdown(equity: pd.Series) -> float:
    roll_max = equity.cummax()
    dd = equity / roll_max - 1.0
    return float(dd.min())


def _returns(equity: pd.Series) -> pd.Series:
    return equity.pct_change().dropna()


def sharpe(equity: pd.Series, rf: float = 0.0) -> float:
    r = _returns(equity)
    if len(r) == 0 or r.std() == 0:
        return 0.0
    excess = r.mean() - rf / _PPY
    return float(excess / r.std() * np.sqrt(_PPY))


def sortino(equity: pd.Series, rf: float = 0.0) -> float:
    r = _returns(equity)
    downside = r[r < 0]
    if len(downside) == 0 or downside.std() == 0:
        return 0.0
    excess = r.mean() - rf / _PPY
    return float(excess / downside.std() * np.sqrt(_PPY))


def volatility(equity: pd.Series) -> float:
    r = _returns(equity)
    return float(r.std() * np.sqrt(_PPY))


def yearly_returns(equity: pd.Series) -> pd.Series:
    yearly = equity.resample("YE").last()
    out = yearly.pct_change()
    out.iloc[0] = yearly.iloc[0] / equity.iloc[0] - 1.0
    out.index = out.index.year
    return out


def summarize(equity: pd.Series, trades: list) -> dict:
    return {
        "total_return": total_return(equity),
        "cagr": cagr(equity),
        "max_drawdown": max_drawdown(equity),
        "sharpe": sharpe(equity),
        "sortino": sortino(equity),
        "volatility": volatility(equity),
        "num_trades": len(trades),
    }
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_performance.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add metrics/performance.py tests/test_performance.py
git commit -m "feat: 성과 지표 (CAGR·MDD·Sharpe·Sortino·요약)"
```

---

### Task 10: data/loader.py — 시세 로더 + 캐시

**Files:**
- Create: `data/loader.py`
- Test: `tests/test_loader.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_loader.py
import pandas as pd
from data.loader import load_prices, build_panels


def _fake_fetch(code, start, end):
    idx = pd.date_range("2020-01-01", periods=5, freq="B")
    base = 100.0 if code == "AAA" else 200.0
    return pd.DataFrame({"Open": base, "Close": base + 1}, index=idx)


def test_load_prices_filters_date_range(tmp_path):
    df = load_prices("AAA", "2020-01-02", "2020-01-03",
                     cache_dir=str(tmp_path), fetch_fn=_fake_fetch)
    assert df.index.min() >= pd.Timestamp("2020-01-02")
    assert df.index.max() <= pd.Timestamp("2020-01-03")


def test_load_prices_writes_and_reads_cache(tmp_path):
    load_prices("AAA", "2020-01-01", "2020-01-31",
                cache_dir=str(tmp_path), fetch_fn=_fake_fetch)
    assert (tmp_path / "AAA.csv").exists()

    def _boom(*a, **k):
        raise AssertionError("fetch must not be called when cache exists")

    df = load_prices("AAA", "2020-01-01", "2020-01-31",
                     cache_dir=str(tmp_path), fetch_fn=_boom)
    assert len(df) == 5


def test_build_panels_aligns_close_and_open(tmp_path):
    close, opens = build_panels(["AAA", "BBB"], "2020-01-01", "2020-01-31",
                                cache_dir=str(tmp_path), fetch_fn=_fake_fetch)
    assert list(close.columns) == ["AAA", "BBB"]
    assert close.index.equals(opens.index)
    assert close.loc[close.index[0], "AAA"] == 101.0
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_loader.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'data.loader'`

- [ ] **Step 3: 최소 구현**

```python
# data/loader.py
import os

import pandas as pd


def _cache_path(cache_dir: str, code: str) -> str:
    return os.path.join(cache_dir, f"{code}.csv")


def fdr_fetch(code: str, start: str, end: str) -> pd.DataFrame:
    import FinanceDataReader as fdr
    return fdr.DataReader(code, start, end)


def load_prices(code, start, end, cache_dir, fetch_fn=fdr_fetch) -> pd.DataFrame:
    path = _cache_path(cache_dir, code)
    if os.path.exists(path):
        df = pd.read_csv(path, index_col=0, parse_dates=True)
    else:
        df = fetch_fn(code, start, end)
        os.makedirs(cache_dir, exist_ok=True)
        df.to_csv(path)
    mask = (df.index >= pd.Timestamp(start)) & (df.index <= pd.Timestamp(end))
    return df.loc[mask]


def build_panels(codes, start, end, cache_dir, fetch_fn=fdr_fetch):
    closes, opens = {}, {}
    for code in codes:
        df = load_prices(code, start, end, cache_dir, fetch_fn)
        closes[code] = df["Close"]
        opens[code] = df["Open"]
    close_panel = pd.DataFrame(closes).sort_index()
    open_panel = pd.DataFrame(opens).reindex(close_panel.index)
    return close_panel, open_panel
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_loader.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add data/loader.py tests/test_loader.py
git commit -m "feat: 시세 로더 + CSV 캐시 (fetch 주입)"
```

---

### Task 11: data/universe.py — 이름→종목코드 매핑

**Files:**
- Create: `data/universe.py`
- Test: `tests/test_universe.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_universe.py
import pandas as pd
from data.universe import match_codes


def _listing():
    return pd.DataFrame({
        "Symbol": ["360750", "381170", "999999"],
        "Name": ["TIGER 미국S&P500", "TIGER 미국테크TOP10 INDXX",
                 "기타 ETF"],
    })


def test_match_exact_ignoring_spaces():
    out = match_codes(["TIGER 미국S&P500"], _listing())
    assert out["TIGER 미국S&P500"] == "360750"


def test_match_handles_space_differences():
    out = match_codes(["TIGER 미국테크TOP10INDXX"], _listing())
    assert out["TIGER 미국테크TOP10INDXX"] == "381170"


def test_unmatched_name_returns_none():
    out = match_codes(["존재하지않는ETF"], _listing())
    assert out["존재하지않는ETF"] is None
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_universe.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'data.universe'`

- [ ] **Step 3: 최소 구현**

```python
# data/universe.py
import pandas as pd


def _norm(s: str) -> str:
    return str(s).replace(" ", "")


def match_codes(names, listing_df: pd.DataFrame) -> dict:
    """ETF 이름 리스트 → {이름: 종목코드 or None}. 공백 무시 매칭."""
    norm_names = listing_df["Name"].map(_norm)
    out = {}
    for name in names:
        target = _norm(name)
        exact = listing_df[norm_names == target]
        if len(exact) > 0:
            out[name] = str(exact.iloc[0]["Symbol"])
            continue
        contains = listing_df[norm_names.str.contains(target, regex=False)]
        out[name] = str(contains.iloc[0]["Symbol"]) if len(contains) else None
    return out


def load_listing() -> pd.DataFrame:
    import FinanceDataReader as fdr
    return fdr.StockListing("ETF/KR")
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_universe.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add data/universe.py tests/test_universe.py
git commit -m "feat: ETF 이름→종목코드 매핑 match_codes"
```

---

### Task 12: report/report.py — 리포트 출력

**Files:**
- Create: `report/report.py`
- Test: `tests/test_report.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_report.py
import numpy as np
import pandas as pd
from report.report import format_summary_table, write_report


def test_format_summary_table_contains_metrics():
    summary = {"total_return": 0.42, "cagr": 0.15, "max_drawdown": -0.2,
               "sharpe": 1.1, "sortino": 1.4, "volatility": 0.18,
               "num_trades": 12}
    txt = format_summary_table(summary)
    assert "CAGR" in txt
    assert "15.00%" in txt
    assert "12" in txt


def test_write_report_creates_files(tmp_path):
    idx = pd.date_range("2020-01-01", periods=50, freq="B")
    strat = pd.Series(1_000_000.0 * (1.0 + 0.001) ** np.arange(50), index=idx)
    bench = pd.Series(1_000_000.0 * (1.0 + 0.0005) ** np.arange(50), index=idx)
    trades = [{"date": idx[0], "code": "A", "side": "BUY", "shares": 1.0,
               "price": 100.0, "cost": 0.0, "reason": "rebalance"}]
    summary = {"total_return": 0.05, "cagr": 0.05, "max_drawdown": -0.01,
               "sharpe": 1.0, "sortino": 1.2, "volatility": 0.1,
               "num_trades": 1}
    out = write_report(strat, bench, trades, summary, str(tmp_path))
    assert (tmp_path / "equity_curve.png").exists()
    assert (tmp_path / "trades.csv").exists()
    assert (tmp_path / "summary.html").exists()
    assert "CAGR" in out
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_report.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'report.report'`

- [ ] **Step 3: 최소 구현**

```python
# report/report.py
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_report.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add report/report.py tests/test_report.py
git commit -m "feat: 리포트 (요약표·차트·거래CSV·HTML)"
```

---

### Task 13: run_backtest.py — CLI 진입점

**Files:**
- Create: `run_backtest.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_cli.py
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
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'run_backtest'`

- [ ] **Step 3: 최소 구현**

```python
# run_backtest.py
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_cli.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: 전체 테스트 스위트 확인**

Run: `pytest -v`
Expected: 모든 테스트 PASS (전 모듈 합산)

- [ ] **Step 6: Commit**

```bash
git add run_backtest.py tests/test_cli.py
git commit -m "feat: CLI 진입점 run_backtest (익절 비교 모드 포함)"
```

---

### Task 14: 실데이터 스모크 실행 (수동 검증)

**Files:** (없음 — 실행 검증만)

- [ ] **Step 1: 실데이터 백테스트 실행**

Run: `python run_backtest.py --start 2021-01-01`
Expected: 콘솔 요약표 출력, `report_output/` 에 `equity_curve.png`, `trades.csv`, `summary.html` 생성. 네트워크 통해 FinanceDataReader가 ETF 시세를 받아오고, `data/cache/`에 종목별 CSV 캐시 생성.

- [ ] **Step 2: 익절 비교 모드 실행**

Run: `python run_backtest.py --start 2021-01-01 --compare-tp`
Expected: 익절 ON / OFF 두 요약표가 각각 출력되고 `report_output_tp_on/`, `report_output_tp_off/` 생성.

- [ ] **Step 3: 결과 육안 점검**

`report_output/summary.html`을 열어 자산곡선이 정상(우상향/하락 구간 합리적), 거래로그(`trades.csv`)에 `rebalance`/`take_profit` 사유가 보이는지 확인. 일부 ETF(2023~2024 상장)는 초기 구간 NaN으로 빠지는 것이 정상 (동적 유니버스, 설계 문서 §3).

- [ ] **Step 4: 종목코드 매핑 검증**

`code_by_name` 결과에서 `None`이 있으면 해당 ETF 이름이 FinanceDataReader 목록과 다르다는 뜻. `config.py`의 이름을 실제 상장 명칭으로 보정 후 재실행. (설계 문서 §3의 수동 오버라이드 허용 항목)

- [ ] **Step 5: Commit (캐시 제외)**

`.gitignore`가 `data/cache/`, `report_output/`를 제외하므로 새로 커밋할 소스 변경이 없으면 생략. `config.py` 이름 보정이 있었다면:

```bash
git add config.py
git commit -m "fix: ETF 이름을 FinanceDataReader 상장명에 맞게 보정"
```

---

## Self-Review

**1. Spec coverage:**

| 설계 문서 항목 | 구현 태스크 |
|---|---|
| §3 ETF 유니버스 + 코드 매핑 | Task 1, Task 11 |
| §3 동적 유니버스 (상장 전 NaN) | Task 3 (`_price_asof` NaN), Task 7 (`select_top_k` NaN drop) |
| §4.1 상대 모멘텀 12-1 | Task 3, Task 4 |
| §4.2 절대 모멘텀 하방 방어 | Task 4 (`target_weights`), Task 7 (테스트) |
| §4.3 +5% 익절 (종가 판단→다음날 시가) | Task 7 |
| §4.4 거래비용 | Task 2, Task 6 |
| §5 백테스트 사양·벤치마크 | Task 7, Task 8 |
| §6 아키텍처/모듈 경계 | Task 0–13 |
| §6.3 엣지 케이스 (현금 전환, 미상장, 마지막날) | Task 7 |
| §7 산출물 (표·차트·CSV·HTML) | Task 12 |
| §7 익절 ON/OFF 비교 | Task 13 |
| §9 테스트 전략 | 전 태스크 TDD |

모든 spec 항목이 태스크에 매핑됨. 누락 없음.

**2. Placeholder scan:** "TBD"/"TODO"/"적절히 처리" 없음. 모든 코드 스텝에 완전한 코드 포함.

**3. Type consistency:**
- `BacktestConfig` 필드명(`commission_rate`, `slippage_rate`, `top_k`, `use_take_profit`, `take_profit_pct`, `use_absolute_momentum`, `absolute_momentum_threshold`, `momentum_lookback_months`, `momentum_skip_months`, `cache_dir`, `start_date`, `end_date`, `initial_capital`, `benchmark_name`, `universe`)이 Task 1 정의와 Task 6/7/13 사용에서 일치.
- `_buy`/`_sell`/`_rebalance` 시그니처가 Task 6 정의와 Task 7 호출에서 일치.
- `run_backtest` 반환 `(pd.Series, list)`이 Task 7 정의와 Task 13 사용에서 일치.
- `summarize` 키가 Task 9 정의와 Task 12 `_ROWS` / Task 12 테스트에서 일치.
- `Position(shares, entry_price)` 생성자가 Task 5 정의와 Task 6 사용에서 일치.

불일치 없음.

---

## Execution Handoff

이 계획은 14개 태스크, 각 태스크는 TDD 5단계(테스트 작성 → 실패 확인 → 구현 → 통과 확인 → 커밋)로 분해되어 있습니다.
