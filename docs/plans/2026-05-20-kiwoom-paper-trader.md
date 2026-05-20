# 키움 모의투자 자동매매 GUI 앱 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 검증된 듀얼 모멘텀 + 익절 전략을 키움 모의투자 계좌에서 자동 실행하는 Tkinter GUI 앱을 기존 `stock-backtest` 저장소에 추가한다.

**Architecture:** 순수 결정 엔진(`live.runner` — 백테스트 전략 재사용) / 부수효과 격리(`live.executor` + `broker.kiwoom`) / 영속 상태(`live.state`) / 안전장치(`live.safety`) / 백그라운드 스케줄러(`live.scheduler`) / Tkinter GUI(`gui.*`). PAPER 모드를 코드 차원에서 강제하고, 불확실 시 NOOP+halt(fail-safe)로 이중주문·추측주문을 방지한다.

**Tech Stack:** Python 3.11+, requests (REST), Tkinter (stdlib), pandas/numpy/FinanceDataReader (재사용), pytest

프로젝트 루트: `C:\Users\ASUS\Desktop\stock-backtest`. 환경(Windows PowerShell): venv `.venv` 이미 존재. 모든 명령은 venv의 python으로 실행.
`Push-Location C:\Users\ASUS\Desktop\stock-backtest; .\.venv\Scripts\python.exe -m pytest -v; Pop-Location`

---

## File Structure

| 파일 | 책임 |
|---|---|
| `broker/credentials.py` | secrets/env에서 자격증명 로드, PAPER 모드 강제 |
| `broker/kiwoom.py` | 키움 REST 클라이언트(토큰·시세·잔고·보유·주문), http 주입 |
| `live/errors.py` | 도메인 예외 계층 |
| `live/state.py` | Holding/TraderState/TraderParams + 원자적 JSON 영속화 |
| `live/universe_store.py` | 사용자 편집 ETF 목록 JSON 영속화 |
| `live/safety.py` | 시간·한도·킬스위치·드리프트 순수 함수 |
| `live/runner.py` | Decision 산출(REBALANCE/TAKE_PROFIT/NOOP) — 전략 재사용 |
| `live/executor.py` | Decision 실행 + 상태 갱신 + fail-safe halt |
| `live/scheduler.py` | 백그라운드 스케줄러 + `should_trigger` 순수 판정 |
| `gui/panels.py` | 종목 편집·파라미터·로그 위젯 |
| `gui/app.py` | Tk 메인 창, 모드 표시, 시작/정지, 스레드 브리지 |
| `run_trader.py` | 진입점 |
| `secrets/.gitkeep`, `state/.gitkeep` | gitignore되는 보관 디렉터리 |

순수 모듈(테스트 100% 결정적): `credentials`, `errors`, `state`, `universe_store`, `safety`, `runner`, `scheduler.should_trigger`. 부수효과 모듈: `kiwoom`(http 주입), `executor`(broker 주입), `scheduler.Scheduler`(thread), `gui.*`.

---

### Task 0: 스캐폴딩

**Files:**
- Modify: `requirements.txt`, `.gitignore`
- Create: `broker/__init__.py`, `live/__init__.py`, `gui/__init__.py`, `secrets/.gitkeep`, `state/.gitkeep`

- [ ] **Step 1: requirements.txt에 `requests` 추가**

```
finance-datareader>=0.9.96
pandas>=2.2
numpy>=1.26
matplotlib>=3.8
pytest>=8.0
requests>=2.32
```

- [ ] **Step 2: 패키지 dir + .gitkeep 생성**

`broker/__init__.py`, `live/__init__.py`, `gui/__init__.py` 내용: `# package` (한 줄)
`secrets/.gitkeep`, `state/.gitkeep` 내용: 빈 파일

- [ ] **Step 3: .gitignore에 secrets/state 추가**

기존 `.gitignore` 끝에 다음 두 줄 추가 (이미 있는 항목은 유지):
```
secrets/*
!secrets/.gitkeep
state/*
!state/.gitkeep
```

- [ ] **Step 4: 의존성 설치**

Run: `C:\Users\ASUS\Desktop\stock-backtest\.venv\Scripts\python.exe -m pip install -r C:\Users\ASUS\Desktop\stock-backtest\requirements.txt`
Expected: `requests`가 새로 설치되거나 "already satisfied"

- [ ] **Step 5: Commit**

```bash
git -C C:\Users\ASUS\Desktop\stock-backtest add requirements.txt .gitignore broker/__init__.py live/__init__.py gui/__init__.py secrets/.gitkeep state/.gitkeep
git -C C:\Users\ASUS\Desktop\stock-backtest commit -m "chore: 키움 트레이더 스캐폴딩(패키지·secrets/state gitignore·requests)"
```

---

### Task 1: live/errors.py — 도메인 예외

**Files:**
- Create: `live/errors.py`
- Test: `tests/test_errors.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_errors.py
import pytest
from live.errors import (TraderError, SafetyError, BrokerError,
                          CredentialsError, StateError)


def test_all_inherit_trader_error():
    assert issubclass(SafetyError, TraderError)
    assert issubclass(BrokerError, TraderError)
    assert issubclass(CredentialsError, TraderError)
    assert issubclass(StateError, TraderError)


def test_can_raise_and_catch_as_trader_error():
    with pytest.raises(TraderError):
        raise SafetyError("test")
```

- [ ] **Step 2: 실패 확인**

Run: `Push-Location C:\Users\ASUS\Desktop\stock-backtest; .\.venv\Scripts\python.exe -m pytest tests/test_errors.py -v; Pop-Location`
Expected: FAIL — `ModuleNotFoundError: No module named 'live.errors'`

- [ ] **Step 3: 구현**

```python
# live/errors.py
class TraderError(Exception):
    """Base exception for the live trader."""


class SafetyError(TraderError):
    """Safety check failed (mode, limits, drift, kill-switch)."""


class BrokerError(TraderError):
    """Broker API call failed or returned unexpected response."""


class CredentialsError(TraderError):
    """Credentials missing, malformed, or disallowed mode."""


class StateError(TraderError):
    """State file corrupted or invariant violated."""
```

- [ ] **Step 4: 통과 확인**

Run: `Push-Location C:\Users\ASUS\Desktop\stock-backtest; .\.venv\Scripts\python.exe -m pytest tests/test_errors.py -v; Pop-Location`
Expected: PASS (2)

- [ ] **Step 5: Commit**

```bash
git -C C:\Users\ASUS\Desktop\stock-backtest add live/errors.py tests/test_errors.py
git -C C:\Users\ASUS\Desktop\stock-backtest commit -m "feat: 도메인 예외 계층(TraderError + 4종)"
```

---

### Task 2: broker/credentials.py — 자격증명 로더 + PAPER 강제

**Files:**
- Create: `broker/credentials.py`
- Test: `tests/test_credentials.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_credentials.py
import json
import pytest
from broker.credentials import Credentials
from live.errors import CredentialsError


def _write(tmp_path, data):
    p = tmp_path / "kiwoom.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_load_from_file(tmp_path):
    p = _write(tmp_path, {"mode": "paper",
                          "base_url": "https://mock.kiwoom.com",
                          "app_key": "K", "app_secret": "S",
                          "account_no": "1234"})
    c = Credentials.load(secrets_path=p)
    assert c.mode == "paper" and c.app_key == "K"
    assert c.account_no == "1234"


def test_load_from_env(tmp_path):
    env = {"KIWOOM_MODE": "paper",
           "KIWOOM_BASE_URL": "https://mock.kiwoom.com",
           "KIWOOM_APP_KEY": "K2", "KIWOOM_APP_SECRET": "S2",
           "KIWOOM_ACCOUNT_NO": "9999"}
    c = Credentials.load(secrets_path=tmp_path / "missing.json", env=env)
    assert c.app_key == "K2" and c.account_no == "9999"


def test_live_mode_rejected_in_this_build(tmp_path):
    p = _write(tmp_path, {"mode": "live", "base_url": "x",
                          "app_key": "K", "app_secret": "S",
                          "account_no": "1"})
    with pytest.raises(CredentialsError):
        Credentials.load(secrets_path=p)


def test_missing_field_raises(tmp_path):
    p = _write(tmp_path, {"mode": "paper"})  # base_url 등 누락
    with pytest.raises(CredentialsError):
        Credentials.load(secrets_path=p)
```

- [ ] **Step 2: 실패 확인**

Run: `Push-Location C:\Users\ASUS\Desktop\stock-backtest; .\.venv\Scripts\python.exe -m pytest tests/test_credentials.py -v; Pop-Location`
Expected: FAIL — `ModuleNotFoundError: No module named 'broker.credentials'`

- [ ] **Step 3: 구현**

```python
# broker/credentials.py
from dataclasses import dataclass
import json
from pathlib import Path

from live.errors import CredentialsError

_REQUIRED = ("mode", "base_url", "app_key", "app_secret", "account_no")
_ENV_KEYS = {
    "mode": "KIWOOM_MODE", "base_url": "KIWOOM_BASE_URL",
    "app_key": "KIWOOM_APP_KEY", "app_secret": "KIWOOM_APP_SECRET",
    "account_no": "KIWOOM_ACCOUNT_NO",
}


@dataclass
class Credentials:
    mode: str
    base_url: str
    app_key: str
    app_secret: str
    account_no: str

    @classmethod
    def load(cls, secrets_path=None, env=None) -> "Credentials":
        data = {}
        p = Path(secrets_path) if secrets_path else None
        if p and p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                raise CredentialsError(f"secrets 파일 손상: {e}") from e
        else:
            e = env or {}
            data = {k: e[v] for k, v in _ENV_KEYS.items() if v in e}
        missing = [k for k in _REQUIRED if not data.get(k)]
        if missing:
            raise CredentialsError(f"자격증명 누락: {missing}")
        if data["mode"] != "paper":
            raise CredentialsError(
                f"이 빌드는 paper 모드만 허용; got mode={data['mode']!r}")
        return cls(**{k: data[k] for k in _REQUIRED})
```

