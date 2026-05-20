# 키움 모의투자 자동매매 GUI 앱 — 설계 문서

- 작성일: 2026-05-20
- 상태: 승인됨 (구현 계획 수립 대기)
- 프로젝트: `stock-backtest` 저장소에 추가 (백테스트와 전략 로직 공유)

## 1. 목적

`stock-backtest`에서 검증한 듀얼 모멘텀 로테이션 + 익절 전략을 **키움증권 모의투자 계좌에서 자동으로 매매**하는 데스크톱 앱을 만든다. 사용자는 간단한 GUI 창에서 ETF 종목 목록과 파라미터를 편집하고, 시작/정지 버튼으로 자동매매를 제어한다.

이번 단계는 **모의투자(가짜 돈) 자동매매에 한정**한다. 실계좌 실전 매매는 별도 후속 spec에서 다룬다 — 검증된 모의 동작을 환경값만 바꿔 승격하는 구조로 설계한다.

## 2. 비목표 (이번 범위에서 제외)

- 실계좌·실제 돈 자동매매 (다음 spec)
- .exe 단일 실행파일 패키징 (다음 spec)
- 알림(텔레그램/이메일/푸시) — 로그/콘솔만
- 지정가·예약주문·분할주문 — 시장가만
- 멀티 전략 동시 운용 — 단일 전략
- 분배금 재투자 보정 (백테스트와 동일한 한계)
- 모바일·웹 UI

## 3. 합법성·안전 전제 (문서화)

본인 명의 키움 모의투자 계좌에서 본인이 직접 시작/정지하는 개인 자동매매가 대상이다. 이 앱은:

- **타인 자금을 운용하지 않는다** (투자일임업 해당 없음)
- **시세조종성 주문을 만들지 않는다** — 단순 모멘텀 신호의 시장가 매수/매도만
- **키움 API 이용약관을 준수한다** — 호출 빈도 제한, 인증 흐름 준수
- 실제 돈 손실 위험은 v2(실전)부터 발생. 본 spec은 가짜 돈만 다룬다

## 4. 사용자 흐름

1. 사용자가 키움 모의투자 가입 + REST API 앱키/시크릿/계좌번호 발급 (외부 준비)
2. 로컬 secrets 파일에 자격증명 입력 (gitignore)
3. `python run_trader.py` 또는 바로가기로 GUI 창 실행
4. 창에서 ETF 목록(종목코드)·파라미터·실행시각 확인/편집
5. 모드 표시기에 **PAPER** 확인 후 "시작" 클릭
6. 앱이 백그라운드에서 매 거래일 지정시각에 신호 산출 → 안전검증 → 모의 주문 → 로그 표시
7. "정지" = 즉시 중단 (킬스위치) — 추가 주문 없음

## 5. 스택

- Python 3.11+ (기존 백테스트와 동일 venv)
- 신규 의존성: `requests`(키움 REST), `tkinter`(stdlib — 추가 설치 불필요)
- 재사용: `finance-datareader`, `pandas`, `numpy` (기존)
- 테스트: `pytest` (기존)

## 6. 아키텍처

기존 `stock-backtest` 저장소에 다음 패키지를 추가한다:

```
stock-backtest/
  broker/
    __init__.py
    kiwoom.py            # 키움 REST 클라이언트 (OAuth, 시세, 잔고, 주문)
    credentials.py       # 자격증명 로더 (env/secrets 파일)
  live/
    __init__.py
    state.py             # 영속 상태 (JSON): 보유·진입가·마지막리밸런싱일·당일처리여부
    safety.py            # 안전장치 (모드·한도·킬스위치·KRX시간·드리프트가드)
    runner.py            # 결정 엔진 (전략→주문 의도 산출)
    executor.py          # 주문 실행 (broker 호출 + 상태/로그 기록)
    scheduler.py         # 백그라운드 스케줄러 (지정시각 + 수동실행)
    universe_store.py    # 사용자 편집 가능한 종목 목록 영속화
  gui/
    __init__.py
    app.py               # Tkinter 메인 창
    panels.py            # 종목편집·파라미터·로그 패널
  run_trader.py          # 진입점 (GUI 부팅)
  secrets/               # gitignore (앱키·시크릿·계좌번호 보관)
    .gitkeep
  state/                 # gitignore (영속 상태 JSON)
    .gitkeep
  tests/
    test_kiwoom_client.py
    test_state.py
    test_safety.py
    test_runner.py
    test_executor.py
    test_universe_store.py
```

