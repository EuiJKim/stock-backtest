# tests/test_kiwoom_retry.py
import pytest
from broker.kiwoom import KiwoomClient


class FakeResp:
    def __init__(self, j, s=200):
        self._j = j
        self.status_code = s

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")

    def json(self):
        return self._j


def _token_ok():
    return FakeResp({"token": "T", "expires_in": 3600})


class FlakyGetHttp:
    """First GET raises, second GET succeeds. POST (token) always succeeds."""

    def __init__(self, success_payload):
        self.gets = 0
        self.posts = 0
        self._success_payload = success_payload

    def post(self, url, json=None, headers=None, timeout=None):
        self.posts += 1
        return _token_ok()

    def get(self, url, params=None, headers=None, timeout=None):
        self.gets += 1
        if self.gets == 1:
            raise Exception("transient 502")
        return FakeResp(self._success_payload)


class FlakyPostHttp:
    """Token POST succeeds; non-token POST always raises."""

    def __init__(self):
        self.token_posts = 0
        self.other_posts = 0

    def post(self, url, json=None, headers=None, timeout=None):
        if "token" in url or "oauth" in url:
            self.token_posts += 1
            return _token_ok()
        self.other_posts += 1
        raise Exception("transient 502")

    def get(self, url, params=None, headers=None, timeout=None):
        return FakeResp({})


def _client(http, sleeps):
    return KiwoomClient(
        "https://mock.kiwoom.com", "K", "S", "1",
        http=http, clock=lambda: 0.0,
        sleep=lambda d: sleeps.append(d),
        retry_delays=(0.5, 1.0),
    )


def test_get_quote_retries_on_transient_failure():
    http = FlakyGetHttp({"price": 12345.0})
    sleeps = []
    assert _client(http, sleeps).get_quote("360750") == 12345.0
    assert http.gets == 2
    assert sleeps == [0.5]


def test_get_balance_retries_on_transient_failure():
    http = FlakyGetHttp({"cash": 5_000_000.0, "equity": 10_000_000.0})
    sleeps = []
    assert _client(http, sleeps).get_balance() == {
        "cash": 5_000_000.0, "equity": 10_000_000.0}
    assert http.gets == 2


def test_get_holdings_retries_on_transient_failure():
    http = FlakyGetHttp({"holdings": [
        {"code": "360750", "shares": 10, "avg_price": 15000.0}]})
    sleeps = []
    h = _client(http, sleeps).get_holdings()
    assert h["360750"]["shares"] == 10
    assert http.gets == 2


def test_get_order_status_retries_on_transient_failure():
    http = FlakyGetHttp({"status": "FILLED",
                         "filled_qty": 3, "fill_price": 15100.0})
    sleeps = []
    s = _client(http, sleeps).get_order_status("ORD-1")
    assert s["status"] == "FILLED"
    assert http.gets == 2


def test_place_order_does_NOT_retry_on_failure():
    http = FlakyPostHttp()
    sleeps = []
    with pytest.raises(Exception):
        _client(http, sleeps).place_order("360750", "BUY", 3)
    # Token call was made once; the non-token order POST was attempted
    # exactly once (no retry).
    assert http.other_posts == 1
    assert sleeps == []  # no delays consumed