- [ ] **Step 4: 통과 확인**

Run: `Push-Location C:\Users\ASUS\Desktop\stock-backtest; .\.venv\Scripts\python.exe -m pytest tests/test_credentials.py -v; Pop-Location`
Expected: PASS (4)

- [ ] **Step 5: Commit**

```bash
git -C C:\Users\ASUS\Desktop\stock-backtest add broker/credentials.py tests/test_credentials.py
git -C C:\Users\ASUS\Desktop\stock-backtest commit -m "feat: Credentials 로더 + PAPER 모드 강제"
```

---

### Task 3: broker/kiwoom.py — 토큰 + HTTP 주입

**Files:**
- Create: `broker/kiwoom.py`
- Test: `tests/test_kiwoom_token.py`

> 키움 REST 정확한 엔드포인트 경로/필드는 키움 공식 API 포털 문서로 구현 시 확정 필요. 본 단계에서는 `KiwoomEndpoints` 데이터클래스로 경로를 분리하고 기본값을 합리적 추정으로 둔다. 테스트는 가짜 http로 동작 시멘틱(토큰 캐싱·만료·헤더 부착)만 검증한다.

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_kiwoom_token.py
from broker.kiwoom import KiwoomClient


class FakeResp:
    def __init__(self, json_data, status=200):
        self._json = json_data
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")

    def json(self):
        return self._json


class FakeHttp:
    def __init__(self):
        self.calls = []
        self.responses = []

    def post(self, url, json=None, headers=None, timeout=None):
        self.calls.append(("POST", url, json, headers))
        return self.responses.pop(0)

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append(("GET", url, params, headers))
        return self.responses.pop(0)


def _client(http, clock_value=1000.0):
    return KiwoomClient(base_url="https://mock.kiwoom.com",
                        app_key="K", app_secret="S", account_no="1",
                        http=http, clock=lambda: clock_value)


def test_get_token_calls_endpoint_and_caches():
    http = FakeHttp()
    http.responses = [FakeResp({"token": "T1", "expires_in": 3600})]
    c = _client(http)
    assert c.get_token() == "T1"
    assert c.get_token() == "T1"  # 두 번째는 캐시
    assert len(http.calls) == 1  # 한 번만 호출


def test_token_refreshes_after_expiry():
    http = FakeHttp()
    http.responses = [FakeResp({"token": "T1", "expires_in": 100}),
                      FakeResp({"token": "T2", "expires_in": 100})]
    calls = []

    def clock():
        return calls and 9999.0 or 1000.0

    c = KiwoomClient(base_url="https://x", app_key="K", app_secret="S",
                     account_no="1", http=http,
                     clock=lambda: 1000.0 if not calls else 9999.0)
    # 첫 호출
    assert c.get_token() == "T1"
    calls.append(1)  # 시계 전진
    # 만료되었으므로 재발급
    assert c.get_token() == "T2"
    assert len(http.calls) == 2
```

- [ ] **Step 2: 실패 확인**

Run: `Push-Location C:\Users\ASUS\Desktop\stock-backtest; .\.venv\Scripts\python.exe -m pytest tests/test_kiwoom_token.py -v; Pop-Location`
Expected: FAIL — `ModuleNotFoundError: No module named 'broker.kiwoom'`

- [ ] **Step 3: 구현**

```python
# broker/kiwoom.py
from dataclasses import dataclass, field
import time


@dataclass
class KiwoomEndpoints:
    """엔드포인트 경로. 기본값은 추정 — 키움 공식 API 문서로 확정 후 조정."""
    token: str = "/oauth2/token"
    quote: str = "/api/dostk/stkinfo"
    balance: str = "/api/dostk/acnt/balance"
    holdings: str = "/api/dostk/acnt/holdings"
    order: str = "/api/dostk/ordr"
    order_status: str = "/api/dostk/ordr/status"


