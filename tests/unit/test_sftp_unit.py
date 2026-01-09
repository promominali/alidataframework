from __future__ import annotations

from types import ModuleType
import builtins
import sys

import pytest

from aliframework.config import SftpAuthType, SftpConfig
from aliframework.sftp import MissingDriverError, create_sftp_client


class DummyTransport:
    def __init__(self, addr):
        self.addr = addr
        self.connect_calls = []

    def connect(self, **kwargs):
        self.connect_calls.append(kwargs)


class DummyRSAKey:
    def __init__(self, path: str, password: str | None):
        self.path = path
        self.password = password

    @classmethod
    def from_private_key_file(cls, path: str, password: str | None = None):
        return cls(path, password)


class DummySFTPClient:
    def __init__(self, transport):
        self.transport = transport

    @classmethod
    def from_transport(cls, transport):
        return cls(transport)


class DummyParamiko(ModuleType):
    def __init__(self):
        super().__init__("paramiko")
        self.last_transport: DummyTransport | None = None

        self.Transport = self._Transport  # type: ignore[assignment]
        self.RSAKey = DummyRSAKey
        self.SFTPClient = DummySFTPClient

    def _Transport(self, addr):
        t = DummyTransport(addr)
        self.last_transport = t
        return t


@pytest.fixture(autouse=True)
def _cleanup_modules():
    original_modules = sys.modules.copy()
    yield
    for name in list(sys.modules.keys()):
        if name not in original_modules:
            sys.modules.pop(name, None)


def test_create_sftp_client_missing_driver_raises(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "paramiko":
            raise ImportError("paramiko not available")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    cfg = SftpConfig(host="h", port=22, username="u", password="p", auth_type=SftpAuthType.PASSWORD)
    with pytest.raises(MissingDriverError):
        create_sftp_client(cfg)


def test_private_key_auth_uses_rsa_key_and_pkey_only():
    dummy = DummyParamiko()
    sys.modules["paramiko"] = dummy

    cfg = SftpConfig(
        host="example.com",
        port=2022,
        username="user",
        private_key_path="/path/to/key",
        private_key_passphrase="secret",
        auth_type=SftpAuthType.PRIVATE_KEY,
    )

    client = create_sftp_client(cfg)
    assert isinstance(client, DummySFTPClient)
    transport = dummy.last_transport
    assert transport is not None
    # Only pkey should be provided, not password
    connect_kwargs = transport.connect_calls[0]
    assert connect_kwargs["username"] == "user"
    assert "password" not in connect_kwargs
    assert "pkey" in connect_kwargs


def test_password_and_key_auth_uses_both_password_and_pkey():
    dummy = DummyParamiko()
    sys.modules["paramiko"] = dummy

    cfg = SftpConfig(
        host="example.com",
        port=2022,
        username="user",
        password="pwd",
        private_key_path="/path/to/key",
        private_key_passphrase=None,
        auth_type=SftpAuthType.PASSWORD_AND_KEY,
    )

    client = create_sftp_client(cfg)
    assert isinstance(client, DummySFTPClient)
    transport = dummy.last_transport
    assert transport is not None
    connect_kwargs = transport.connect_calls[0]
    assert connect_kwargs["username"] == "user"
    assert connect_kwargs["password"] == "pwd"
    assert "pkey" in connect_kwargs


def test_unsupported_auth_type_raises_value_error():
    dummy = DummyParamiko()
    sys.modules["paramiko"] = dummy

    # type: ignore[arg-type]
    cfg = SftpConfig(host="h", username="u", auth_type="unsupported")

    with pytest.raises(ValueError):
        create_sftp_client(cfg)
