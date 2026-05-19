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
