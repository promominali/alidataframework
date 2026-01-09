"""Unified connection framework for databases, APIs, SFTP, GCP, and secrets.

This package exposes small, focused helpers instead of a heavy framework.
You can import only what you need, e.g.:

    from aliframework.db import create_db_connection, DatabaseType, DbConfig
    from aliframework.api import ApiClient, ApiAuthType, ApiConfig

Or, for convenience, import shared config and enum types directly from the
package root.
"""

from . import db, nosql, api, sftp, gcp, secrets  # noqa: F401
from .config import (  # re-export for convenience
    DbConfig,
    DatabaseType,
    ApiConfig,
    ApiAuthType,
    SftpConfig,
    SftpAuthType,
    GcpConfig,
    VaultConfig,
)
from .errors import AliFrameworkError, MissingDriverError

__all__ = [
    # Submodules
    "db",
    "nosql",
    "api",
    "sftp",
    "gcp",
    "secrets",
    # Config / enums
    "DbConfig",
    "DatabaseType",
    "ApiConfig",
    "ApiAuthType",
    "SftpConfig",
    "SftpAuthType",
    "GcpConfig",
    "VaultConfig",
    # Errors
    "AliFrameworkError",
    "MissingDriverError",
]
