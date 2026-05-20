import logging
import queue
import tkinter as tk
from tkinter import ttk

from gui.panels import UniversePanel, ParamsPanel, LogPanel


class GuiLogHandler(logging.Handler):
    """logging.Handler that routes records to the TraderApp log panel."""

    def __init__(self, app: "TraderApp"):
        super().__init__()
        self.app = app

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.app.log(self.format(record))
        except Exception:
            self.handleError(record)


def _build_app_class(base):
    """Return a TraderApp class inheriting from *base* (tk.Tk or tk.Toplevel).

    Production always uses tk.Tk.  Tests call this with tk.Toplevel to
    reuse a session fixture root without creating a new Tcl interpreter.
    """

    class TraderApp(base):
        """메인 트레이더 창."""

        def __init__(self, *, state, params, universe, on_start, on_stop,
                     params_path=None, universe_path=None, **kwargs):
            super().__init__(**kwargs)
            self.title("키움 모의투자 자동매매")
            self.geometry("960x600")
            self._state = state
            self._on_start = on_start
            self._on_stop = on_stop
            self._params_path = params_path
            self._universe_path = universe_path
            # Thread-safe queue for deferred GUI updates from worker threads
            self._gui_queue: queue.Queue = queue.Queue()

            # 좌측: Universe + Params
            left = ttk.Frame(self)
            left.pack(side="left", fill="y", padx=8, pady=8)
            ttk.Label(left, text="ETF 종목").pack(anchor="w")
            self.universe_panel = UniversePanel(left, universe)
            self.universe_panel.pack(fill="x")
            ttk.Label(left, text="파라미터").pack(anchor="w", pady=(8, 0))
            self.params_panel = ParamsPanel(left, params)
            self.params_panel.pack(fill="x")

            # 우측 상: 모드 + 시작/정지
            right = ttk.Frame(self)
            right.pack(side="right", fill="both", expand=True, padx=8, pady=8)
            self._mode_var = tk.StringVar(value=self._mode_text())
            ttk.Label(right, textvariable=self._mode_var,
                      font=("", 16, "bold"), foreground="green").pack(anchor="w")

            btns = ttk.Frame(right)
            btns.pack(fill="x", pady=4)
            self._start_btn = ttk.Button(btns, text="시작",
                                          command=self.click_start)
            self._start_btn.pack(side="left", padx=4)
            self._stop_btn = ttk.Button(btns, text="정지",
                                         command=self.click_stop)
            self._stop_btn.pack(side="left", padx=4)
            if params_path is not None or universe_path is not None:
                self._save_btn = ttk.Button(btns, text="저장",
                                             command=self.click_save)
                self._save_btn.pack(side="left", padx=4)

            # 우측 하: 로그
            ttk.Label(right, text="로그").pack(anchor="w", pady=(8, 0))
            self.log_panel = LogPanel(right)
            self.log_panel.pack(fill="both", expand=True)

            # Start polling the thread-safe queue
            self._poll_gui_queue()

        def _mode_text(self) -> str:
            if getattr(self._state, "halted", False):
                return "HALTED"
            return f"MODE: {self._state.mode.upper()}"

        def mode_label_text(self) -> str:
            return self._mode_var.get()

        def _poll_gui_queue(self) -> None:
            """Drain the thread-safe queue and apply pending GUI updates."""
            try:
                while True:
                    fn = self._gui_queue.get_nowait()
                    fn()
            except queue.Empty:
                pass
            # Reschedule: safe because this always runs on the main Tk thread
            self.after(50, self._poll_gui_queue)

        def refresh_mode(self) -> None:
            # thread-safe: enqueue the widget update for the Tk main loop
            self._gui_queue.put(lambda: self._mode_var.set(self._mode_text()))

        def click_start(self) -> None:
            self._on_start()

        def click_stop(self) -> None:
            self._on_stop()

        def click_save(self) -> None:
            if self._params_path is not None:
                params = self.params_panel.read()
                params.save(self._params_path)
            if self._universe_path is not None:
                self.universe_panel.store.save(self._universe_path)
            self.log("저장됨")

        def log(self, line: str) -> None:
            # thread-safe: enqueue the widget update for the Tk main loop
            self._gui_queue.put(lambda l=line: self.log_panel.append(l))

        def flush_gui_queue(self) -> None:
            """Drain all pending GUI callbacks immediately (test helper)."""
            try:
                while True:
                    fn = self._gui_queue.get_nowait()
                    fn()
            except queue.Empty:
                pass

        def log_text(self) -> str:
            return self.log_panel.text()

    return TraderApp


# Production class — inherits from tk.Tk (IS the root window).
TraderApp = _build_app_class(tk.Tk)
