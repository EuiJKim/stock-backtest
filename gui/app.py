import logging
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
                     **kwargs):
            super().__init__(**kwargs)
            self.title("키움 모의투자 자동매매")
            self.geometry("960x600")
            self._state = state
            self._on_start = on_start
            self._on_stop = on_stop

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

            # 우측 하: 로그
            ttk.Label(right, text="로그").pack(anchor="w", pady=(8, 0))
            self.log_panel = LogPanel(right)
            self.log_panel.pack(fill="both", expand=True)

        def _mode_text(self) -> str:
            if getattr(self._state, "halted", False):
                return "HALTED"
            return f"MODE: {self._state.mode.upper()}"

        def mode_label_text(self) -> str:
            return self._mode_var.get()

        def refresh_mode(self) -> None:
            self._mode_var.set(self._mode_text())

        def click_start(self) -> None:
            self._on_start()

        def click_stop(self) -> None:
            self._on_stop()

        def log(self, line: str) -> None:
            self.log_panel.append(line)

        def log_text(self) -> str:
            return self.log_panel.text()

    return TraderApp


# Production class — inherits from tk.Tk (IS the root window).
TraderApp = _build_app_class(tk.Tk)
