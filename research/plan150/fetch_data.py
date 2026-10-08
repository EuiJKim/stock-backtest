"""월간 점검용 공개 데이터 수집 (네트워크: raw.githubusercontent.com + git clone만 필요).

출력: <out>/universe_krw.csv  (원화 환산 일별 종가, 열 = 자산명)
소스:
  - 미국 ETF 수정종가: github.com/sad-kitten/etf-eod (Yahoo, 매일 갱신)
  - QQQ 1999~2019 수정종가: github.com/nateGeorge/simulate_leveraged_ETFs
  - 나스닥100 지수 2019~: github.com/Chief-rich/nasdaq100-data
  - 원/달러: github.com/datasets/exchange-rates (연준 H.10)
  - 코스피: github.com/anextone/kospi-signal-data
"""
import argparse, os, subprocess, sys
import pandas as pd

RAW = "https://raw.githubusercontent.com"
TICK = {"S&P500": "VOO", "배당다우존스": "SCHD", "필라델피아반도체": "SOXX", "금": "GLD", "미국채7-10년": "IEF",
        "미국채20년+": "TLT", "미국단기채(현금)": "BIL", "헬스케어": "XLV", "에너지": "XLE", "인도": "INDA",
        "일본": "EWJ", "리츠": "VNQ", "비트코인": "IBIT"}


def sh(cmd, cwd=None):
    subprocess.run(cmd, shell=True, check=True, cwd=cwd)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--work", default="data/plan150_raw")
    p.add_argument("--out", default="data/plan150")
    a = p.parse_args()
    os.makedirs(a.work, exist_ok=True); os.makedirs(a.out, exist_ok=True)
    if not os.path.isdir(f"{a.work}/etf-eod"):
        sh(f"git clone -q --depth 1 https://github.com/sad-kitten/etf-eod.git {a.work}/etf-eod")
    else:
        sh("git pull -q", cwd=f"{a.work}/etf-eod")
    if not os.path.isdir(f"{a.work}/lev"):
        sh(f"git clone -q --depth 1 https://github.com/nateGeorge/simulate_leveraged_ETFs.git {a.work}/lev")
    for name, url in [("ndx.csv", f"{RAW}/Chief-rich/nasdaq100-data/main/data/ndx_daily/history.csv"),
                      ("fx.csv", f"{RAW}/datasets/exchange-rates/main/data/daily.csv"),
                      ("kospi.csv", f"{RAW}/anextone/kospi-signal-data/main/data/kospi_index.csv")]:
        sh(f"curl -sS --fail -o {a.work}/{name} --max-time 120 '{url}'")

    fx = pd.read_csv(f"{a.work}/fx.csv"); fx = fx[fx["Country"] == "South Korea"]
    fx = fx.assign(Date=pd.to_datetime(fx["Date"])).set_index("Date")["Exchange rate"].astype(float).sort_index()

    def us(t):
        s = pd.read_csv(f"{a.work}/etf-eod/prices/{t}.csv", parse_dates=["Date"]).set_index("Date")["Adj_Close"].sort_index()
        return s[~s.index.duplicated()]
    usd = pd.DataFrame({k: us(v) for k, v in TICK.items()})
    q = pd.read_csv(f"{a.work}/lev/eod_data/QQQ.csv", parse_dates=["Date"]).set_index("Date")["Adj_Close"]
    n = pd.read_csv(f"{a.work}/ndx.csv", parse_dates=["Date"]).set_index("Date")["Close"]
    splice = q.index[-1]; ratio = q.loc[splice] / n.loc[splice]
    usd["나스닥100"] = pd.concat([q.loc[:splice], n.loc[n.index > splice] * ratio]).sort_index()
    df = usd.join(fx.rename("fx"), how="left"); df["fx"] = df["fx"].ffill().bfill()
    krw = df.drop(columns="fx").mul(df["fx"], axis=0)
    ko = pd.read_csv(f"{a.work}/kospi.csv", parse_dates=["date"]).set_index("date")["close"]
    krw = krw.join(ko.rename("코스피"), how="outer").sort_index()
    krw["달러현금(환율)"] = df["fx"].reindex(krw.index).ffill()
    krw = krw.ffill(limit=5)
    krw.to_csv(f"{a.out}/universe_krw.csv")
    print(f"saved {a.out}/universe_krw.csv  {krw.index[0].date()} ~ {krw.index[-1].date()}  {len(krw.columns)} assets")


if __name__ == "__main__":
    main()
