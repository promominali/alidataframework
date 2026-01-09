from __future__ import annotations

from types import ModuleType
import builtins
import sys

import pytest

from aliframework.config import DbConfig, DatabaseType
from aliframework.db import MissingDriverError, create_db_connection


class DummyPsycopg2(ModuleType):
    def __init__(self):
        super().__init__("psycopg2")
        self.connect_calls = []

    def connect(self, **kwargs):  # type: ignore[override]
        self.connect_calls.append(kwargs)
        return "pg-conn"


class DummyPyMySQL(ModuleType):
    def __init__(self):
        super().__init__("pymysql")
        self.connect_calls = []

    def connect(self, **kwargs):  # type: ignore[override]
        self.connect_calls.append(kwargs)
        return "mysql-conn"


class DummyPyODBC(ModuleType):
    def __init__(self):
        super().__init__("pyodbc")
        self.connect_calls = []

    def connect(self, conn_str):  # type: ignore[override]
        self.connect_calls.append(conn_str)
        return "mssql-conn"


class DummyOracleDB(ModuleType):
    def __init__(self):
        super().__init__("oracledb")
        self.makedsn_calls = []
        self.connect_calls = []

    def makedsn(self, host, port, service_name):  # type: ignore[override]
        dsn = f"dsn://{host}:{port}/{service_name}"
        self.makedsn_calls.append(dsn)
        return dsn

    def connect(self, **kwargs):  # type: ignore[override]
        self.connect_calls.append(kwargs)
        return "oracle-conn"


@pytest.fixture(autouse=True)
def _cleanup_modules():
    # Ensure our dummy modules do not leak between tests
    original_modules = sys.modules.copy()
    yield
    # Restore modules dictionary (best-effort, keep it simple)
    for name in list(sys.modules.keys()):
        if name not in original_modules:
            sys.modules.pop(name, None)


def test_postgres_missing_driver_raises(monkeypatch):
    cfg = DbConfig(
        db_type=DatabaseType.POSTGRES,
        host="h",
        port=5432,
        user="u",
        password="p",
        database="d",
    )

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "psycopg2":
            raise ImportError("psycopg2 not available")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(MissingDriverError):
        create_db_connection(cfg)


def test_postgres_success_uses_psycopg2_connect():
    dummy = DummyPsycopg2()
    sys.modules["psycopg2"] = dummy

    cfg = DbConfig(
        db_type=DatabaseType.POSTGRES,
        host="localhost",
        port=5432,
        user="user",
        password="pass",
        database="db",
        extra={"connect_timeout": 10},
    )

    conn = create_db_connection(cfg)
    assert conn == "pg-conn"
    assert dummy.connect_calls[0]["host"] == "localhost"
    assert dummy.connect_calls[0]["dbname"] == "db"
    assert dummy.connect_calls[0]["connect_timeout"] == 10


def test_mysql_missing_driver_raises(monkeypatch):
    cfg = DbConfig(
        db_type=DatabaseType.MYSQL,
        host="h",
        port=3306,
        user="u",
        password="p",
        database="d",
    )

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "pymysql":
            raise ImportError("pymysql not available")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(MissingDriverError):
        create_db_connection(cfg)


def test_mysql_success_uses_pymysql_connect():
    dummy = DummyPyMySQL()
    sys.modules["pymysql"] = dummy

    cfg = DbConfig(
        db_type=DatabaseType.MYSQL,
        host="localhost",
        port=3306,
        user="user",
        password="pass",
        database="db",
    )

    conn = create_db_connection(cfg)
    assert conn == "mysql-conn"
    assert dummy.connect_calls[0]["db"] == "db"


def test_mssql_missing_driver_raises(monkeypatch):
    cfg = DbConfig(
        db_type=DatabaseType.MSSQL,
        host="h",
        port=1433,
        user="u",
        password="p",
        database="d",
    )

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "pyodbc":
            raise ImportError("pyodbc not available")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(MissingDriverError):
        create_db_connection(cfg)


def test_mssql_with_dsn_uses_provided_dsn():
    dummy = DummyPyODBC()
    sys.modules["pyodbc"] = dummy

    cfg = DbConfig(
        db_type=DatabaseType.MSSQL,
        host="h",
        port=1433,
        user="u",
        password="p",
        database="d",
        extra={"dsn": "DSN=mydsn"},
    )

    conn = create_db_connection(cfg)
    assert conn == "mssql-conn"
    assert dummy.connect_calls[0] == "DSN=mydsn"


def test_mssql_without_dsn_builds_connection_string_with_default_driver():
    dummy = DummyPyODBC()
    sys.modules["pyodbc"] = dummy

    cfg = DbConfig(
        db_type=DatabaseType.MSSQL,
        host="server",
        port=1444,
        user="user",
        password="pass",
        database="db",
        extra={},
    )

    conn = create_db_connection(cfg)
    assert conn == "mssql-conn"
    conn_str = dummy.connect_calls[0]
    assert "SERVER=server,1444" in conn_str
    assert "DATABASE=db" in conn_str
    assert "UID=user" in conn_str


def test_oracle_missing_driver_raises(monkeypatch):
    cfg = DbConfig(
        db_type=DatabaseType.ORACLE,
        host="h",
        port=1521,
        user="u",
        password="p",
        database="service",
    )

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "oracledb":
            raise ImportError("oracledb not available")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(MissingDriverError):
        create_db_connection(cfg)


def test_oracle_success_uses_oracledb_connect_and_makedsn():
    dummy = DummyOracleDB()
    sys.modules["oracledb"] = dummy

    cfg = DbConfig(
        db_type=DatabaseType.ORACLE,
        host="host",
        port=1521,
        user="user",
        password="pass",
        database="svc",
        extra={"encoding": "UTF-8"},
    )

    conn = create_db_connection(cfg)
    assert conn == "oracle-conn"
    assert dummy.makedsn_calls[0] == "dsn://host:1521/svc"
    assert dummy.connect_calls[0]["user"] == "user"
    assert dummy.connect_calls[0]["encoding"] == "UTF-8"


def test_unsupported_db_type_raises_value_error():
    # type: ignore[arg-type]
    cfg = DbConfig(
        db_type="unknown",  # force bad value at runtime
        host="h",
        port=0,
        user="u",
        password="p",
        database="d",
    )

    with pytest.raises(ValueError):
        create_db_connection(cfg)
