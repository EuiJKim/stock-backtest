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
