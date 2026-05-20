from broker.kiwoom import KiwoomClient


class FakeResp:
    def __init__(self, j, s=200):
        self._j = j; self.status_code = s
    def raise_for_status(self):
        if self.status_code >= 400: raise Exception(self.status_code)
    def json(self): return self._j


class FakeHttp:
    def __init__(self): self.calls = []; self.responses = []
    def post(self, url, json=None, headers=None, timeout=None):
        self.calls.append(("POST", url, json, headers))
        return self.responses.pop(0)
    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append(("GET", url, params, headers))
        return self.responses.pop(0)


def _client(http):
    return KiwoomClient("https://mock.kiwoom.com", "K", "S", "1234",
                        http=http, clock=lambda: 0.0)


def _token_resp():
    return FakeResp({"token": "T", "expires_in": 3600})


def test_get_quote_returns_price():
    http = FakeHttp()
    http.responses = [_token_resp(), FakeResp({"price": 12345.0})]
    assert _client(http).get_quote("360750") == 12345.0
    # GET호출 시 Authorization 헤더 부착
    last = http.calls[-1]
    assert last[0] == "GET"
    assert last[3]["Authorization"] == "Bearer T"


def test_get_balance_returns_cash_and_equity():
    http = FakeHttp()
    http.responses = [_token_resp(),
                      FakeResp({"cash": 5_000_000.0, "equity": 10_000_000.0})]
    b = _client(http).get_balance()
    assert b == {"cash": 5_000_000.0, "equity": 10_000_000.0}


def test_get_holdings_returns_code_map():
    http = FakeHttp()
    http.responses = [_token_resp(), FakeResp({"holdings": [
        {"code": "360750", "shares": 10, "avg_price": 15000.0},
        {"code": "381170", "shares": 5, "avg_price": 22000.0},
    ]})]
    h = _client(http).get_holdings()
    assert h == {
        "360750": {"shares": 10, "avg_price": 15000.0},
        "381170": {"shares": 5, "avg_price": 22000.0},
    }


def test_place_order_returns_order_id_and_sends_payload():
    http = FakeHttp()
    http.responses = [_token_resp(), FakeResp({"order_id": "ORD-1"})]
    oid = _client(http).place_order("360750", "BUY", 3)
    assert oid == "ORD-1"
    last = http.calls[-1]
    assert last[0] == "POST"
    payload = last[2]
    assert payload["code"] == "360750"
    assert payload["side"] == "BUY"
    assert payload["qty"] == 3
    assert payload["order_type"] == "MARKET"
    assert payload["account_no"] == "1234"


def test_get_order_status_parses_fields():
    http = FakeHttp()
    http.responses = [_token_resp(),
                      FakeResp({"status": "FILLED",
                                "filled_qty": 3, "fill_price": 15100.0})]
    s = _client(http).get_order_status("ORD-1")
    assert s == {"order_id": "ORD-1", "status": "FILLED",
                 "filled_qty": 3, "fill_price": 15100.0}
