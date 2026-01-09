from __future__ import annotations

from types import ModuleType
import builtins
import sys

import pytest

from aliframework.nosql import MissingDriverError, create_mongo_client


class DummyMongoClient:
    def __init__(self, uri: str, **kwargs):
        self.uri = uri
        self.kwargs = kwargs


class DummyPymongo(ModuleType):
    def __init__(self):
        super().__init__("pymongo")
        self.instances: list[DummyMongoClient] = []

    def MongoClient(self, uri: str, **kwargs):  # type: ignore[override]
        client = DummyMongoClient(uri, **kwargs)
        self.instances.append(client)
        return client


@pytest.fixture(autouse=True)
def _cleanup_modules():
    original_modules = sys.modules.copy()
    yield
    for name in list(sys.modules.keys()):
        if name not in original_modules:
            sys.modules.pop(name, None)


def test_create_mongo_client_missing_driver_raises(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "pymongo":
            raise ImportError("pymongo not available")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(MissingDriverError):
        create_mongo_client("mongodb://localhost:27017")


def test_create_mongo_client_without_credentials_uses_plain_uri():
    dummy = DummyPymongo()
    sys.modules["pymongo"] = dummy

    client = create_mongo_client("mongodb://localhost:27017", connectTimeoutMS=1000)
    assert isinstance(client, DummyMongoClient)
    assert dummy.instances[0].uri == "mongodb://localhost:27017"
    assert dummy.instances[0].kwargs["connectTimeoutMS"] == 1000


def test_create_mongo_client_with_username_and_password():
    dummy = DummyPymongo()
    sys.modules["pymongo"] = dummy

    client = create_mongo_client(
        "mongodb://localhost:27017",
        username="user",
        password="pass",
        authSource="admin",
    )

    assert isinstance(client, DummyMongoClient)
    assert dummy.instances[0].kwargs["username"] == "user"
    assert dummy.instances[0].kwargs["password"] == "pass"
    assert dummy.instances[0].kwargs["authSource"] == "admin"
