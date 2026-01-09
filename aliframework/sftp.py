from __future__ import annotations

"""SFTP client helpers using Paramiko.

Supports password, private-key, or both.
"""

from typing import Any

from .config import SftpConfig, SftpAuthType
from .errors import MissingDriverError


def create_sftp_client(config: SftpConfig) -> Any:
    """Create and return a Paramiko SFTPClient.

    Caller is responsible for closing the underlying Transport/SFTPClient.
    """
    try:
        import paramiko  # type: ignore
    except ImportError as exc:
        raise MissingDriverError("paramiko is required for SFTP") from exc

    transport = paramiko.Transport((config.host, config.port))

    if config.auth_type == SftpAuthType.PASSWORD:
        transport.connect(username=config.username, password=config.password)
    elif config.auth_type in (SftpAuthType.PRIVATE_KEY, SftpAuthType.PASSWORD_AND_KEY):
        key = paramiko.RSAKey.from_private_key_file(
            config.private_key_path, password=config.private_key_passphrase
        )
        if config.auth_type == SftpAuthType.PRIVATE_KEY:
            transport.connect(username=config.username, pkey=key)
        else:
            transport.connect(username=config.username, password=config.password, pkey=key)
    else:
        raise ValueError(f"Unsupported SFTP auth type: {config.auth_type}")

    return paramiko.SFTPClient.from_transport(transport)

# ---------------------------------------------------------------------------
# Usage examples
#
# SFTP CRUD-like operations on files:
# from aliframework.config import SftpConfig, SftpAuthType
# from aliframework.sftp import create_sftp_client
#
# cfg = SftpConfig(
#     host="localhost",
#     port=2222,
#     username="user",
#     password="secret",
#     auth_type=SftpAuthType.PASSWORD,
# )
# sftp = create_sftp_client(cfg)
#
# # CREATE/UPLOAD
# sftp.put("local.txt", "remote.txt")
# # READ/LIST
# print(sftp.listdir("."))
# # DOWNLOAD
# sftp.get("remote.txt", "downloaded.txt")
# # DELETE
# sftp.remove("remote.txt")
# sftp.close()
#
# ---------------------------------------------------------------------------
# from aliframework.config import SftpConfig, SftpAuthType
# from aliframework.sftp import create_sftp_client
#
# # Password auth
# cfg_pwd = SftpConfig(
#     host="sftp.example.com",
#     port=22,
#     username="user",
#     password="secret",
#     auth_type=SftpAuthType.PASSWORD,
# )
# sftp = create_sftp_client(cfg_pwd)
# print(sftp.listdir("."))
# sftp.close()
#
# # Key-based auth
# cfg_key = SftpConfig(
#     host="sftp.example.com",
#     username="user",
#     private_key_path="/path/to/id_rsa",
#     private_key_passphrase=None,
#     auth_type=SftpAuthType.PRIVATE_KEY,
# )
# sftp2 = create_sftp_client(cfg_key)
# sftp2.close()
