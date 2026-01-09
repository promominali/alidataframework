from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any


class DatabaseType(str, Enum):
    POSTGRES = "postgres"
    MYSQL = "mysql"
    MSSQL = "mssql"
    ORACLE = "oracle"


@dataclass
class DbConfig:
    db_type: DatabaseType
    host: str
    port: int
    user: str
    password: str
    database: str
    extra: Dict[str, Any] | None = None


class ApiAuthType(str, Enum):
    NONE = "none"
    BASIC = "basic"
    BEARER = "bearer"
    API_KEY_HEADER = "api_key_header"
    API_KEY_QUERY = "api_key_query"
    OAUTH2_CLIENT_CREDENTIALS = "oauth2_client_credentials"


@dataclass
class ApiConfig:
    base_url: str
    auth_type: ApiAuthType = ApiAuthType.NONE
    username: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None
    api_key_name: Optional[str] = None
    api_key_value: Optional[str] = None
    oauth2_token_url: Optional[str] = None
    oauth2_client_id: Optional[str] = None
    oauth2_client_secret: Optional[str] = None
    default_headers: Optional[Dict[str, str]] = None


class SftpAuthType(str, Enum):
    PASSWORD = "password"
    PRIVATE_KEY = "private_key"
    PASSWORD_AND_KEY = "password_and_key"


@dataclass
class SftpConfig:
    host: str
    port: int = 22
    username: str = ""
    password: Optional[str] = None
    private_key_path: Optional[str] = None
    private_key_passphrase: Optional[str] = None
    auth_type: SftpAuthType = SftpAuthType.PASSWORD


@dataclass
class GcpConfig:
    project_id: str
    credentials_path: Optional[str] = None  # path to service account JSON, if not using ADC


@dataclass
class VaultConfig:
    url: str
    role: str
    jwt: Optional[str] = None  # e.g. GCP-signed JWT
    token: Optional[str] = None  # direct Vault token (alternative auth)
