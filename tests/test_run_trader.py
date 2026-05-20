import json
import logging
import pytest

try:
    import tkinter as tk
    _r = tk.Tk(); _r.withdraw()
    _HAS_TK = True
except Exception:
    _HAS_TK = False

from run_trader import build_components


def _write_secrets(tmp_path):
    p = tmp_path / "kiwoom.json"
    p.write_text(json.dumps({
        "mode": "paper", "base_url": "https://mock.kiwoom.com",
        "app_key": "K", "app_secret": "S", "account_no": "1",
    }), encoding="utf-8")
    return p


@pytest.mark.skipif(not _HAS_TK, reason="Tkinter 사용 불가")
def test_build_components_wires_everything(tmp_path):
    sec = _write_secrets(tmp_path)
    state_path = tmp_path / "state.json"
    params_path = tmp_path / "params.json"
    universe_path = tmp_path / "universe.json"
    log = logging.getLogger("test")

    comps = build_components(secrets_path=sec,
                              state_path=state_path,
                              params_path=params_path,
                              universe_path=universe_path,
                              log=log)
    assert comps.credentials.mode == "paper"
    assert comps.state.mode == "paper"
    assert comps.params.top_k == 3
    assert comps.universe.entries == []
    assert comps.broker is not None
    assert comps.scheduler is not None
    comps.app.destroy()
