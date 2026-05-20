from broker.kiwoom import KiwoomClient


class FakeResp:
    def __init__(self, json_data, status=200):
        self._json = json_data
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")

    def json(self):
        return self._json


class FakeHttp:
    def __init__(self):
        self.calls = []
        self.responses = []

    def post(self, url, json=None, headers=None, timeout=None):
        self.calls.append(("POST", url, json, headers))
        return self.responses.pop(0)

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append(("GET", url, params, headers))
        return self.responses.pop(0)


def _client(http, clock_value=1000.0):
    return KiwoomClient(base_url="https://mock.kiwoom.com",
                        app_key="K", app_secret="S", account_no="1",
                        http=http, clock=lambda: clock_value)


def test_get_token_calls_endpoint_and_caches():
    http = FakeHttp()
    http.responses = [FakeResp({"token": "T1", "expires_in": 3600})]
    c = _client(http)
    assert c.get_token() == "T1"
    assert c.get_token() == "T1"  # 두 번째는 캐시
    assert len(http.calls) == 1  # 한 번만 호출


def test_token_refreshes_after_expiry():
    http = FakeHttp()
    http.responses = [FakeResp({"token": "T1", "expires_in": 100}),
                      FakeResp({"token": "T2", "expires_in": 100})]
    calls = []

    def clock():
        return calls and 9999.0 or 1000.0

    c = KiwoomClient(base_url="https://x", app_key="K", app_secret="S",
                     account_no="1", http=http,
                     clock=lambda: 1000.0 if not calls else 9999.0)
    # 첫 호출
    assert c.get_token() == "T1"
    calls.append(1)  # 시계 전진
    # 만료되었으므로 재발급
    assert c.get_token() == "T2"
    assert len(http.calls) == 2
