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
