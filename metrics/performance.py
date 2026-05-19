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