class KiwoomClient:
    def __init__(self, base_url, app_key, app_secret, account_no,
                 endpoints=None, http=None, clock=time.time):
        self.base_url = base_url.rstrip("/")
        self.app_key = app_key
        self.app_secret = app_secret
        self.account_no = account_no
        self.endpoints = endpoints or KiwoomEndpoints()
        self.http = http if http is not None else _default_http()
        self._clock = clock
        self._token = None
        self._token_expires_at = 0.0

    def get_token(self) -> str:
        if self._token and self._clock() < self._token_expires_at - 60:
            return self._token
        url = self.base_url + self.endpoints.token
        resp = self.http.post(url, json={
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "secretkey": self.app_secret,
        }, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        self._token = data["token"]
        ttl = float(data.get("expires_in", 3600))
        self._token_expires_at = self._clock() + ttl
        return self._token

    def _auth_headers(self):
        return {"Authorization": f"Bearer {self.get_token()}"}


def _default_http():
    import requests
    return requests.Session()
```

- [ ] **Step 4: 통과 확인**

Run: `Push-Location C:\Users\ASUS\Desktop\stock-backtest; .\.venv\Scripts\python.exe -m pytest tests/test_kiwoom_token.py -v; Pop-Location`
Expected: PASS (2)

- [ ] **Step 5: Commit**

```bash
git -C C:\Users\ASUS\Desktop\stock-backtest add broker/kiwoom.py tests/test_kiwoom_token.py
git -C C:\Users\ASUS\Desktop\stock-backtest commit -m "feat: KiwoomClient 토큰 발급/캐싱/만료 갱신"
```

---

### Task 4: broker/kiwoom.py — 시세·잔고·보유·주문 메서드

**Files:**
- Modify: `broker/kiwoom.py`
- Test: `tests/test_kiwoom_methods.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_kiwoom_methods.py
from broker.kiwoom import KiwoomClient


class FakeResp:
    def __init__(self, j, s=200):
        self._j = j; self.status_code = s
    def raise_for_status(self):
        if self.status_code >= 400: raise Exception(self.status_code)
    def json(self): return self._j


class FakeHttp:
    def __init__(self): self.calls = []; self.responses = []
    def post(self, url, json=None, headers=None, timeout=None):
        self.calls.append(("POST", url, json, headers))
        return self.responses.pop(0)
    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append(("GET", url, params, headers))
        return self.responses.pop(0)


def _client(http):
    return KiwoomClient("https://mock.kiwoom.com", "K", "S", "1234",
                        http=http, clock=lambda: 0.0)


def _token_resp():
    return FakeResp({"token": "T", "expires_in": 3600})


def test_get_quote_returns_price():
    http = FakeHttp()
    http.responses = [_token_resp(), FakeResp({"price": 12345.0})]
    assert _client(http).get_quote("360750") == 12345.0
    # GET호출 시 Authorization 헤더 부착
    last = http.calls[-1]
    assert last[0] == "GET"
    assert last[3]["Authorization"] == "Bearer T"


def test_get_balance_returns_cash_and_equity():
    http = FakeHttp()
    http.responses = [_token_resp(),
                      FakeResp({"cash": 5_000_000.0, "equity": 10_000_000.0})]
    b = _client(http).get_balance()
    assert b == {"cash": 5_000_000.0, "equity": 10_000_000.0}


def test_get_holdings_returns_code_map():
    http = FakeHttp()
    http.responses = [_token_resp(), FakeResp({"holdings": [
        {"code": "360750", "shares": 10, "avg_price": 15000.0},
        {"code": "381170", "shares": 5, "avg_price": 22000.0},
    ]})]
    h = _client(http).get_holdings()
    assert h == {
        "360750": {"shares": 10, "avg_price": 15000.0},
        "381170": {"shares": 5, "avg_price": 22000.0},
    }


def test_place_order_returns_order_id_and_sends_payload():
    http = FakeHttp()
    http.responses = [_token_resp(), FakeResp({"order_id": "ORD-1"})]
    oid = _client(http).place_order("360750", "BUY", 3)
    assert oid == "ORD-1"
    last = http.calls[-1]
    assert last[0] == "POST"
    payload = last[2]
    assert payload["code"] == "360750"
    assert payload["side"] == "BUY"
    assert payload["qty"] == 3
    assert payload["order_type"] == "MARKET"
    assert payload["account_no"] == "1234"


def test_get_order_status_parses_fields():
    http = FakeHttp()
    http.responses = [_token_resp(),
                      FakeResp({"status": "FILLED",
                                "filled_qty": 3, "fill_price": 15100.0})]
    s = _client(http).get_order_status("ORD-1")
    assert s == {"order_id": "ORD-1", "status": "FILLED",
                 "filled_qty": 3, "fill_price": 15100.0}
```

- [ ] **Step 2: 실패 확인**

Run: `Push-Location C:\Users\ASUS\Desktop\stock-backtest; .\.venv\Scripts\python.exe -m pytest tests/test_kiwoom_methods.py -v; Pop-Location`
Expected: FAIL — `AttributeError: 'KiwoomClient' object has no attribute 'get_quote'`

- [ ] **Step 3: 구현 (broker/kiwoom.py 끝에 메서드 추가)**

```python
    def get_quote(self, code) -> float:
        url = self.base_url + self.endpoints.quote
        resp = self.http.get(url, params={"code": code},
                             headers=self._auth_headers(), timeout=10)
        resp.raise_for_status()
        return float(resp.json()["price"])

    def get_balance(self) -> dict:
        url = self.base_url + self.endpoints.balance
        resp = self.http.get(url, params={"account_no": self.account_no},
                             headers=self._auth_headers(), timeout=10)
        resp.raise_for_status()
        d = resp.json()
        return {"cash": float(d["cash"]), "equity": float(d["equity"])}

    def get_holdings(self) -> dict:
        url = self.base_url + self.endpoints.holdings
        resp = self.http.get(url, params={"account_no": self.account_no},
                             headers=self._auth_headers(), timeout=10)
        resp.raise_for_status()
        items = resp.json().get("holdings", [])
        return {item["code"]: {"shares": int(item["shares"]),
                                "avg_price": float(item["avg_price"])}
                for item in items}

    def place_order(self, code, side, qty) -> str:
        url = self.base_url + self.endpoints.order
        payload = {
            "account_no": self.account_no, "code": code,
            "side": side, "qty": int(qty), "order_type": "MARKET",
        }
        resp = self.http.post(url, json=payload,
                              headers=self._auth_headers(), timeout=10)
        resp.raise_for_status()
        return str(resp.json()["order_id"])

    def get_order_status(self, order_id) -> dict:
        url = self.base_url + self.endpoints.order_status
        resp = self.http.get(url, params={"order_id": order_id},
                             headers=self._auth_headers(), timeout=10)
        resp.raise_for_status()
        d = resp.json()
        return {"order_id": order_id, "status": d["status"],
                "filled_qty": int(d.get("filled_qty", 0)),
                "fill_price": float(d.get("fill_price", 0.0))}
```

- [ ] **Step 4: 통과 확인**

Run: `Push-Location C:\Users\ASUS\Desktop\stock-backtest; .\.venv\Scripts\python.exe -m pytest tests/test_kiwoom_methods.py -v; Pop-Location`
Expected: PASS (5)

- [ ] **Step 5: Commit**

```bash
git -C C:\Users\ASUS\Desktop\stock-backtest add broker/kiwoom.py tests/test_kiwoom_methods.py
git -C C:\Users\ASUS\Desktop\stock-backtest commit -m "feat: KiwoomClient 시세·잔고·보유·주문·주문상태"
```

---

### Task 5: live/state.py — Holding/TraderState/TraderParams + 원자적 영속화

**Files:**
- Create: `live/state.py`
- Test: `tests/test_state.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_state.py
from live.state import Holding, TraderState, TraderParams


def test_state_default_paper_no_holdings():
    s = TraderState()
    assert s.mode == "paper"
    assert s.holdings == {}
    assert s.halted is False


def test_state_roundtrip_json(tmp_path):
    s = TraderState(mode="paper", cash=1_000_000.0,
                    holdings={"360750": Holding(shares=10,
                                                entry_price=15000.0,
                                                bought_at="2026-05-20")},
                    last_rebalance_date="2026-05-01",
                    last_action_date="2026-05-20",
                    halted=False, equity_start_of_day=11_000_000.0)
    p = tmp_path / "state.json"
    s.save(p)
    s2 = TraderState.load(p)
    assert s2.cash == 1_000_000.0
    assert s2.holdings["360750"].shares == 10
    assert s2.holdings["360750"].entry_price == 15000.0
    assert s2.last_rebalance_date == "2026-05-01"


def test_state_load_missing_file_returns_default(tmp_path):
    s = TraderState.load(tmp_path / "nope.json")
    assert s.mode == "paper" and s.holdings == {}


def test_state_save_is_atomic(tmp_path):
    """save() writes via temp+rename — no partial file on a target dir."""
    p = tmp_path / "deep" / "state.json"
    TraderState().save(p)
    assert p.exists()
    # no stray .tmp left behind
    assert not list((tmp_path / "deep").glob("*.tmp"))


def test_params_defaults_match_backtest():
    p = TraderParams()
    assert p.top_k == 3
    assert p.take_profit_pct == 0.05
    assert p.use_absolute_momentum is True
    assert p.target_time_hhmm == "15:15"
    assert 0 < p.max_position_pct < 1
    assert p.min_order_amount > 0


def test_params_roundtrip_json(tmp_path):
    p = TraderParams(top_k=2, take_profit_pct=0.10)
    f = tmp_path / "params.json"
    p.save(f)
    p2 = TraderParams.load(f)
    assert p2.top_k == 2
    assert p2.take_profit_pct == 0.10
```

- [ ] **Step 2: 실패 확인**

Run: `Push-Location C:\Users\ASUS\Desktop\stock-backtest; .\.venv\Scripts\python.exe -m pytest tests/test_state.py -v; Pop-Location`
Expected: FAIL — `ModuleNotFoundError: No module named 'live.state'`

- [ ] **Step 3: 구현**

```python
# live/state.py
from dataclasses import dataclass, field, asdict
from pathlib import Path
import json
import os


@dataclass
class Holding:
    shares: int
    entry_price: float
    bought_at: str = ""


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


@dataclass
class TraderState:
    mode: str = "paper"
    cash: float = 0.0
    holdings: dict = field(default_factory=dict)  # code -> Holding
    last_rebalance_date: str = ""
    last_action_date: str = ""
    halted: bool = False
    equity_start_of_day: float = 0.0

    def to_json(self) -> str:
        d = {**asdict(self),
             "holdings": {c: asdict(h) for c, h in self.holdings.items()}}
        return json.dumps(d, indent=2, ensure_ascii=False)

    @classmethod
    def from_json(cls, text: str) -> "TraderState":
        d = json.loads(text)
        h = {c: Holding(**v) for c, v in d.pop("holdings", {}).items()}
        s = cls(**d)
        s.holdings = h
        return s

    @classmethod
    def load(cls, path) -> "TraderState":
        p = Path(path)
        if not p.exists():
            return cls()
        return cls.from_json(p.read_text(encoding="utf-8"))

    def save(self, path) -> None:
        _atomic_write(Path(path), self.to_json())


@dataclass
class TraderParams:
    top_k: int = 3
    momentum_lookback_months: int = 12
    momentum_skip_months: int = 1
    use_take_profit: bool = True
    take_profit_pct: float = 0.05
    use_absolute_momentum: bool = True
    absolute_momentum_threshold: float = 0.0
    target_time_hhmm: str = "15:15"
    max_position_pct: float = 0.40
    min_order_amount: float = 10_000.0
    max_daily_loss: float = 0.05
    drift_tolerance: float = 0.05

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path) -> "TraderParams":
        p = Path(path)
        if not p.exists():
            return cls()
        return cls(**json.loads(p.read_text(encoding="utf-8")))

    def save(self, path) -> None:
        _atomic_write(Path(path), self.to_json())
```

- [ ] **Step 4: 통과 확인**

Run: `Push-Location C:\Users\ASUS\Desktop\stock-backtest; .\.venv\Scripts\python.exe -m pytest tests/test_state.py -v; Pop-Location`
Expected: PASS (6)

- [ ] **Step 5: Commit**

```bash
git -C C:\Users\ASUS\Desktop\stock-backtest add live/state.py tests/test_state.py
git -C C:\Users\ASUS\Desktop\stock-backtest commit -m "feat: Holding/TraderState/TraderParams 원자적 JSON 영속화"
```

---

### Task 6: live/universe_store.py — 사용자 편집 ETF 목록 영속화

**Files:**
- Create: `live/universe_store.py`
- Test: `tests/test_universe_store.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_universe_store.py
from live.universe_store import UniverseEntry, UniverseStore


def test_default_universe_empty():
    s = UniverseStore(entries=[])
    assert s.entries == []


def test_add_remove(tmp_path):
    s = UniverseStore(entries=[])
    s.add(UniverseEntry(name="TIGER 미국S&P500", code="360750"))
    s.add(UniverseEntry(name="TIGER 미국테크TOP10 INDXX", code="381170"))
    assert len(s.entries) == 2
    s.remove("360750")
    assert len(s.entries) == 1 and s.entries[0].code == "381170"


def test_add_dup_code_replaces(tmp_path):
    s = UniverseStore(entries=[UniverseEntry("OLD", "360750")])
    s.add(UniverseEntry(name="NEW", code="360750"))
    assert len(s.entries) == 1
    assert s.entries[0].name == "NEW"


def test_roundtrip(tmp_path):
    s = UniverseStore(entries=[UniverseEntry("A", "111"),
                                UniverseEntry("B", "222")])
    p = tmp_path / "u.json"
    s.save(p)
    s2 = UniverseStore.load(p)
    assert [(e.name, e.code) for e in s2.entries] == [("A", "111"),
                                                       ("B", "222")]


def test_load_missing_returns_empty(tmp_path):
    s = UniverseStore.load(tmp_path / "no.json")
    assert s.entries == []


def test_codes_helper():
    s = UniverseStore(entries=[UniverseEntry("A", "111"),
                                UniverseEntry("B", "222")])
    assert s.codes() == ["111", "222"]
```

- [ ] **Step 2: 실패 확인**

Run: `Push-Location C:\Users\ASUS\Desktop\stock-backtest; .\.venv\Scripts\python.exe -m pytest tests/test_universe_store.py -v; Pop-Location`
Expected: FAIL — `ModuleNotFoundError: No module named 'live.universe_store'`

- [ ] **Step 3: 구현**

```python
# live/universe_store.py
from dataclasses import dataclass, asdict
from pathlib import Path
import json

from live.state import _atomic_write


@dataclass
class UniverseEntry:
    name: str
    code: str


class UniverseStore:
    def __init__(self, entries=None):
        self.entries = list(entries or [])

    def add(self, entry: UniverseEntry) -> None:
        # 동일 code면 교체
        self.entries = [e for e in self.entries if e.code != entry.code]
        self.entries.append(entry)

    def remove(self, code: str) -> None:
        self.entries = [e for e in self.entries if e.code != code]

    def codes(self) -> list:
        return [e.code for e in self.entries]

    def names(self) -> list:
        return [e.name for e in self.entries]

    def save(self, path) -> None:
        text = json.dumps([asdict(e) for e in self.entries],
                          indent=2, ensure_ascii=False)
        _atomic_write(Path(path), text)

    @classmethod
    def load(cls, path) -> "UniverseStore":
        p = Path(path)
        if not p.exists():
            return cls()
        data = json.loads(p.read_text(encoding="utf-8"))
        return cls(entries=[UniverseEntry(**d) for d in data])
