from __future__ import annotations

import builtins
from typing import Any

import pytest

from aliframework.api import ApiClient
from aliframework.config import ApiAuthType, ApiConfig


class DummyResponse:
    def __init__(self, url: str, method: str, params, kwargs: dict[str, Any]):
        self.url = url
        self.method = method
        self.params = params
        self.kwargs = kwargs

    def raise_for_status(self) -> None:  # for OAuth2 flow tests
        return None

    def json(self) -> dict[str, Any]:
        return {"access_token": "ACCESS"}


class DummySession:
    def __init__(self):
        self.headers: dict[str, str] = {}
        self.auth: Any = None
        self.post_calls: list[tuple[str, dict[str, Any]]] = []
        self.request_calls: list[tuple[str, str, dict[str, Any], dict[str, Any]]] = []

    def post(self, url: str, data: dict[str, Any]):
        self.post_calls.append((url, data))
        return DummyResponse(url, "POST", None, {"data": data})

    def request(self, method: str, url: str, params=None, **kwargs: Any):
        self.request_calls.append((method, url, params, kwargs))
        return DummyResponse(url, method, params, kwargs)


@pytest.fixture
def dummy_session(monkeypatch):
    import requests

    sess = DummySession()

    def make_session():
        return sess

    monkeypatch.setattr(requests, "Session", make_session)
    return sess


def test_get_session_applies_default_headers(dummy_session):
    cfg = ApiConfig(base_url="https://example.com", default_headers={"X-Test": "1"})
    client = ApiClient(cfg)

    # Trigger _get_session via request
    client.get("/path")
    assert dummy_session.headers["X-Test"] == "1"


@pytest.mark.parametrize(
    "auth_type, expected_auth, expected_header",
    [
        (ApiAuthType.NONE, None, None),
        (ApiAuthType.BASIC, ("user", "pass"), None),
        (ApiAuthType.BEARER, None, "Bearer TOKEN"),
    ],
)
def test_apply_auth_basic_bearer_and_none(auth_type, expected_auth, expected_header, dummy_session):
    cfg = ApiConfig(
        base_url="https://example.com",
        auth_type=auth_type,
        username="user",
        password="pass",
        token="TOKEN",
    )
    client = ApiClient(cfg)

    client._apply_auth(dummy_session)

    if expected_auth is not None:
        assert dummy_session.auth == expected_auth
    else:
        assert getattr(dummy_session, "auth", None) in (None, expected_auth)

    if expected_header is not None:
        assert dummy_session.headers["Authorization"] == expected_header
    else:
        assert "Authorization" not in dummy_session.headers


def test_apply_auth_api_key_header_sets_header(dummy_session):
    cfg = ApiConfig(
        base_url="https://example.com",
        auth_type=ApiAuthType.API_KEY_HEADER,
        api_key_name="X-API-Key",
        api_key_value="SECRET",
    )
    client = ApiClient(cfg)

    client._apply_auth(dummy_session)
    assert dummy_session.headers["X-API-Key"] == "SECRET"


def test_apply_auth_api_key_header_ignored_if_missing_name_or_value(dummy_session):
    cfg = ApiConfig(
        base_url="https://example.com",
        auth_type=ApiAuthType.API_KEY_HEADER,
        api_key_name=None,
        api_key_value=None,
    )
    client = ApiClient(cfg)

    client._apply_auth(dummy_session)
    assert dummy_session.headers == {}


def test_apply_auth_unsupported_type_raises(dummy_session):
    cfg = ApiConfig(base_url="https://example.com")
    # type: ignore[assignment]
    cfg.auth_type = "unsupported"  # force runtime bad value
    client = ApiClient(cfg)

    with pytest.raises(ValueError):
        client._apply_auth(dummy_session)


def test_obtain_oauth2_token_missing_config_raises(dummy_session):
    cfg = ApiConfig(base_url="https://example.com", auth_type=ApiAuthType.OAUTH2_CLIENT_CREDENTIALS)
    client = ApiClient(cfg)

    with pytest.raises(ValueError):
        client._obtain_oauth2_token(dummy_session)


def test_obtain_oauth2_token_missing_access_token_raises(monkeypatch, dummy_session):
    cfg = ApiConfig(
        base_url="https://example.com",
        auth_type=ApiAuthType.OAUTH2_CLIENT_CREDENTIALS,
        oauth2_token_url="https://auth/token",
        oauth2_client_id="id",
        oauth2_client_secret="secret",
    )
    client = ApiClient(cfg)

    class BadResponse(DummyResponse):
        def json(self) -> dict[str, Any]:
            return {}

    def bad_post(url: str, data: dict[str, Any]):
        return BadResponse(url, "POST", None, {"data": data})

    dummy_session.post = bad_post  # type: ignore[assignment]

    with pytest.raises(RuntimeError):
        client._obtain_oauth2_token(dummy_session)


def test_obtain_oauth2_token_success_sets_header(dummy_session):
    cfg = ApiConfig(
        base_url="https://example.com",
        auth_type=ApiAuthType.OAUTH2_CLIENT_CREDENTIALS,
        oauth2_token_url="https://auth/token",
        oauth2_client_id="id",
        oauth2_client_secret="secret",
    )
    client = ApiClient(cfg)

    client._obtain_oauth2_token(dummy_session)

    assert dummy_session.headers["Authorization"] == "Bearer ACCESS"
    assert dummy_session.post_calls[0][0] == "https://auth/token"
    assert dummy_session.post_calls[0][1]["grant_type"] == "client_credentials"


def test_request_builds_url_and_passes_params(dummy_session):
    cfg = ApiConfig(base_url="https://example.com/api", auth_type=ApiAuthType.NONE)
    client = ApiClient(cfg)

    resp = client.request("get", "v1/resource", params={"x": 1})

    assert resp.url == "https://example.com/api/v1/resource"
    assert resp.method == "GET"
    assert resp.params == {"x": 1}


def test_request_adds_api_key_query_param(dummy_session):
    cfg = ApiConfig(
        base_url="https://example.com/api/",
        auth_type=ApiAuthType.API_KEY_QUERY,
        api_key_name="api_key",
        api_key_value="SECRET",
    )
    client = ApiClient(cfg)

    resp = client.request("GET", "/items", params={"foo": "bar"})

    assert resp.url == "https://example.com/api/items"
    # API key should be merged into params
    assert resp.params["foo"] == "bar"
    assert resp.params["api_key"] == "SECRET"


def test_get_and_post_helpers_use_request(monkeypatch, dummy_session):
    cfg = ApiConfig(base_url="https://example.com")
    client = ApiClient(cfg)

    calls: list[tuple[str, str]] = []

    def fake_request(method: str, path: str, **kwargs: Any):
        calls.append((method, path))
        return DummyResponse(path, method, None, kwargs)

    monkeypatch.setattr(client, "request", fake_request)

    client.get("/a")
    client.post("/b")

    assert calls == [("GET", "/a"), ("POST", "/b")]


def test_apply_auth_oauth2_calls_obtain_token(monkeypatch, dummy_session):
    cfg = ApiConfig(base_url="https://example.com", auth_type=ApiAuthType.OAUTH2_CLIENT_CREDENTIALS)
    client = ApiClient(cfg)

    called: dict[str, Any] = {}

    def fake_obtain(sess):
        called["sess"] = sess

    monkeypatch.setattr(client, "_obtain_oauth2_token", fake_obtain)

    client._apply_auth(dummy_session)
    assert called["sess"] is dummy_session
