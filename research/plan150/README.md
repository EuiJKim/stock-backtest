# plan150 — 월 150만원 적립 포트폴리오 월간 점검

2026-10 세션에서 만든 분석을 재현 가능하게 옮긴 것. 네트워크는 GitHub(raw/clone)만 필요.

```bash
pip install -r requirements.txt
python research/plan150/fetch_data.py        # 데이터 수집 → data/plan150/universe_krw.csv
python research/plan150/monthly_report.py    # 리포트 → data/plan150/report_<날짜>.md, history.csv
python research/plan150/monthly_report.py --weights "나스닥100:0.55,필라델피아반도체:0.2,코스피:0.25"
```

- 원화 환산 = 미국 ETF 수정종가 × 연준 H.10 원/달러. 코스피는 배당 제외 지수. 현금CD는 연 3% 가정.
- 미국 ETF는 sp500-data 릴리스(prices.parquet, 약 235MB, 평일 밤 갱신)에서 받는다. 2026-11 기존 소스(etf-eod)가 사라져 교체했고, 새 소스에 없는 SCHD(배당다우존스)는 빠져서 균형형 비교는 제외된다.
- 리포트 머리말의 "실제 기준일"이 자산별 마지막 시세 날짜다. 미국 ETF는 1~2거래일 늦을 수 있다.
- 나스닥100은 QQQ(1999~2019) + 나스닥100 지수(2019~) 접합. 한국 상장 ETF의 보수·괴리율은 미반영.
- 점검 규칙(공격형): docs/plans/2026-10-plan150-checklist.md
