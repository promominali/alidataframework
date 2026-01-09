from __future__ import annotations

from types import ModuleType, SimpleNamespace
import builtins
import sys

import pytest

from aliframework.config import VaultConfig
from aliframework.secrets import MissingDriverError, create_vault_client


class DummyHvacClient:
    def __init__(self, url: str, token: str | None):
        self.url = url
        self.token = token
        self.auth = SimpleNamespace(gcp=SimpleNamespace(login=self._login))
        self.gcp_login_calls: list[tuple[str, str]] = []

    def _login(self, role: str, jwt: str):
        self.gcp_login_calls.append((role, jwt))


class DummyHvac(ModuleType):
    def __init__(self):
        super().__init__("hvac")
        self.clients: list[DummyHvacClient] = []

    def Client(self, url: str, token: str | None):  # type: ignore[override]
        client = DummyHvacClient(url, token)
        self.clients.append(client)
        return client


@pytest.fixture(autouse=True)
def _cleanup_modules():
    original_modules = sys.modules.copy()
    yield
    for name in list(sys.modules.keys()):
        if name not in original_modules:
            sys.modules.pop(name, None)


def test_create_vault_client_missing_driver_raises(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "hvac":
            raise ImportError("hvac not available")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    cfg = VaultConfig(url="http://vault", role="r", token="t")
    with pytest.raises(MissingDriverError):
        create_vault_client(cfg)


def test_create_vault_client_with_direct_token_does_not_call_gcp_login():
    dummy = DummyHvac()
    sys.modules["hvac"] = dummy

    cfg = VaultConfig(url="http://vault", role="ignored", token="token-value")
    client = create_vault_client(cfg)

    assert isinstance(client, DummyHvacClient)
    assert client.token == "token-value"
    assert client.gcp_login_calls == []


def test_create_vault_client_with_jwt_uses_gcp_login():
    dummy = DummyHvac()
    sys.modules["hvac"] = dummy

    cfg = VaultConfig(url="http://vault", role="my-role", jwt="jwt-token", token=None)
    client = create_vault_client(cfg)

    assert isinstance(client, DummyHvacClient)
    assert client.token is None
    assert client.gcp_login_calls == [("my-role", "jwt-token")]
