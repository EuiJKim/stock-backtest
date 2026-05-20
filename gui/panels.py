import tkinter as tk
from tkinter import ttk

from live.state import TraderParams
from live.universe_store import UniverseEntry, UniverseStore


class UniversePanel(ttk.Frame):
    def __init__(self, master, store: UniverseStore):
        super().__init__(master)
        self.store = store
        self.tree = ttk.Treeview(self, columns=("name", "code"),
                                  show="headings", height=10)
        self.tree.heading("name", text="이름")
        self.tree.heading("code", text="종목코드")
        self.tree.column("code", width=80)
        self.tree.pack(fill="both", expand=True)

        form = ttk.Frame(self); form.pack(fill="x")
        self.name_var = tk.StringVar(); self.code_var = tk.StringVar()
        ttk.Label(form, text="이름").pack(side="left")
        ttk.Entry(form, textvariable=self.name_var, width=24).pack(side="left")
        ttk.Label(form, text="코드").pack(side="left")
        ttk.Entry(form, textvariable=self.code_var, width=10).pack(side="left")
        ttk.Button(form, text="추가",
                    command=self._on_add).pack(side="left")
        ttk.Button(form, text="선택삭제",
                    command=self._on_remove_selected).pack(side="left")
        self._refresh()

    def _refresh(self):
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        for e in self.store.entries:
            self.tree.insert("", "end", iid=e.code, values=(e.name, e.code))

    def _on_add(self):
        n = self.name_var.get().strip()
        c = self.code_var.get().strip()
        if n and c:
            self.add_entry(n, c)
            self.name_var.set(""); self.code_var.set("")

    def _on_remove_selected(self):
        sel = self.tree.selection()
        for iid in sel:
            self.remove_entry(iid)

    def add_entry(self, name: str, code: str) -> None:
        self.store.add(UniverseEntry(name=name, code=code))
        self._refresh()

    def remove_entry(self, code: str) -> None:
        self.store.remove(code)
        self._refresh()

    def row_count(self) -> int:
        return len(self.tree.get_children())


class ParamsPanel(ttk.Frame):
    def __init__(self, master, params: TraderParams):
        super().__init__(master)
        self._top_k = tk.IntVar(value=params.top_k)
        self._tp_pct = tk.DoubleVar(value=params.take_profit_pct)
        self._use_tp = tk.BooleanVar(value=params.use_take_profit)
        self._use_abs = tk.BooleanVar(value=params.use_absolute_momentum)
        self._target = tk.StringVar(value=params.target_time_hhmm)
        for label, var in (("Top K", self._top_k), ("익절률", self._tp_pct),
                            ("실행시각(HH:MM)", self._target)):
            row = ttk.Frame(self); row.pack(fill="x")
            ttk.Label(row, text=label, width=14).pack(side="left")
            ttk.Entry(row, textvariable=var).pack(side="left")
        ttk.Checkbutton(self, text="익절 사용",
                         variable=self._use_tp).pack(anchor="w")
        ttk.Checkbutton(self, text="절대 모멘텀 사용",
                         variable=self._use_abs).pack(anchor="w")
        self._template = params

    def set_top_k(self, k: int) -> None: self._top_k.set(k)
    def set_take_profit_pct(self, p: float) -> None: self._tp_pct.set(p)

    def read(self) -> TraderParams:
        out = TraderParams(**{**self._template.__dict__})
        out.top_k = int(self._top_k.get())
        out.take_profit_pct = float(self._tp_pct.get())
        out.use_take_profit = bool(self._use_tp.get())
        out.use_absolute_momentum = bool(self._use_abs.get())
        out.target_time_hhmm = str(self._target.get())
        return out


class LogPanel(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self._text = tk.Text(self, height=15, wrap="none")
        self._text.pack(fill="both", expand=True)

    def append(self, line: str) -> None:
        self._text.insert("end", line.rstrip() + "\n")
        self._text.see("end")

    def text(self) -> str:
        return self._text.get("1.0", "end")
