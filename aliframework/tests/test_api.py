from aliframework.api import ApiClient
from aliframework.config import ApiConfig, ApiAuthType


class DummyResponse:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json = json_data or {}

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("error")


def test_bearer_auth(monkeypatch):
    calls = {}

    def fake_request(self, method, url, params=None, **kwargs):  # type: ignore[override]
        calls["method"] = method
        calls["url"] = url
        calls["auth_header"] = self.headers.get("Authorization")
        return DummyResponse()

    import requests

    monkeypatch.setattr(requests.Session, "request", fake_request)

    cfg = ApiConfig(
        base_url="https://api.example.com",
        auth_type=ApiAuthType.BEARER,
        token="XYZ",
    )
    client = ApiClient(cfg)
    resp = client.get("/test")
    assert isinstance(resp, DummyResponse)
    assert calls["auth_header"] == "Bearer XYZ"
