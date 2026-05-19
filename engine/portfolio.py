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
