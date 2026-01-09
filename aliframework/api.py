from __future__ import annotations

"""HTTP API client wrapper with flexible authentication.

Supports:
- no auth
- Basic auth
- Bearer token
- API key in header or query
- OAuth2 client credentials flow
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests

from .config import ApiConfig, ApiAuthType


@dataclass
class ApiClient:
    config: ApiConfig

    def _get_session(self) -> requests.Session:
        sess = requests.Session()
        if self.config.default_headers:
            sess.headers.update(self.config.default_headers)
        return sess

    def _apply_auth(self, sess: requests.Session) -> None:
        c = self.config
        if c.auth_type == ApiAuthType.NONE:
            return
        if c.auth_type == ApiAuthType.BASIC:
            sess.auth = (c.username or "", c.password or "")
        elif c.auth_type == ApiAuthType.BEARER:
            sess.headers["Authorization"] = f"Bearer {c.token}"  # type: ignore[arg-type]
        elif c.auth_type == ApiAuthType.API_KEY_HEADER:
            if c.api_key_name and c.api_key_value:
                sess.headers[c.api_key_name] = c.api_key_value
        elif c.auth_type == ApiAuthType.API_KEY_QUERY:
            # handled per-request by adding params
            pass
        elif c.auth_type == ApiAuthType.OAUTH2_CLIENT_CREDENTIALS:
            self._obtain_oauth2_token(sess)
        else:
            raise ValueError(f"Unsupported auth type: {c.auth_type}")

    def _obtain_oauth2_token(self, sess: requests.Session) -> None:
        c = self.config
        if not (c.oauth2_token_url and c.oauth2_client_id and c.oauth2_client_secret):
            raise ValueError("OAuth2 client credentials require token_url, client_id, client_secret")

        data = {
            "grant_type": "client_credentials",
            "client_id": c.oauth2_client_id,
            "client_secret": c.oauth2_client_secret,
        }
        resp = sess.post(c.oauth2_token_url, data=data)
        resp.raise_for_status()
        token = resp.json().get("access_token")
        if not token:
            raise RuntimeError("OAuth2 token response missing access_token")
        sess.headers["Authorization"] = f"Bearer {token}"

    def request(self, method: str, path: str, *, params: Optional[Dict[str, Any]] = None, **kwargs: Any) -> requests.Response:
        url = self.config.base_url.rstrip("/") + "/" + path.lstrip("/")
        sess = self._get_session()
        self._apply_auth(sess)

        params = dict(params or {})
        # If API key in query, attach here
        if self.config.auth_type == ApiAuthType.API_KEY_QUERY and self.config.api_key_name and self.config.api_key_value:
            params[self.config.api_key_name] = self.config.api_key_value

        resp = sess.request(method.upper(), url, params=params, **kwargs)
        return resp

    def get(self, path: str, **kwargs: Any) -> requests.Response:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> requests.Response:
        return self.request("POST", path, **kwargs)

# ---------------------------------------------------------------------------
# Usage examples
#
# HTTP CRUD-style example (using httpbin.org for demo):
# from aliframework.api import ApiClient
# from aliframework.config import ApiConfig, ApiAuthType
#
# cfg = ApiConfig(base_url="https://httpbin.org", auth_type=ApiAuthType.NONE)
# client = ApiClient(cfg)
#
# # CREATE (POST)
# r = client.post("/post", json={"name": "foo"})
#
# # READ (GET)
# r = client.get("/get", params={"id": 1})
#
# # UPDATE (PUT)
# r = client.request("PUT", "/put", json={"id": 1, "name": "bar"})
#
# # DELETE (DELETE)
# r = client.request("DELETE", "/delete", params={"id": 1})
#
# ---------------------------------------------------------------------------
# from aliframework.api import ApiClient
# from aliframework.config import ApiConfig, ApiAuthType
#
# # No auth
# cfg_none = ApiConfig(
#     base_url="https://httpbin.org",
#     auth_type=ApiAuthType.NONE,
# )
# client_none = ApiClient(cfg_none)
# r = client_none.get("/get", params={"hello": "world"})
#
# # Basic auth
# cfg_basic = ApiConfig(
#     base_url="https://api.example.com",
#     auth_type=ApiAuthType.BASIC,
#     username="user",
#     password="pass",
# )
# client_basic = ApiClient(cfg_basic)
# r = client_basic.get("/secure")
#
# # Bearer token
# cfg_bearer = ApiConfig(
#     base_url="https://api.example.com",
#     auth_type=ApiAuthType.BEARER,
#     token="YOUR_TOKEN_HERE",
# )
# client_bearer = ApiClient(cfg_bearer)
# r = client_bearer.post("/data", json={"x": 1})
#
# # API key in header
# cfg_key_header = ApiConfig(
#     base_url="https://api.example.com",
#     auth_type=ApiAuthType.API_KEY_HEADER,
#     api_key_name="X-API-Key",
#     api_key_value="SECRET",
# )
# client_key_header = ApiClient(cfg_key_header)
# r = client_key_header.get("/data")
#
# # API key in query
# cfg_key_query = ApiConfig(
#     base_url="https://api.example.com",
#     auth_type=ApiAuthType.API_KEY_QUERY,
#     api_key_name="api_key",
#     api_key_value="SECRET",
# )
# client_key_query = ApiClient(cfg_key_query)
# r = client_key_query.get("/data", params={"foo": "bar"})
#
# # OAuth2 client credentials
# cfg_oauth = ApiConfig(
#     base_url="https://api.example.com",
#     auth_type=ApiAuthType.OAUTH2_CLIENT_CREDENTIALS,
#     oauth2_token_url="https://auth.example.com/oauth/token",
#     oauth2_client_id="client-id",
#     oauth2_client_secret="client-secret",
# )
# client_oauth = ApiClient(cfg_oauth)
# r = client_oauth.get("/protected")
