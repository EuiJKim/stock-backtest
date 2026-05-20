import json
import pytest
from broker.credentials import Credentials
from live.errors import CredentialsError


def _write(tmp_path, data):
    p = tmp_path / "kiwoom.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_load_from_file(tmp_path):
    p = _write(tmp_path, {"mode": "paper",
                          "base_url": "https://mock.kiwoom.com",
                          "app_key": "K", "app_secret": "S",
                          "account_no": "1234"})
    c = Credentials.load(secrets_path=p)
    assert c.mode == "paper" and c.app_key == "K"
    assert c.account_no == "1234"


def test_load_from_env(tmp_path):
    env = {"KIWOOM_MODE": "paper",
           "KIWOOM_BASE_URL": "https://mock.kiwoom.com",
           "KIWOOM_APP_KEY": "K2", "KIWOOM_APP_SECRET": "S2",
           "KIWOOM_ACCOUNT_NO": "9999"}
    c = Credentials.load(secrets_path=tmp_path / "missing.json", env=env)
    assert c.app_key == "K2" and c.account_no == "9999"


def test_live_mode_rejected_in_this_build(tmp_path):
    p = _write(tmp_path, {"mode": "live", "base_url": "x",
                          "app_key": "K", "app_secret": "S",
                          "account_no": "1"})
    with pytest.raises(CredentialsError):
        Credentials.load(secrets_path=p)


def test_missing_field_raises(tmp_path):
    p = _write(tmp_path, {"mode": "paper"})  # base_url 등 누락
    with pytest.raises(CredentialsError):
        Credentials.load(secrets_path=p)
