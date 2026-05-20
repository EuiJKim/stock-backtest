import json
import logging
import tkinter as tk
import pytest

from run_trader import build_components


def _write_secrets(tmp_path):
    p = tmp_path / "kiwoom.json"
    p.write_text(json.dumps({
        "mode": "paper", "base_url": "https://mock.kiwoom.com",
        "app_key": "K", "app_secret": "S", "account_no": "1",
    }), encoding="utf-8")
    return p


def test_build_components_wires_everything(tk_root, tmp_path):
    """build_components should wire all components correctly.

    TraderApp is constructed with app_master=tk_root so it runs as a
    Toplevel and reuses the session fixture Tk interpreter.
    """
    sec = _write_secrets(tmp_path)
    log = logging.getLogger("test")
    comps = build_components(
        secrets_path=sec,
        state_path=tmp_path / "state.json",
        params_path=tmp_path / "params.json",
        universe_path=tmp_path / "universe.json",
        log=log,
        app_master=tk_root,
    )
    try:
        assert comps.credentials.mode == "paper"
        assert comps.state.mode == "paper"
        assert comps.params.top_k == 3
        assert comps.universe.entries == []
        assert comps.broker is not None
        assert comps.scheduler is not None
    finally:
        comps.app.destroy()
