from __future__ import annotations

"""Secret management: HashiCorp Vault via GCP or direct token.

This module uses hvac, which you must install separately.
"""

from typing import Any

from .config import VaultConfig
from .errors import MissingDriverError


def create_vault_client(config: VaultConfig) -> Any:
    try:
        import hvac  # type: ignore
    except ImportError as exc:
        raise MissingDriverError("hvac is required for Vault integration") from exc

    client = hvac.Client(url=config.url, token=config.token)

    # If no direct token is provided but a JWT+role is, attempt GCP auth
    if not config.token and config.jwt:
        client.auth.gcp.login(role=config.role, jwt=config.jwt)

    return client

# ---------------------------------------------------------------------------
# Usage examples
#
# KV CRUD example with Vault (KVv2 engine):
# from aliframework.config import VaultConfig
# from aliframework.secrets import create_vault_client
#
# cfg = VaultConfig(
#     url="http://localhost:8200",
#     role="dev-role",
#     token="root",
# )
# client = create_vault_client(cfg)
#
# path = "integration/example"
# # CREATE/UPDATE
# client.secrets.kv.v2.create_or_update_secret(path=path, secret={"foo": "bar"})
# # READ
# read_resp = client.secrets.kv.v2.read_secret_version(path=path)
# print(read_resp["data"]["data"])
# # DELETE (soft-delete latest version)
# client.secrets.kv.v2.delete_latest_version(path=path)
#
# ---------------------------------------------------------------------------
# from aliframework.config import VaultConfig
# from aliframework.secrets import create_vault_client
#
# # Direct token auth
# cfg_token = VaultConfig(
#     url="https://vault.example.com",
#     role="ignored-when-using-token",
#     token="s.my-root-token",
# )
# client = create_vault_client(cfg_token)
# print(client.is_authenticated())
#
# # GCP auth via JWT
# cfg_gcp = VaultConfig(
#     url="https://vault.example.com",
#     role="my-gcp-role",
#     jwt="GCP-SIGNED-JWT-HERE",
# )
# client2 = create_vault_client(cfg_gcp)
