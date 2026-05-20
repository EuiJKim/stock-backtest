import pytest

try:
    import tkinter as tk
    _r = tk.Tk(); _r.withdraw()
    _HAS_TK = True
except Exception:
    _HAS_TK = False

pytestmark = pytest.mark.skipif(not _HAS_TK, reason="Tkinter 사용 불가")


def test_app_constructs_and_shows_paper_mode():
    from gui.app import TraderApp
    from live.universe_store import UniverseStore
    from live.state import TraderState, TraderParams
    app = TraderApp(state=TraderState(mode="paper"),
                     params=TraderParams(),
                     universe=UniverseStore(entries=[]),
                     on_start=lambda: None, on_stop=lambda: None)
    assert "PAPER" in app.mode_label_text()
    app.destroy()


def test_app_start_stop_invoke_callbacks():
    from gui.app import TraderApp
    from live.universe_store import UniverseStore
    from live.state import TraderState, TraderParams
    starts = []; stops = []
    app = TraderApp(state=TraderState(mode="paper"),
                     params=TraderParams(),
                     universe=UniverseStore(entries=[]),
                     on_start=lambda: starts.append(1),
                     on_stop=lambda: stops.append(1))
    app.click_start()
    app.click_stop()
    assert starts == [1] and stops == [1]
    app.destroy()


def test_app_logs_messages():
    from gui.app import TraderApp
    from live.universe_store import UniverseStore
    from live.state import TraderState, TraderParams
    app = TraderApp(state=TraderState(mode="paper"),
                     params=TraderParams(),
                     universe=UniverseStore(entries=[]),
                     on_start=lambda: None, on_stop=lambda: None)
    app.log("hello world")
    assert "hello world" in app.log_text()
    app.destroy()
