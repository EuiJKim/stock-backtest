from dataclasses import dataclass, field
import time

from live.retry import with_backoff


@dataclass
class KiwoomEndpoints:
    """엔드포인트 경로. 기본값은 추정 — 키움 공식 API 문서로 확정 후 조정."""
    token: str = "/oauth2/token"
    quote: str = "/api/dostk/stkinfo"
    balance: str = "/api/dostk/acnt/balance"
    holdings: str = "/api/dostk/acnt/holdings"
    order: str = "/api/dostk/ordr"
    order_status: str = "/api/dostk/ordr/status"


class KiwoomClient:
    def __init__(self, base_url, app_key, app_secret, account_no,
                 endpoints=None, http=None, clock=time.time,
                 sleep=time.sleep,
                 retry_delays=(0.5, 1.0, 2.0, 5.0)):
        self.base_url = base_url.rstrip("/")
        self.app_key = app_key
        self.app_secret = app_secret
        self.account_no = account_no
        self.endpoints = endpoints or KiwoomEndpoints()
        self.http = http if http is not None else _default_http()
        self._clock = clock
        self._token = None
        self._token_expires_at = 0.0
        self._sleep = sleep
        self._retry_delays = retry_delays

    def _retry(self, fn):
        return with_backoff(fn, delays=self._retry_delays, sleep=self._sleep)

    def get_token(self) -> str:
        if self._token and self._clock() < self._token_expires_at - 60:
            return self._token
        url = self.base_url + self.endpoints.token

        def _do():
            resp = self.http.post(url, json={
                "grant_type": "client_credentials",
                "appkey": self.app_key,
                "secretkey": self.app_secret,
            }, timeout=10)
            resp.raise_for_status()
            return resp.json()

        data = self._retry(_do)
        self._token = data["token"]
        ttl = float(data.get("expires_in", 3600))
        self._token_expires_at = self._clock() + ttl
        return self._token

    def _auth_headers(self):
        return {"Authorization": f"Bearer {self.get_token()}"}

    def get_quote(self, code) -> float:
        url = self.base_url + self.endpoints.quote

        def _do():
            resp = self.http.get(url, params={"code": code},
                                 headers=self._auth_headers(), timeout=10)
            resp.raise_for_status()
            return resp.json()

        return float(self._retry(_do)["price"])

    def get_balance(self) -> dict:
        url = self.base_url + self.endpoints.balance

        def _do():
            resp = self.http.get(url, params={"account_no": self.account_no},
                                 headers=self._auth_headers(), timeout=10)
            resp.raise_for_status()
            return resp.json()

        d = self._retry(_do)
        return {"cash": float(d["cash"]), "equity": float(d["equity"])}

    def get_holdings(self) -> dict:
        url = self.base_url + self.endpoints.holdings

        def _do():
            resp = self.http.get(url, params={"account_no": self.account_no},
                                 headers=self._auth_headers(), timeout=10)
            resp.raise_for_status()
            return resp.json()

        items = self._retry(_do).get("holdings", [])
        return {item["code"]: {"shares": int(item["shares"]),
                                "avg_price": float(item["avg_price"])}
                for item in items}

    def place_order(self, code, side, qty) -> str:
        # NOTE: place_order is intentionally NOT wrapped with _retry.
        # Auto-retrying writes risks duplicate orders (spec §6.3 / §9).
        # On failure the exception propagates to the executor which halts
        # the trader — correct fail-safe behavior.
        url = self.base_url + self.endpoints.order
        payload = {
            "account_no": self.account_no, "code": code,
            "side": side, "qty": int(qty), "order_type": "MARKET",
        }
        resp = self.http.post(url, json=payload,
                              headers=self._auth_headers(), timeout=10)
        resp.raise_for_status()
        return str(resp.json()["order_id"])

    def get_order_status(self, order_id) -> dict:
        url = self.base_url + self.endpoints.order_status

        def _do():
            resp = self.http.get(url, params={"order_id": order_id},
                                 headers=self._auth_headers(), timeout=10)
            resp.raise_for_status()
            return resp.json()

        d = self._retry(_do)
        return {"order_id": order_id, "status": d["status"],
                "filled_qty": int(d.get("filled_qty", 0)),
                "fill_price": float(d.get("fill_price", 0.0))}


def _default_http():
    import requests
    return requests.Session()