```

- [ ] **Step 4: 통과 확인**

Run: `Push-Location C:\Users\ASUS\Desktop\stock-backtest; .\.venv\Scripts\python.exe -m pytest tests/test_universe_store.py -v; Pop-Location`
Expected: PASS (6)

- [ ] **Step 5: Commit**

```bash
git -C C:\Users\ASUS\Desktop\stock-backtest add live/universe_store.py tests/test_universe_store.py
git -C C:\Users\ASUS\Desktop\stock-backtest commit -m "feat: UniverseStore (사용자 편집 ETF 목록 영속화)"
```

---

### Task 7: live/safety.py — 안전장치 (순수 함수)

**Files:**
- Create: `live/safety.py`
- Test: `tests/test_safety.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_safety.py
from datetime import datetime
import pytest
from live.safety import (is_market_open, within_position_limit,
                          daily_loss_kill, order_size_ok,
                          holdings_drift_ok, validate_paper_mode)
from live.state import Holding
from live.errors import SafetyError


def test_market_open_weekday_inside():
    # 2026-05-20은 수요일
    assert is_market_open(datetime(2026, 5, 20, 10, 0)) is True


def test_market_closed_weekend():
    assert is_market_open(datetime(2026, 5, 23, 10, 0)) is False


def test_market_closed_outside_hours():
    assert is_market_open(datetime(2026, 5, 20, 8, 0)) is False
    assert is_market_open(datetime(2026, 5, 20, 16, 0)) is False


def test_within_position_limit_under():
    assert within_position_limit(3_000_000, 10_000_000, 0.40) is True


def test_within_position_limit_over():
    assert within_position_limit(5_000_000, 10_000_000, 0.40) is False


def test_within_position_limit_zero_equity():
    assert within_position_limit(1.0, 0.0, 0.40) is False


def test_daily_loss_kill_triggers():
    # -5% 초과 손실
    assert daily_loss_kill(equity_now=9_400_000,
                           equity_start=10_000_000,
                           max_loss_pct=0.05) is True


def test_daily_loss_kill_does_not_trigger():
    assert daily_loss_kill(9_700_000, 10_000_000, 0.05) is False


def test_order_size_ok():
    assert order_size_ok(20_000, min_amount=10_000) is True
    assert order_size_ok(5_000, min_amount=10_000) is False


def test_holdings_drift_ok_within_tolerance():
    state = {"360750": Holding(shares=100, entry_price=15000.0)}
    broker = {"360750": {"shares": 102, "avg_price": 15000.0}}
    assert holdings_drift_ok(state, broker, 0.05) is True


def test_holdings_drift_detects_difference():
    state = {"360750": Holding(shares=100, entry_price=15000.0)}
    broker = {"360750": {"shares": 50, "avg_price": 15000.0}}
    assert holdings_drift_ok(state, broker, 0.05) is False


def test_holdings_drift_detects_missing_position():
    state = {"360750": Holding(shares=100, entry_price=15000.0)}
    broker = {}  # 브로커에 없음
    assert holdings_drift_ok(state, broker, 0.05) is False


def test_validate_paper_mode_passes():
    validate_paper_mode("paper")  # 예외 없음


def test_validate_paper_mode_rejects_live():
    with pytest.raises(SafetyError):
        validate_paper_mode("live")
```

- [ ] **Step 2: 실패 확인**

Run: `Push-Location C:\Users\ASUS\Desktop\stock-backtest; .\.venv\Scripts\python.exe -m pytest tests/test_safety.py -v; Pop-Location`
Expected: FAIL — `ModuleNotFoundError: No module named 'live.safety'`

- [ ] **Step 3: 구현**

```python
# live/safety.py
from datetime import datetime, time

from live.errors import SafetyError

KRX_OPEN = time(9, 0)
KRX_CLOSE = time(15, 30)


def is_market_open(now: datetime) -> bool:
    if now.weekday() >= 5:  # 토(5), 일(6)
        return False
    t = now.time()
    return KRX_OPEN <= t <= KRX_CLOSE


def within_position_limit(notional: float, equity: float,
                          max_pct: float) -> bool:
    if equity <= 0:
        return False
    return notional / equity <= max_pct


def daily_loss_kill(equity_now: float, equity_start: float,
                    max_loss_pct: float) -> bool:
    if equity_start <= 0:
        return False
    loss = (equity_start - equity_now) / equity_start
    return loss >= max_loss_pct


def order_size_ok(notional: float, min_amount: float) -> bool:
    return notional >= min_amount


def holdings_drift_ok(state_holdings: dict, broker_holdings: dict,
                      tolerance: float) -> bool:
    codes = set(state_holdings.keys()) | set(broker_holdings.keys())
    for code in codes:
        s_shares = (state_holdings[code].shares
                    if code in state_holdings else 0)
        b_shares = int(broker_holdings.get(code, {}).get("shares", 0))
        if s_shares == 0 and b_shares == 0:
            continue
        max_shares = max(s_shares, b_shares)
        if max_shares == 0:
            continue
        if abs(s_shares - b_shares) / max_shares > tolerance:
            return False
    return True


def validate_paper_mode(mode: str) -> None:
    if mode != "paper":
        raise SafetyError(f"paper 모드만 허용; got mode={mode!r}")
```

- [ ] **Step 4: 통과 확인**

Run: `Push-Location C:\Users\ASUS\Desktop\stock-backtest; .\.venv\Scripts\python.exe -m pytest tests/test_safety.py -v; Pop-Location`
Expected: PASS (14)

- [ ] **Step 5: Commit**

```bash
git -C C:\Users\ASUS\Desktop\stock-backtest add live/safety.py tests/test_safety.py
git -C C:\Users\ASUS\Desktop\stock-backtest commit -m "feat: safety 검사 함수 (시간·한도·킬스위치·드리프트·모드)"
```

---

### Task 8: live/runner.py — Decision 엔진

**Files:**
- Create: `live/runner.py`
- Test: `tests/test_runner.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_runner.py
from datetime import date
import numpy as np
import pandas as pd

from live.runner import Order, Decision, decide
from live.state import Holding, TraderState, TraderParams


def _panel():
    idx = pd.date_range("2024-01-01", "2026-05-20", freq="B")
    n = len(idx)
    return pd.DataFrame({
        "A": 100.0 * (1.005) ** np.arange(n),
        "B": 100.0 * (1.001) ** np.arange(n),
        "C": 100.0 * (0.999) ** np.arange(n),
    }, index=idx)


def test_rebalance_when_new_month():
    panel = _panel()
    state = TraderState(mode="paper", cash=10_000_000.0, holdings={},
                        last_rebalance_date="")
    params = TraderParams(top_k=1, use_take_profit=False,
                          use_absolute_momentum=False)
    d = decide(panel, date(2026, 5, 20), {}, 10_000_000.0, params, state)
    assert d.action == "REBALANCE"
    # 상승률이 가장 큰 A가 선택되어야 함
    buy_codes = [o.code for o in d.orders if o.side == "BUY"]
    assert buy_codes == ["A"]


def test_noop_when_same_month_and_no_tp():
    panel = _panel()
    state = TraderState(mode="paper", cash=10_000_000.0,
                        last_rebalance_date="2026-05-01")
    params = TraderParams(top_k=1, use_take_profit=False)
    d = decide(panel, date(2026, 5, 20), {}, 10_000_000.0, params, state)
    assert d.action == "NOOP"
    assert d.orders == []


def test_take_profit_triggers_sell():
    panel = _panel()
    # 보유: A를 매우 낮은 진입가로 → 현재가 대비 5% 초과
    holdings = {"A": Holding(shares=10, entry_price=1.0,
                              bought_at="2024-01-01")}
    state = TraderState(mode="paper", holdings=holdings,
                        last_rebalance_date="2026-05-01")
    params = TraderParams(top_k=1, use_take_profit=True,
                          take_profit_pct=0.05)
    d = decide(panel, date(2026, 5, 20), holdings, 0.0, params, state)
    assert d.action == "TAKE_PROFIT"
    assert any(o.code == "A" and o.side == "SELL" for o in d.orders)


def test_rebalance_includes_sell_of_existing_holdings():
    panel = _panel()
    holdings = {"C": Holding(shares=10, entry_price=100.0)}
    state = TraderState(mode="paper", holdings=holdings,
                        last_rebalance_date="2026-04-01")
    params = TraderParams(top_k=1, use_take_profit=False,
                          use_absolute_momentum=False)
    d = decide(panel, date(2026, 5, 20), holdings,
               5_000_000.0, params, state)
    assert d.action == "REBALANCE"
    sides = {o.side for o in d.orders}
    assert "SELL" in sides and "BUY" in sides
```

- [ ] **Step 2: 실패 확인**

Run: `Push-Location C:\Users\ASUS\Desktop\stock-backtest; .\.venv\Scripts\python.exe -m pytest tests/test_runner.py -v; Pop-Location`
Expected: FAIL — `ModuleNotFoundError: No module named 'live.runner'`

- [ ] **Step 3: 구현**

```python
# live/runner.py
from dataclasses import dataclass, field
import pandas as pd

from strategy.momentum import compute_scores, select_top_k, target_weights


@dataclass
class Order:
    code: str
    side: str   # "BUY" | "SELL"
    qty: int
    reason: str


