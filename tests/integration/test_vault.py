from __future__ import annotations

"""Integration test for Vault using hvac via our framework.

Requires docker-compose vault service (dev mode):
  vault: http://localhost:8200, token=root
"""

import pytest

from aliframework.config import VaultConfig
from aliframework.secrets import create_vault_client
from .conftest import wait_for_port


@pytest.mark.integration
def test_vault_auth_and_kv_write_read():
    pytest.importorskip("hvac")
    wait_for_port("localhost", 8200, timeout=60)

    cfg = VaultConfig(
        url="http://localhost:8200",
        role="dev-role",
        token="root",
    )
    client = create_vault_client(cfg)
    assert client.is_authenticated()

    # Enable KVv2 at path "secret" if not already enabled
    mounts = client.sys.list_mounted_secrets_engines()["data"].keys()
    if "secret/" not in mounts:
        client.sys.enable_secrets_engine("kv", path="secret", options={"version": "2"})

    # Write and read back a secret
    path = "integration/test"
    client.secrets.kv.v2.create_or_update_secret(path=path, secret={"foo": "bar"})
    read_resp = client.secrets.kv.v2.read_secret_version(path=path, raise_on_deleted_version=True)
    assert read_resp["data"]["data"]["foo"] == "bar"
