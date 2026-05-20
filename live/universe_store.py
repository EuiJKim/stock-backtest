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
