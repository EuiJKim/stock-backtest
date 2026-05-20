import tkinter as tk
import pytest


@pytest.fixture
def app_factory(tk_root):
    """Construct a TraderApp that inherits tk.Toplevel so tests reuse the
    session fixture root instead of creating a new Tk interpreter."""
    from gui.app import _build_app_class
    from live.universe_store import UniverseStore
    from live.state import TraderState, TraderParams

    TestApp = _build_app_class(tk.Toplevel)
    created = []

    def make(state=None, params=None, universe=None,
             on_start=lambda: None, on_stop=lambda: None):
        a = TestApp(
            state=state or TraderState(mode="paper"),
            params=params or TraderParams(),
            universe=universe or UniverseStore(entries=[]),
            on_start=on_start, on_stop=on_stop,
            master=tk_root,
        )
        created.append(a)
        return a

    yield make

    for a in created:
        try:
            a.destroy()
        except Exception:
            pass


def test_app_constructs_and_shows_paper_mode(app_factory):
    app = app_factory()
    assert "PAPER" in app.mode_label_text()


def test_app_start_stop_invoke_callbacks(app_factory):
    starts = []
    stops = []
    app = app_factory(on_start=lambda: starts.append(1),
                       on_stop=lambda: stops.append(1))
    app.click_start()
    app.click_stop()
    assert starts == [1] and stops == [1]


def test_app_logs_messages(app_factory):
    app = app_factory()
    app.log("hello world")
    assert "hello world" in app.log_text()
