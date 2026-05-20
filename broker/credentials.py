from dataclasses import dataclass
import json
from pathlib import Path

from live.errors import CredentialsError

_REQUIRED = ("mode", "base_url", "app_key", "app_secret", "account_no")
_ENV_KEYS = {
    "mode": "KIWOOM_MODE", "base_url": "KIWOOM_BASE_URL",
    "app_key": "KIWOOM_APP_KEY", "app_secret": "KIWOOM_APP_SECRET",
    "account_no": "KIWOOM_ACCOUNT_NO",
}


@dataclass
class Credentials:
    mode: str
    base_url: str
    app_key: str
    app_secret: str
    account_no: str

    @classmethod
    def load(cls, secrets_path=None, env=None) -> "Credentials":
        data = {}
        p = Path(secrets_path) if secrets_path else None
        if p and p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                raise CredentialsError(f"secrets 파일 손상: {e}") from e
        else:
            e = env or {}
            data = {k: e[v] for k, v in _ENV_KEYS.items() if v in e}
        missing = [k for k in _REQUIRED if not data.get(k)]
        if missing:
            raise CredentialsError(f"자격증명 누락: {missing}")
        if data["mode"] != "paper":
            raise CredentialsError(
                f"이 빌드는 paper 모드만 허용; got mode={data['mode']!r}")
        return cls(**{k: data[k] for k in _REQUIRED})