@dataclass
class Decision:
    action: str  # "REBALANCE" | "TAKE_PROFIT" | "NOOP"
    orders: list = field(default_factory=list)
    reason: str = ""


def _is_first_action_of_month(today, last_rebalance_str: str) -> bool:
    if not last_rebalance_str:
        return True
    last = pd.Timestamp(last_rebalance_str).date()
    return (today.year, today.month) != (last.year, last.month)


def decide(close_panel: pd.DataFrame, today,
           holdings_state: dict, cash: float,
           params, state) -> Decision:
    latest = close_panel.iloc[-1]

    # 1) 월이 바뀌었으면 리밸런싱 (익절보다 우선)
    if _is_first_action_of_month(today, state.last_rebalance_date):
        scores = compute_scores(close_panel, pd.Timestamp(today),
                                params.momentum_lookback_months,
                                params.momentum_skip_months)
        selected = select_top_k(scores, params.top_k)
        weights = target_weights(selected, scores, params.top_k,
                                 params.use_absolute_momentum,
                                 params.absolute_momentum_threshold)
        equity = cash + sum(
            h.shares * float(latest.get(c, 0) or 0)
            for c, h in holdings_state.items()
        )
        orders = []
        for code, h in holdings_state.items():
            orders.append(Order(code=code, side="SELL", qty=h.shares,
                                reason="rebalance"))
        for code, w in weights.items():
            px = float(latest.get(code, 0) or 0)
            if px > 0:
                qty = int((equity * w) // px)
                if qty > 0:
                    orders.append(Order(code=code, side="BUY", qty=qty,
                                        reason="rebalance"))
        return Decision(action="REBALANCE", orders=orders,
                        reason=f"monthly rebalance: target={list(weights)}")

    # 2) 같은 달이면 익절만 검사
    if params.use_take_profit:
        tp_orders = []
        for code, h in holdings_state.items():
            px = float(latest.get(code, 0) or 0)
            if px > 0 and px / h.entry_price - 1.0 >= params.take_profit_pct:
                tp_orders.append(Order(code=code, side="SELL",
                                       qty=h.shares, reason="take_profit"))
        if tp_orders:
            return Decision(action="TAKE_PROFIT", orders=tp_orders,
                            reason=f"+{params.take_profit_pct:.0%} reached")

    return Decision(action="NOOP", orders=[], reason="no signal today")
```

- [ ] **Step 4: 통과 확인**

Run: `Push-Location C:\Users\ASUS\Desktop\stock-backtest; .\.venv\Scripts\python.exe -m pytest tests/test_runner.py -v; Pop-Location`
Expected: PASS (4)

- [ ] **Step 5: Commit**

```bash
git -C C:\Users\ASUS\Desktop\stock-backtest add live/runner.py tests/test_runner.py
git -C C:\Users\ASUS\Desktop\stock-backtest commit -m "feat: Runner Decision 엔진 (REBALANCE/TAKE_PROFIT/NOOP)"
```

---

### Task 9: live/executor.py — Decision 실행 + fail-safe

**Files:**
- Create: `live/executor.py`
- Test: `tests/test_executor.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_executor.py
import logging
from live.executor import execute
from live.runner import Decision, Order
from live.state import Holding, TraderState, TraderParams


class FakeBroker:
    def __init__(self, quote=10000.0, balance=None, fill="FILLED"):
        self.quote = quote
        self._balance = balance or {"cash": 5_000_000.0,
                                     "equity": 10_000_000.0}
        self.placed = []
        self._next_id = 0
        self._fill = fill

    def get_quote(self, code): return self.quote
    def get_balance(self): return dict(self._balance)
    def get_holdings(self): return {}

    def place_order(self, code, side, qty):
        self._next_id += 1
        oid = f"ORD-{self._next_id}"
        self.placed.append((oid, code, side, qty))
        return oid

    def get_order_status(self, order_id):
        # 마지막 주문 정보로부터 체결가 모사
        _, code, side, qty = next(p for p in self.placed if p[0] == order_id)
        return {"order_id": order_id, "status": self._fill,
                "filled_qty": qty, "fill_price": self.quote}


def _logger():
    return logging.getLogger("test")


def _safety():
    return {"max_position_pct": 0.40, "min_order_amount": 10_000.0,
            "max_daily_loss": 0.05}


def test_noop_returns_true_without_orders():
    broker = FakeBroker()
    state = TraderState(equity_start_of_day=10_000_000.0)
    ok = execute(Decision(action="NOOP", orders=[], reason=""),
                  broker, state, _safety(), _logger())
    assert ok is True
    assert broker.placed == []


def test_rebalance_sells_then_buys_and_updates_state():
    broker = FakeBroker(quote=10_000.0)
    state = TraderState(mode="paper", cash=0.0,
                        holdings={"OLD": Holding(shares=5,
                                                 entry_price=20_000.0)},
                        equity_start_of_day=10_000_000.0)
    d = Decision(action="REBALANCE", orders=[
        Order(code="OLD", side="SELL", qty=5, reason="rebalance"),
        Order(code="NEW", side="BUY", qty=100, reason="rebalance"),
    ])
    ok = execute(d, broker, state, _safety(), _logger())
    assert ok is True
    # SELL이 BUY보다 먼저 호출됨
    sides = [p[2] for p in broker.placed]
    assert sides == ["SELL", "BUY"]
    # 상태 업데이트
    assert "OLD" not in state.holdings
    assert state.holdings["NEW"].shares == 100
    assert state.holdings["NEW"].entry_price == 10_000.0


def test_position_limit_blocks_buy_but_keeps_state_safe():
    # 단가 너무 비싸서 한도 초과 → 매수 스킵
    broker = FakeBroker(quote=1_000_000.0)  # 100주 = 1억
    state = TraderState(mode="paper", cash=10_000_000.0,
                        equity_start_of_day=10_000_000.0)
    d = Decision(action="REBALANCE", orders=[
        Order(code="X", side="BUY", qty=100, reason="rebalance"),
    ])
    ok = execute(d, broker, state, _safety(), _logger())
    assert ok is True
    # 주문 안 됨
    assert broker.placed == []
    assert "X" not in state.holdings


def test_rejected_order_halts_state():
    broker = FakeBroker(quote=10_000.0, fill="REJECTED")
    state = TraderState(mode="paper", cash=10_000_000.0,
                        equity_start_of_day=10_000_000.0)
    d = Decision(action="REBALANCE", orders=[
        Order(code="X", side="BUY", qty=100, reason="rebalance"),
    ])
    ok = execute(d, broker, state, _safety(), _logger())
    assert ok is False
    assert state.halted is True


def test_daily_loss_kill_halts():
    broker = FakeBroker(balance={"cash": 0.0, "equity": 9_000_000.0})
    state = TraderState(mode="paper", equity_start_of_day=10_000_000.0)
    d = Decision(action="REBALANCE", orders=[
        Order(code="X", side="BUY", qty=100, reason="rebalance"),
    ])
    ok = execute(d, broker, state, _safety(), _logger())
    assert ok is False
    assert state.halted is True
    assert broker.placed == []


def test_live_mode_rejected():
    broker = FakeBroker()
    state = TraderState(mode="live", equity_start_of_day=10_000_000.0)
    d = Decision(action="REBALANCE", orders=[
        Order(code="X", side="BUY", qty=1, reason="rebalance")])
    ok = execute(d, broker, state, _safety(), _logger())
    assert ok is False
    assert state.halted is True
```

- [ ] **Step 2: 실패 확인**

Run: `Push-Location C:\Users\ASUS\Desktop\stock-backtest; .\.venv\Scripts\python.exe -m pytest tests/test_executor.py -v; Pop-Location`
Expected: FAIL — `ModuleNotFoundError: No module named 'live.executor'`

- [ ] **Step 3: 구현**

```python
# live/executor.py
from datetime import datetime

from live.errors import SafetyError
from live.safety import (within_position_limit, daily_loss_kill,
                          order_size_ok, validate_paper_mode)
from live.state import Holding


def execute(decision, broker, state, safety_params, log, now=None) -> bool:
    """
    Decision을 실제 주문으로 실행한다.
    안전검사 실패·주문거부·예외 시 state.halted=True로 설정하고 False 반환.
    """
    if decision.action == "NOOP":
        return True

    now = now or datetime.now()

    # 1) 모드 검사
    try:
        validate_paper_mode(state.mode)
    except SafetyError as e:
        log.error(f"mode violation: {e}")
        state.halted = True
        return False

    # 2) 일일 손실 킬스위치
    try:
        equity_now = broker.get_balance().get("equity", 0.0)
    except Exception as e:
        log.error(f"balance fetch failed: {e}")
        state.halted = True
        return False
    if daily_loss_kill(equity_now, state.equity_start_of_day,
                       safety_params["max_daily_loss"]):
        log.warning("daily loss kill-switch triggered")
        state.halted = True
        return False

    # 3) 매도 먼저
    for order in decision.orders:
        if order.side != "SELL":
            continue
        try:
            oid = broker.place_order(order.code, "SELL", order.qty)
            status = broker.get_order_status(oid)
        except Exception as e:
            log.error(f"SELL {order.code} 실패: {e}")
            state.halted = True
            return False
        if str(status.get("status", "")).upper() != "FILLED":
            log.error(f"SELL {order.code} 미체결: {status}")
            state.halted = True
            return False
        state.cash += status["filled_qty"] * status["fill_price"]
        state.holdings.pop(order.code, None)
        log.info(f"SELL {order.code} x{status['filled_qty']} @ "
                 f"{status['fill_price']} ({order.reason})")

    # 4) 매수
    for order in decision.orders:
        if order.side != "BUY":
            continue
        try:
            quote = broker.get_quote(order.code)
        except Exception as e:
            log.error(f"quote {order.code} 실패: {e}")
            state.halted = True
            return False
        notional = order.qty * quote
        equity_now = broker.get_balance().get("equity", 0.0)
        if not within_position_limit(notional, equity_now,
                                     safety_params["max_position_pct"]):
            log.warning(
                f"BUY {order.code} 한도초과 (notional={notional:.0f} "
                f"> {safety_params['max_position_pct']:.0%} of equity); 건너뜀")
            continue
        if not order_size_ok(notional, safety_params["min_order_amount"]):
            log.info(f"BUY {order.code} 최소금액 미달; 건너뜀")
            continue
        try:
            oid = broker.place_order(order.code, "BUY", order.qty)
            status = broker.get_order_status(oid)
        except Exception as e:
            log.error(f"BUY {order.code} 실패: {e}")
            state.halted = True
            return False
        if str(status.get("status", "")).upper() != "FILLED":
            log.error(f"BUY {order.code} 미체결: {status}")
            state.halted = True
            return False
        state.cash -= status["filled_qty"] * status["fill_price"]
        state.holdings[order.code] = Holding(
            shares=int(status["filled_qty"]),
            entry_price=float(status["fill_price"]),
            bought_at=now.date().isoformat(),
        )
        log.info(f"BUY {order.code} x{status['filled_qty']} @ "
                 f"{status['fill_price']} ({order.reason})")

    # 5) 액션 기록
    today_str = now.date().isoformat()
    state.last_action_date = today_str
    if decision.action == "REBALANCE":
        state.last_rebalance_date = today_str
    return True
```

- [ ] **Step 4: 통과 확인**

Run: `Push-Location C:\Users\ASUS\Desktop\stock-backtest; .\.venv\Scripts\python.exe -m pytest tests/test_executor.py -v; Pop-Location`
Expected: PASS (6)

- [ ] **Step 5: Commit**

```bash
git -C C:\Users\ASUS\Desktop\stock-backtest add live/executor.py tests/test_executor.py
git -C C:\Users\ASUS\Desktop\stock-backtest commit -m "feat: Executor (Decision 실행 + 안전검사 + fail-safe halt)"
```

---

### Task 10: live/scheduler.py — `should_trigger` + Scheduler

**Files:**
- Create: `live/scheduler.py`
- Test: `tests/test_scheduler.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_scheduler.py
from datetime import datetime, time
import threading

from live.scheduler import should_trigger, Scheduler


def test_should_not_trigger_before_target():
    now = datetime(2026, 5, 20, 14, 0)
    assert should_trigger(now, target_time=time(15, 15),
                          last_action_date="") is False


def test_should_trigger_after_target_unprocessed():
    now = datetime(2026, 5, 20, 15, 20)
    assert should_trigger(now, target_time=time(15, 15),
                          last_action_date="") is True


def test_should_not_trigger_if_already_processed_today():
    now = datetime(2026, 5, 20, 15, 20)
    assert should_trigger(now, target_time=time(15, 15),
                          last_action_date="2026-05-20") is False


def test_should_not_trigger_on_weekend():
    now = datetime(2026, 5, 23, 15, 20)  # 토요일
    assert should_trigger(now, target_time=time(15, 15),
                          last_action_date="") is False


def test_scheduler_calls_on_trigger():
    calls = []
    s = Scheduler(target_time=time(0, 0),  # 항상 지난 시각
                  on_trigger=lambda: calls.append(1),
                  tick_seconds=0.05,
                  clock=lambda: datetime(2026, 5, 20, 10, 0))
    state = type("S", (), {"halted": False, "last_action_date": ""})()
    s.start(state_provider=lambda: state)
    # 한두 tick 안에 호출됐는지 확인
    deadline = threading.Event()
    deadline.wait(0.3)
    s.stop()
    assert len(calls) >= 1


def test_scheduler_respects_halted():
    calls = []
    s = Scheduler(target_time=time(0, 0),
                  on_trigger=lambda: calls.append(1),
                  tick_seconds=0.05,
                  clock=lambda: datetime(2026, 5, 20, 10, 0))
    state = type("S", (), {"halted": True, "last_action_date": ""})()
    s.start(state_provider=lambda: state)
    threading.Event().wait(0.2)
    s.stop()
    assert calls == []
```

- [ ] **Step 2: 실패 확인**

Run: `Push-Location C:\Users\ASUS\Desktop\stock-backtest; .\.venv\Scripts\python.exe -m pytest tests/test_scheduler.py -v; Pop-Location`
Expected: FAIL — `ModuleNotFoundError: No module named 'live.scheduler'`

- [ ] **Step 3: 구현**

```python
# live/scheduler.py
from datetime import datetime, time as dtime
import threading


def should_trigger(now: datetime, target_time: dtime,
                   last_action_date: str) -> bool:
    if now.weekday() >= 5:  # 주말 제외
        return False
    if now.time() < target_time:
        return False
    if last_action_date == now.date().isoformat():
        return False
    return True


class Scheduler:
    def __init__(self, target_time, on_trigger, tick_seconds=30,
                 clock=datetime.now):
        self.target_time = target_time
        self.on_trigger = on_trigger
        self.tick_seconds = tick_seconds
        self.clock = clock
        self._stop = threading.Event()
        self._thread = None

    def start(self, state_provider) -> None:
        def _run():
            while not self._stop.is_set():
                now = self.clock()
                state = state_provider()
                if (not getattr(state, "halted", False)
                        and should_trigger(now, self.target_time,
                                           getattr(state, "last_action_date",
                                                   ""))):
                    try:
                        self.on_trigger()
                    except Exception:
                        pass  # GUI 로그어가 상위에서 잡음
                self._stop.wait(self.tick_seconds)
        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
```

- [ ] **Step 4: 통과 확인**

Run: `Push-Location C:\Users\ASUS\Desktop\stock-backtest; .\.venv\Scripts\python.exe -m pytest tests/test_scheduler.py -v; Pop-Location`
Expected: PASS (6)

- [ ] **Step 5: Commit**

```bash
git -C C:\Users\ASUS\Desktop\stock-backtest add live/scheduler.py tests/test_scheduler.py
git -C C:\Users\ASUS\Desktop\stock-backtest commit -m "feat: should_trigger 순수 판정 + 백그라운드 Scheduler 스레드"
```

---

### Task 11: gui/panels.py — 종목 편집·파라미터·로그 위젯

**Files:**
- Create: `gui/panels.py`
- Test: `tests/test_gui_panels.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_gui_panels.py
import pytest

try:
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    _HAS_TK = True
except Exception:
    _HAS_TK = False

from live.universe_store import UniverseEntry, UniverseStore
from live.state import TraderParams


pytestmark = pytest.mark.skipif(not _HAS_TK,
                                 reason="Tkinter 사용 불가 환경")


def test_universe_panel_lists_entries():
    from gui.panels import UniversePanel
    store = UniverseStore(entries=[UniverseEntry("TIGER 미국S&P500", "360750"),
                                    UniverseEntry("KODEX 인도Nifty50", "453810")])
    panel = UniversePanel(root, store)
    assert panel.row_count() == 2


def test_universe_panel_add_and_remove():
    from gui.panels import UniversePanel
    store = UniverseStore(entries=[])
    panel = UniversePanel(root, store)
    panel.add_entry(name="A", code="111")
    assert panel.row_count() == 1
    panel.remove_entry("111")
    assert panel.row_count() == 0


def test_params_panel_reads_and_writes():
    from gui.panels import ParamsPanel
    params = TraderParams()
    panel = ParamsPanel(root, params)
    panel.set_top_k(2)
    panel.set_take_profit_pct(0.10)
    out = panel.read()
    assert out.top_k == 2
    assert out.take_profit_pct == 0.10


def test_log_panel_appends_lines():
    from gui.panels import LogPanel
    panel = LogPanel(root)
    panel.append("hello")
    panel.append("world")
    assert "hello" in panel.text() and "world" in panel.text()
```

- [ ] **Step 2: 실패 확인**

Run: `Push-Location C:\Users\ASUS\Desktop\stock-backtest; .\.venv\Scripts\python.exe -m pytest tests/test_gui_panels.py -v; Pop-Location`
Expected: FAIL — `ModuleNotFoundError: No module named 'gui.panels'` (또는 Tkinter 미설치 시 SKIPPED)

- [ ] **Step 3: 구현**

```python
# gui/panels.py
import tkinter as tk
from tkinter import ttk

from live.state import TraderParams
from live.universe_store import UniverseEntry, UniverseStore


class UniversePanel(ttk.Frame):
    def __init__(self, master, store: UniverseStore):
        super().__init__(master)
        self.store = store
        self.tree = ttk.Treeview(self, columns=("name", "code"),
                                  show="headings", height=10)
        self.tree.heading("name", text="이름")
        self.tree.heading("code", text="종목코드")
        self.tree.column("code", width=80)
        self.tree.pack(fill="both", expand=True)

        form = ttk.Frame(self); form.pack(fill="x")
        self.name_var = tk.StringVar(); self.code_var = tk.StringVar()
        ttk.Label(form, text="이름").pack(side="left")
        ttk.Entry(form, textvariable=self.name_var, width=24).pack(side="left")
        ttk.Label(form, text="코드").pack(side="left")
        ttk.Entry(form, textvariable=self.code_var, width=10).pack(side="left")
        ttk.Button(form, text="추가",
                    command=self._on_add).pack(side="left")
        ttk.Button(form, text="선택삭제",
                    command=self._on_remove_selected).pack(side="left")
        self._refresh()

    def _refresh(self):
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        for e in self.store.entries:
            self.tree.insert("", "end", iid=e.code, values=(e.name, e.code))

    def _on_add(self):
        n = self.name_var.get().strip()
        c = self.code_var.get().strip()
        if n and c:
            self.add_entry(n, c)
            self.name_var.set(""); self.code_var.set("")

    def _on_remove_selected(self):
        sel = self.tree.selection()
        for iid in sel:
            self.remove_entry(iid)

    def add_entry(self, name: str, code: str) -> None:
        self.store.add(UniverseEntry(name=name, code=code))
        self._refresh()

    def remove_entry(self, code: str) -> None:
        self.store.remove(code)
        self._refresh()

    def row_count(self) -> int:
        return len(self.tree.get_children())


class ParamsPanel(ttk.Frame):
    def __init__(self, master, params: TraderParams):
        super().__init__(master)
        self._top_k = tk.IntVar(value=params.top_k)
        self._tp_pct = tk.DoubleVar(value=params.take_profit_pct)
        self._use_tp = tk.BooleanVar(value=params.use_take_profit)
        self._use_abs = tk.BooleanVar(value=params.use_absolute_momentum)
        self._target = tk.StringVar(value=params.target_time_hhmm)
        for label, var in (("Top K", self._top_k), ("익절률", self._tp_pct),
                            ("실행시각(HH:MM)", self._target)):
            row = ttk.Frame(self); row.pack(fill="x")
            ttk.Label(row, text=label, width=14).pack(side="left")
            ttk.Entry(row, textvariable=var).pack(side="left")
        ttk.Checkbutton(self, text="익절 사용",
                         variable=self._use_tp).pack(anchor="w")
        ttk.Checkbutton(self, text="절대 모멘텀 사용",
                         variable=self._use_abs).pack(anchor="w")
        self._template = params

    def set_top_k(self, k: int) -> None: self._top_k.set(k)
    def set_take_profit_pct(self, p: float) -> None: self._tp_pct.set(p)

    def read(self) -> TraderParams:
        out = TraderParams(**{**self._template.__dict__})
        out.top_k = int(self._top_k.get())
        out.take_profit_pct = float(self._tp_pct.get())
        out.use_take_profit = bool(self._use_tp.get())
        out.use_absolute_momentum = bool(self._use_abs.get())
        out.target_time_hhmm = str(self._target.get())
        return out


class LogPanel(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self._text = tk.Text(self, height=15, wrap="none")
        self._text.pack(fill="both", expand=True)

    def append(self, line: str) -> None:
        self._text.insert("end", line.rstrip() + "\n")
        self._text.see("end")

    def text(self) -> str:
        return self._text.get("1.0", "end")
```

- [ ] **Step 4: 통과 확인**

Run: `Push-Location C:\Users\ASUS\Desktop\stock-backtest; .\.venv\Scripts\python.exe -m pytest tests/test_gui_panels.py -v; Pop-Location`
Expected: PASS (4) — Tkinter 사용 불가 환경에서는 SKIPPED

- [ ] **Step 5: Commit**

```bash
git -C C:\Users\ASUS\Desktop\stock-backtest add gui/panels.py tests/test_gui_panels.py
git -C C:\Users\ASUS\Desktop\stock-backtest commit -m "feat: GUI 패널 (Universe·Params·Log)"
```

---

### Task 12: gui/app.py — 메인 창 + 모드 표시 + 시작/정지

**Files:**
- Create: `gui/app.py`
- Test: `tests/test_gui_app.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_gui_app.py
import pytest

try:
    import tkinter as tk
    _r = tk.Tk(); _r.withdraw()
    _HAS_TK = True
except Exception:
    _HAS_TK = False

pytestmark = pytest.mark.skipif(not _HAS_TK, reason="Tkinter 사용 불가")


def test_app_constructs_and_shows_paper_mode():
    from gui.app import TraderApp
    from live.universe_store import UniverseStore
    from live.state import TraderState, TraderParams
    app = TraderApp(state=TraderState(mode="paper"),
                     params=TraderParams(),
                     universe=UniverseStore(entries=[]),
                     on_start=lambda: None, on_stop=lambda: None)
    assert "PAPER" in app.mode_label_text()
    app.destroy()


def test_app_start_stop_invoke_callbacks():
    from gui.app import TraderApp
    from live.universe_store import UniverseStore
    from live.state import TraderState, TraderParams
    starts = []; stops = []
    app = TraderApp(state=TraderState(mode="paper"),
                     params=TraderParams(),
                     universe=UniverseStore(entries=[]),
                     on_start=lambda: starts.append(1),
                     on_stop=lambda: stops.append(1))
    app.click_start()
    app.click_stop()
    assert starts == [1] and stops == [1]
    app.destroy()


def test_app_logs_messages():
    from gui.app import TraderApp
    from live.universe_store import UniverseStore
    from live.state import TraderState, TraderParams
    app = TraderApp(state=TraderState(mode="paper"),
                     params=TraderParams(),
                     universe=UniverseStore(entries=[]),
                     on_start=lambda: None, on_stop=lambda: None)
    app.log("hello world")
    assert "hello world" in app.log_text()
    app.destroy()
```

- [ ] **Step 2: 실패 확인**

Run: `Push-Location C:\Users\ASUS\Desktop\stock-backtest; .\.venv\Scripts\python.exe -m pytest tests/test_gui_app.py -v; Pop-Location`
Expected: FAIL — `ModuleNotFoundError: No module named 'gui.app'`

- [ ] **Step 3: 구현**

```python
# gui/app.py
import tkinter as tk
from tkinter import ttk

from gui.panels import UniversePanel, ParamsPanel, LogPanel


class TraderApp(tk.Tk):
    def __init__(self, *, state, params, universe, on_start, on_stop):
        super().__init__()
        self.title("키움 모의투자 자동매매")
        self.geometry("960x600")
        self._state = state
        self._on_start = on_start
        self._on_stop = on_stop

        # 좌측: Universe + Params
        left = ttk.Frame(self); left.pack(side="left", fill="y", padx=8, pady=8)
        ttk.Label(left, text="ETF 종목").pack(anchor="w")
        self.universe_panel = UniversePanel(left, universe)
        self.universe_panel.pack(fill="x")
        ttk.Label(left, text="파라미터").pack(anchor="w", pady=(8, 0))
        self.params_panel = ParamsPanel(left, params)
        self.params_panel.pack(fill="x")

        # 우측 상: 모드 + 시작/정지
        right = ttk.Frame(self); right.pack(side="right", fill="both",
                                              expand=True, padx=8, pady=8)
        self._mode_var = tk.StringVar(value=self._mode_text())
        mode_lbl = ttk.Label(right, textvariable=self._mode_var,
                              font=("", 16, "bold"), foreground="green")
        mode_lbl.pack(anchor="w")

        btns = ttk.Frame(right); btns.pack(fill="x", pady=4)
        self._start_btn = ttk.Button(btns, text="시작",
                                       command=self.click_start)
        self._start_btn.pack(side="left", padx=4)
        self._stop_btn = ttk.Button(btns, text="정지",
                                      command=self.click_stop)
        self._stop_btn.pack(side="left", padx=4)

        # 우측 하: 로그
        ttk.Label(right, text="로그").pack(anchor="w", pady=(8, 0))
        self.log_panel = LogPanel(right)
        self.log_panel.pack(fill="both", expand=True)

    def _mode_text(self) -> str:
        if getattr(self._state, "halted", False):
            return "HALTED"
        return f"MODE: {self._state.mode.upper()}"

    def mode_label_text(self) -> str:
        return self._mode_var.get()

    def refresh_mode(self) -> None:
        self._mode_var.set(self._mode_text())

    def click_start(self) -> None:
        self._on_start()

    def click_stop(self) -> None:
        self._on_stop()

    def log(self, line: str) -> None:
        self.log_panel.append(line)

    def log_text(self) -> str:
        return self.log_panel.text()
```

- [ ] **Step 4: 통과 확인**

Run: `Push-Location C:\Users\ASUS\Desktop\stock-backtest; .\.venv\Scripts\python.exe -m pytest tests/test_gui_app.py -v; Pop-Location`
Expected: PASS (3)

- [ ] **Step 5: Commit**

```bash
git -C C:\Users\ASUS\Desktop\stock-backtest add gui/app.py tests/test_gui_app.py
git -C C:\Users\ASUS\Desktop\stock-backtest commit -m "feat: TraderApp 메인 창 (모드/시작/정지/로그)"
```

---

### Task 13: run_trader.py — 진입점 + 통합 스모크

**Files:**
- Create: `run_trader.py`
- Test: `tests/test_run_trader.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_run_trader.py
import json
import logging
import pytest

try:
    import tkinter as tk
    _r = tk.Tk(); _r.withdraw()
    _HAS_TK = True
except Exception:
    _HAS_TK = False

from run_trader import build_components


def _write_secrets(tmp_path):
    p = tmp_path / "kiwoom.json"
    p.write_text(json.dumps({
        "mode": "paper", "base_url": "https://mock.kiwoom.com",
        "app_key": "K", "app_secret": "S", "account_no": "1",
    }), encoding="utf-8")
    return p


@pytest.mark.skipif(not _HAS_TK, reason="Tkinter 사용 불가")
def test_build_components_wires_everything(tmp_path):
    sec = _write_secrets(tmp_path)
    state_path = tmp_path / "state.json"
    params_path = tmp_path / "params.json"
    universe_path = tmp_path / "universe.json"
    log = logging.getLogger("test")

    comps = build_components(secrets_path=sec,
                              state_path=state_path,
                              params_path=params_path,
                              universe_path=universe_path,
                              log=log)
    assert comps.credentials.mode == "paper"
    assert comps.state.mode == "paper"
    assert comps.params.top_k == 3
    assert comps.universe.entries == []
    assert comps.broker is not None
    assert comps.scheduler is not None
    comps.app.destroy()
```

- [ ] **Step 2: 실패 확인**

Run: `Push-Location C:\Users\ASUS\Desktop\stock-backtest; .\.venv\Scripts\python.exe -m pytest tests/test_run_trader.py -v; Pop-Location`
Expected: FAIL — `ModuleNotFoundError: No module named 'run_trader'`

> 주의: `run_backtest.py`가 이미 존재한다. 새 진입점은 별도 모듈 `run_trader.py`.

- [ ] **Step 3: 구현**

```python
# run_trader.py
import logging
from dataclasses import dataclass
from datetime import datetime, time as dtime
from pathlib import Path

from broker.credentials import Credentials
from broker.kiwoom import KiwoomClient
from gui.app import TraderApp
from live.executor import execute
from live.runner import decide
from live.scheduler import Scheduler
from live.state import TraderState, TraderParams
from live.universe_store import UniverseStore

DEFAULT_SECRETS = Path("secrets/kiwoom.json")
DEFAULT_STATE = Path("state/trader_state.json")
DEFAULT_PARAMS = Path("state/trader_params.json")
DEFAULT_UNIVERSE = Path("state/universe.json")
DEFAULT_LOG = Path("state/trader.log")


@dataclass
class TraderComponents:
    credentials: Credentials
    state: TraderState
    params: TraderParams
    universe: UniverseStore
    broker: KiwoomClient
    scheduler: Scheduler
    app: TraderApp


def _parse_hhmm(s: str) -> dtime:
    h, m = s.split(":")
    return dtime(int(h), int(m))


def build_components(secrets_path=DEFAULT_SECRETS,
                     state_path=DEFAULT_STATE,
                     params_path=DEFAULT_PARAMS,
                     universe_path=DEFAULT_UNIVERSE,
                     log=None) -> TraderComponents:
    log = log or logging.getLogger("trader")
    creds = Credentials.load(secrets_path=secrets_path)
    state = TraderState.load(state_path)
    state.mode = creds.mode  # 자격증명 모드를 신뢰
    params = TraderParams.load(params_path)
    universe = UniverseStore.load(universe_path)
    broker = KiwoomClient(base_url=creds.base_url,
                          app_key=creds.app_key,
                          app_secret=creds.app_secret,
                          account_no=creds.account_no)

    safety_params = {
        "max_position_pct": params.max_position_pct,
        "min_order_amount": params.min_order_amount,
        "max_daily_loss": params.max_daily_loss,
    }

    def on_trigger():
        try:
            from data.loader import build_panels
            close, _ = build_panels(universe.codes(),
                                     "2024-01-01",
                                     datetime.now().date().isoformat(),
                                     "data/cache")
            balance = broker.get_balance()
            holdings = broker.get_holdings()  # broker live; state 보유와 비교는 다음 단계 spec
            decision = decide(close, datetime.now().date(),
                               state.holdings, balance.get("cash", 0.0),
                               params, state)
            ok = execute(decision, broker, state, safety_params, log,
                          now=datetime.now())
            state.save(state_path)
            log.info(f"trigger 완료 ok={ok} action={decision.action} "
                     f"reason={decision.reason}")
        except Exception as e:
            log.exception(f"trigger 실패: {e}")
            state.halted = True
            state.save(state_path)

    scheduler = Scheduler(target_time=_parse_hhmm(params.target_time_hhmm),
                          on_trigger=on_trigger, tick_seconds=30)

    def on_start():
        scheduler.start(state_provider=lambda: state)
        log.info("자동매매 시작")
        app.refresh_mode()

    def on_stop():
        scheduler.stop()
        state.halted = True
        state.save(state_path)
        log.info("자동매매 정지 (HALTED)")
        app.refresh_mode()

    app = TraderApp(state=state, params=params, universe=universe,
                     on_start=on_start, on_stop=on_stop)

    return TraderComponents(credentials=creds, state=state, params=params,
                             universe=universe, broker=broker,
                             scheduler=scheduler, app=app)


def main():
    logging.basicConfig(level=logging.INFO,
                         format="%(asctime)s %(levelname)s %(message)s")
    log = logging.getLogger("trader")
    Path("state").mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(DEFAULT_LOG, encoding="utf-8")
    fh.setLevel(logging.INFO)
    log.addHandler(fh)
    comps = build_components(log=log)
    comps.app.mainloop()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 통과 확인**

Run: `Push-Location C:\Users\ASUS\Desktop\stock-backtest; .\.venv\Scripts\python.exe -m pytest tests/test_run_trader.py -v; Pop-Location`
Expected: PASS (1) — Tkinter 미사용 환경에서는 SKIPPED

- [ ] **Step 5: 전체 스위트 최종 확인**

Run: `Push-Location C:\Users\ASUS\Desktop\stock-backtest; .\.venv\Scripts\python.exe -m pytest -v; Pop-Location`
Expected: 모든 테스트 PASS (기존 백테스트 45개 + 신규 트레이더 약 40개)

- [ ] **Step 6: Commit**

```bash
git -C C:\Users\ASUS\Desktop\stock-backtest add run_trader.py tests/test_run_trader.py
git -C C:\Users\ASUS\Desktop\stock-backtest commit -m "feat: run_trader.py 진입점 + 통합 컴포넌트 와이어링"
```

---

## Self-Review

**1. Spec coverage:**

| 설계 문서 항목 | 구현 태스크 |
|---|---|
| §3 합법성·안전 전제 | §7(safety) + §2(credentials PAPER 강제) |
| §4 사용자 흐름 | Task 13(run_trader 통합) |
| §5 스택 | Task 0(requirements) |
| §6 아키텍처/모듈 책임 | Task 1–13 (1:1 매핑) |
| §6.1 broker.credentials PAPER 강제 | Task 2 |
| §6.1 broker.kiwoom http 주입·토큰 | Task 3, Task 4 |
| §6.1 live.state Holding/TraderState 원자적 | Task 5 |
| §6.1 live.safety 순수 함수 | Task 7 |
| §6.1 live.runner Decision 분기 | Task 8 |
| §6.1 live.executor fail-safe halt | Task 9 |
| §6.1 live.scheduler should_trigger + Scheduler | Task 10 |
| §6.1 live.universe_store | Task 6 |
| §6.1 gui.app / gui.panels | Task 11, Task 12 |
| §6.2 데이터 흐름 | Task 13 on_trigger |
| §6.3 신호=백테스트와 동일 (전략 재사용) | Task 8 (`strategy.momentum` import) |
| §6.3 idempotency (last_action_date) | Task 10 should_trigger + Task 9 execute |
| §6.3 불확실 시 NOOP+halt | Task 9 execute (모든 예외/거부 경로) |
| §6.3 킬스위치 = 정지 버튼 + halted | Task 12 click_stop + Task 13 on_stop |
| §6.4 안전 한도 기본값 | Task 5 TraderParams 기본값 + Task 9 적용 |
| §7 GUI 화면(좌 종목/파라미터, 우 모드/버튼/로그) | Task 11, Task 12 |
| §8 자격증명 파일/env | Task 2 |
| §9 키움 REST 구현 정책 | Task 3, Task 4 (Endpoints 분리, 문서로 확정) |
| §10 오류처리·로깅 | Task 9 (log 사용) + Task 13 (FileHandler) |
| §11 테스트 전략 | 전 태스크 TDD |

모든 spec 항목 매핑 완료. 누락 없음.

**2. Placeholder scan:** "TBD"/"TODO"/"적절히 처리" 없음. 모든 코드 스텝에 완전한 코드 포함. `KiwoomEndpoints` 기본값은 "추정 — 키움 문서 확정" 주석이 명시되어 있으나 이는 외부 의존 정책이지 플랜 내 미정 항목 아님.

**3. Type consistency:**
- `Credentials` 필드(`mode`, `base_url`, `app_key`, `app_secret`, `account_no`)는 Task 2 정의와 Task 13 사용에서 일치
- `KiwoomClient.__init__` 시그니처(`base_url, app_key, app_secret, account_no, endpoints=None, http=None, clock=time.time`)는 Task 3 정의와 Task 4·13 사용에서 일치
- `Holding(shares, entry_price, bought_at="")` 생성자는 Task 5 정의와 Task 7·8·9 사용에서 일치
- `TraderState` 필드(`mode, cash, holdings, last_rebalance_date, last_action_date, halted, equity_start_of_day`)는 Task 5 정의와 Task 7·9·10·12·13 사용에서 일치
- `TraderParams` 필드(특히 `target_time_hhmm`, `max_position_pct`, `min_order_amount`, `max_daily_loss`, `drift_tolerance`)는 Task 5 정의와 Task 9·13 사용에서 일치
- `Decision(action, orders, reason)` / `Order(code, side, qty, reason)`은 Task 8 정의와 Task 9·테스트에서 일치
- `execute(decision, broker, state, safety_params, log, now=None) -> bool`은 Task 9 정의와 Task 13 사용에서 일치
- `Scheduler(target_time, on_trigger, tick_seconds, clock)` + `start(state_provider)`/`stop()`은 Task 10 정의와 Task 13 사용에서 일치
- `should_trigger(now, target_time, last_action_date)`는 Task 10 정의와 Task 10 테스트에서 일치
- `UniversePanel(master, store)` / `ParamsPanel(master, params)` / `LogPanel(master)`는 Task 11 정의와 Task 12 사용에서 일치
- `TraderApp(state=, params=, universe=, on_start=, on_stop=)`는 Task 12 정의와 Task 13 사용에서 일치

불일치 없음.

---

## Execution Handoff

이 계획은 14개 태스크, 각 태스크는 TDD 5단계로 분해되어 있습니다. 기존 `stock-backtest` 저장소의 `strategy/`, `data/loader.py`, `config.py`를 그대로 재사용하므로 전략 검증 결과와 라이브 동작이 자동으로 일치합니다.
