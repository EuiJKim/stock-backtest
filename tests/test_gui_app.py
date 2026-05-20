import threading
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
             on_start=lambda: None, on_stop=lambda: None, **kwargs):
        a = TestApp(
            state=state or TraderState(mode="paper"),
            params=params or TraderParams(),
            universe=universe or UniverseStore(entries=[]),
            on_start=on_start, on_stop=on_stop,
            master=tk_root,
            **kwargs,
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
    app.flush_gui_queue()  # drain the thread-safe queue
    assert "hello world" in app.log_text()


def test_app_log_is_thread_safe(app_factory):
    app = app_factory()
    t = threading.Thread(target=lambda: app.log("from-thread"))
    t.start()
    t.join(timeout=1.0)
    app.flush_gui_queue()  # drain the thread-safe queue
    assert "from-thread" in app.log_text()


def test_app_save_button_writes_files(app_factory, tmp_path):
    from live.universe_store import UniverseStore, UniverseEntry
    from live.state import TraderParams
    params_path = tmp_path / "params.json"
    universe_path = tmp_path / "universe.json"
    params = TraderParams(top_k=4)
    universe = UniverseStore(entries=[UniverseEntry("A", "111")])
    app = app_factory(params=params, universe=universe,
                      params_path=params_path, universe_path=universe_path)
    # Modify a param in the panel, then save
    app.params_panel.set_top_k(7)
    app.click_save()
    app.flush_gui_queue()  # drain the thread-safe queue for the log call
    assert params_path.exists() and universe_path.exists()
    written = TraderParams.load(params_path)
    assert written.top_k == 7
