import tkinter as tk
from tkinter import ttk

from gui.panels import UniversePanel, ParamsPanel, LogPanel


class TraderApp(tk.Toplevel):
    """
    메인 트레이더 창.
    tk._default_root 이 이미 존재하면 Toplevel 로 동작,
    없으면 내부적으로 숨겨진 Tk 루트를 만들어 그 위에 Toplevel 로 띄운다.
    destroy() 는 숨겨진 루트까지 정리한다.
    """

    def __init__(self, *, state, params, universe, on_start, on_stop):
        # 루트가 없으면 만들어 둔다 (테스트 환경에서도 안전)
        if tk._default_root is None:
            self._owned_root = tk.Tk()
            self._owned_root.withdraw()
        else:
            self._owned_root = None

        super().__init__()
        self.title("키움 모의투자 자동매매")
        self.geometry("960x600")
        self._state = state
        self._on_start = on_start
        self._on_stop = on_stop

        # 좌측: Universe + Params
        left = ttk.Frame(self); left.pack(side="left", fill="y", padx=8, pady=8)
        ttk.Label(left, text="ETF 종목").pack(anchor="w")
        self.universe_panel = UniversePanel(left, universe)
        self.universe_panel.pack(fill="x")
        ttk.Label(left, text="파라미터").pack(anchor="w", pady=(8, 0))
        self.params_panel = ParamsPanel(left, params)
        self.params_panel.pack(fill="x")

        # 우측 상: 모드 + 시작/정지
        right = ttk.Frame(self); right.pack(side="right", fill="both",
                                              expand=True, padx=8, pady=8)
        self._mode_var = tk.StringVar(value=self._mode_text())
        mode_lbl = ttk.Label(right, textvariable=self._mode_var,
                              font=("", 16, "bold"), foreground="green")
        mode_lbl.pack(anchor="w")

        btns = ttk.Frame(right); btns.pack(fill="x", pady=4)
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

    def destroy(self) -> None:
        super().destroy()
        if self._owned_root is not None:
            try:
                self._owned_root.destroy()
            except Exception:
                pass
            self._owned_root = None

    def mainloop(self, n=0):
        """루트가 있으면 루트의 mainloop, 없으면 Toplevel 의 기본 동작."""
        if self._owned_root is not None:
            self._owned_root.mainloop(n)
        else:
            super().mainloop(n)
