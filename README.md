# stock-backtest

ETF 듀얼 모멘텀 로테이션 + 익절 전략 백테스트, 고정 비중 포트폴리오 백테스트.

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

## 고정 비중 포트폴리오 (나스닥100 70 / 필라델피아반도체 30)

```bash
python run_portfolio.py                          # 70/30 매월 리밸런싱 + 매수후보유·단일자산·S&P500 비교
python run_portfolio.py --rebalance quarterly    # none | monthly | quarterly | yearly
python run_portfolio.py --band 0.05              # 목표 대비 5%p 이탈 시에도 리밸런싱
python run_portfolio.py --compare-rebalance      # 4개 리밸런싱 규칙 한 표 비교
python run_portfolio.py --weights "TIGER 미국나스닥100:0.6,TIGER 미국필라델피아반도체나스닥:0.4"
python run_portfolio.py --codes "133690:0.7,381180:0.3" --offline   # 리스팅 조회 없이 코드로 지정
```

- 신호는 종가, 체결은 다음 거래일 시가. 수수료 0.015% + 슬리피지 0.035% 편도.
- 구간은 모든 자산 시세가 존재하는 공통 구간 (TIGER 미국필라델피아반도체나스닥 상장 2021-04 이후).
- 결과: `report_output_portfolio/summary.html`, `compare.png`, `weights.png`, `equity_curves.csv`.
- 오프라인: `data/cache/<코드>.csv`(Date 인덱스, Open/Close 열)가 있으면 네트워크 없이 사용.

설계: `docs/specs/2026-05-19-etf-momentum-backtest-design.md`