재사용 모듈(변경 없음): `strategy/momentum.py`, `config.py`, `data/loader.py`, `metrics/`(미사용), `engine/`(미사용).

### 6.1 모듈 책임 (단일 책임 · 명확한 경계)

- **`broker.kiwoom`**: 키움 REST 클라이언트. `KiwoomClient(base_url, app_key, app_secret, account, http=requests)` — `http`를 주입 가능하게 만들어 네트워크 없는 테스트 가능. 메서드: `get_token()`, `get_quote(code)`, `get_balance()`, `get_holdings()`, `place_order(code, side, qty, order_type="market")`, `get_order_status(order_id)`. 토큰 만료 시 자동 갱신.
- **`broker.credentials`**: `Credentials.load()` — `secrets/kiwoom.json` 또는 환경변수에서 로드. 모드 플래그(`paper`/`live`)와 `base_url` 같이 노출. 본 spec에서는 `paper`만 허용 (`live`는 명시 차단).
- **`live.state`**: `TraderState` JSON 직렬화 객체. 필드: `mode`, `holdings: {code: {shares, entry_price, bought_at}}`, `cash`, `last_rebalance_date`, `last_tp_check_date`, `last_action_date`, `halted: bool`. `load()`/`save()` 원자적 쓰기(temp+rename).
- **`live.safety`**: 순수 함수 모음. `validate_mode(creds) -> None`(live면 raise), `is_market_open(now, calendar) -> bool`, `within_position_limit(target_notional, equity, max_pct) -> bool`, `daily_loss_kill(equity_today, equity_start_day, max_loss_pct) -> bool`, `holdings_drift_ok(state, broker_holdings, tolerance) -> bool`, `order_size_ok(notional, min, max) -> bool`. 어떤 검사든 실패하면 호출자에게 거부 사유를 돌려줘 fail-safe.
- **`live.runner`**: 결정 엔진(순수). 입력: 가격패널(FDR), 현재 보유(키움), 현금, 현재일시, 파라미터, 상태. 출력: `Decision { action: "REBALANCE"|"TAKE_PROFIT"|"NOOP", orders: [...], reason }`. 신호 계산은 `strategy/momentum.py`를 그대로 호출. 익절 판정은 state의 진입가 사용. **체결 없음**.
- **`live.executor`**: `Decision`+broker를 받아 실제 모의 주문 실행. 안전검증을 한 번 더 통과시킨 뒤만 주문. 결과(주문ID·체결가·수량) state에 기록. 부분체결·거부는 로그+중단(추측 금지).
- **`live.scheduler`**: 백그라운드 스레드. tick 주기(기본 30초)로 깨어 "오늘 지정시각이 지났고 아직 미처리이면 1회 실행". 수동 "지금 실행" 트리거. 정지 신호로 즉시 종료.
- **`live.universe_store`**: 사용자 편집 ETF 목록을 `state/universe.json`에 저장/로드. 항목: `{name, code}` (코드 필수, name은 표시용). FinanceDataReader 매핑으로 추가 시 자동 보조.
- **`gui.app`**: Tkinter 메인 창. 시작 시 GUI 스레드에서 동작, 스케줄러를 별도 스레드로 띄움. 상태 갱신은 큐 폴링으로 안전하게.
- **`gui.panels`**: ETF 편집 패널(추가/삭제/코드입력+이름 자동완성), 파라미터 패널(top_k, 익절률, 절대모멘텀 토글, 실행시각), 모드 표시기(녹색 PAPER), 시작/정지 버튼, 로그 뷰(텍스트 박스).

