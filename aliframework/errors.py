from __future__ import annotations

"""Shared error types for the aliframework package.

Having a central error module makes it easier for callers to catch and reason
about framework-specific exceptions without depending on third-party driver
classes directly.
"""


class AliFrameworkError(Exception):
    """Base class for all framework-specific exceptions."""


class MissingDriverError(ImportError, AliFrameworkError):
    """Raised when an optional third-party driver/client is not installed.

    Examples include database drivers (psycopg2, pymysql, pyodbc, oracledb),
    GCP clients, hvac for Vault, Paramiko for SFTP, etc.
    """
    pass