### 6.2 데이터 흐름

```
GUI 시작 → 스케줄러 스레드 시작
  ↓ tick (30s)
지정시각 지남 & 미처리?
  ↓ yes
broker.get_holdings/get_balance       (현재 보유·현금)
data.loader.build_panels(FDR)         (모멘텀용 과거 시세)
runner.decide(panels, holdings, ...)  (전략 신호 → Decision)
safety.validate(Decision)             (모드·한도·시간·드리프트)
executor.execute(Decision, broker)    (모의 주문)
state.save                            (영속화)
GUI.log_queue.put(요약)               (로그 표시)
```

### 6.3 핵심 동작 규칙

- **신호=백테스트와 동일**: 12-1 모멘텀·상위 K 동일비중·절대모멘텀·+5% 익절·월 1회 리밸런싱. 파라미터는 GUI에서 조정.
- **시그널 가격 vs 주문 가격**: 신호 산출은 FDR 종가, 주문은 키움 모의 시장가. 둘 사이 약간의 차이 발생 가능 — 허용. (백테스트는 "다음날 시가"였으나 실시간은 즉시 시장가로 단순화)
- **상태 기반 idempotency**: `state.last_action_date == today`면 그 날 추가 실행 거부. PC를 껐다 켜도 이중주문 없음.
- **불확실 시 NOOP**: 키움 보유와 state의 보유가 허용오차 밖이면(드리프트), 네트워크/주문 거부/부분체결이면 → **자동 NOOP + 로그 + 정지(수동 확인 요구)**. 절대 추측 주문 안 함.
- **킬스위치**: GUI "정지"는 스케줄러 즉시 종료 + `state.halted=true` 영속화. 재시작 시 halted면 사용자 명시적 해제 전까지 거래 안 함.

### 6.4 안전 한도 (기본값, GUI에서 편집 가능)

| 항목 | 기본값 | 의미 |
|---|---|---|
| 모드 | `paper` (강제) | 본 spec에서 `live` 차단 |
| 종목당 최대비중 | 40% | top_k=3 → 33%이므로 여유 |
| 최소 주문 금액 | 10,000원 | 너무 작은 주문 방지 |
| 일일 손실 킬스위치 | -5% | 당일 평가손익 < -5%면 모든 신규 주문 중단 |
| KRX 거래시간 | 09:00–15:30 KST | 그 외 시간 거부 |
| 실행시각 | 15:15 KST | 장마감 15분 전 (체결 안정성) |
| 드리프트 허용오차 | 종목당 ±5% 수량 | 그 이상 차이 시 NOOP+정지 |
| 호출 백오프 | 0.5/1/2/5초 4회 | 키움 API 일시오류 시 |

## 7. GUI 화면

단일 창, 좌우 2분할:

- **좌측**: 종목 편집 (테이블: name/code, 추가/삭제 버튼, 이름 입력 시 FDR로 코드 자동완성), 파라미터(top_k, 모멘텀 lookback, 익절률, 절대모멘텀 ON/OFF, 실행시각), 안전한도 보기/편집
- **우측 상**: 모드 표시기(녹색 `PAPER`, 빨간 `HALTED`), 계좌 요약(평가금액·현금·보유 종목), 시작/정지 큰 버튼
- **우측 하**: 실시간 로그 (스크롤 텍스트, 거래/오류/안전중단 사유)

저장 버튼으로 종목·파라미터를 영속화. 시작 후에는 종목 편집 잠금(혼동 방지) — 정지 후 재편집.

## 8. 자격증명 관리

- 파일: `secrets/kiwoom.json` (gitignore). 형식:
  ```json
  {
    "mode": "paper",
    "base_url": "<키움 모의투자 REST base>",
    "app_key": "...",
    "app_secret": "...",
    "account_no": "..."
  }
  ```
- 환경변수 대안: `KIWOOM_APP_KEY`, `KIWOOM_APP_SECRET`, `KIWOOM_ACCOUNT_NO`, `KIWOOM_BASE_URL`, `KIWOOM_MODE`
- `Credentials.load()`은 secrets 파일 우선, 없으면 env. `mode != "paper"`이면 본 spec에서 즉시 오류 (안전).
- `.gitignore`에 `secrets/*`, `state/*` 추가.

## 9. 키움 REST 클라이언트 — 구현 정책

키움 REST의 정확한 엔드포인트 경로·요청/응답 스키마는 **키움 공식 API 포털 문서**에서 확정한다. 본 spec은 **인터페이스(메서드 시그니처)와 동작 의미**만 고정하고, 내부 HTTP 호출은 구현 단계에서 키움 문서 기준으로 채운다. 추측 금지.

- `KiwoomClient(...)` 메서드 시그니처는 §6.1대로 고정
- 모든 HTTP는 `requests.Session`을 `http=` 파라미터로 주입 (테스트에서 가짜 응답)
- 4xx/5xx 오류는 예외로 변환, 재시도 정책은 호출자(executor)에서 백오프 4회
- 응답 파싱은 별도 함수로 분리(단위 테스트 가능)

## 10. 오류 처리·로깅

- 모든 외부 호출 try/except, 예외는 `live.errors`의 도메인 예외로 변환
- 로그: 표준 `logging`, 파일(`state/trader.log`) + GUI 로그 패널 동시 출력
- 거래 결정과 그 이유, 안전 거부 사유, 키움 응답 요약을 한 줄 JSON으로 남겨 추후 분석 가능
- 치명적 오류(자격증명 누락, 모드 위반, 드리프트) → 즉시 `halted=true` + GUI 빨간 표시

## 11. 테스트 전략

- `broker.kiwoom`: 가짜 HTTP 객체(`http.post/get`)로 토큰 발급·시세·잔고·주문 흐름 단위 테스트. 네트워크 없이 100% 결정적.
- `live.state`: JSON 라운드트립, 원자적 쓰기(부분 쓰기에도 깨지지 않음) 테스트
- `live.safety`: 각 검사함수 경계값(시간 경계, 한도 초과, 드리프트 경계) 테스트
- `live.runner`: 합성 가격패널 + 합성 보유로 결정 산출 결정적 테스트, REBALANCE/TAKE_PROFIT/NOOP 분기 모두 커버
- `live.executor`: 가짜 broker로 정상 주문, 거부, 부분체결, 예외 시나리오 → 상태 갱신/중단 동작 검증
- `live.universe_store`: 추가·삭제·저장·로드 라운드트립
- `gui.app`: 생성 스모크(인스턴스화·핵심 위젯 존재) 정도만. 본격 GUI 자동화는 비목표.
- 신호 계산은 `strategy/momentum.py`의 기존 테스트 그대로 (재사용 검증)

## 12. 알려진 한계 (의도된 단순화)

- 시장가만 지원 — 슬리피지·체결가 변동 그대로 받음
- FDR 종가 기반 신호 → 실제 키움 시세와 미세 괴리 가능
- 분배금 미반영 (백테스트와 동일 한계)
- 단일 통화(KRW), 환헤지 구분 없음
- 멀티 계좌·멀티 전략 미지원
- 키움 REST 정확한 스펙은 외부 의존 (구현 시 문서 확인 필요)

## 13. 후속 단계 (범위 밖)

1. **실전 승격(v2)**: `mode=live` 활성화, 추가 확인 다이얼로그, 더 엄격한 한도, 사고대비 백업
2. **.exe 패키징**: PyInstaller로 단일 실행파일 빌드
3. **알림**: 텔레그램/이메일/시스템 알림 통합
4. **고급 주문**: 지정가·예약·분할주문
5. **모니터링 대시보드**: 누적 성과·일별 PnL·차트
