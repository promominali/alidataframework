from __future__ import annotations

"""Integration test for SFTP connection using Paramiko via our framework.

Requires docker-compose sftp service:
  sftp: localhost:2222, user/secret
"""

import pytest

from aliframework.config import SftpConfig, SftpAuthType
from aliframework.sftp import create_sftp_client
from .conftest import wait_for_port


@pytest.mark.integration
def test_sftp_password_auth_and_listdir(tmp_path):
    pytest.importorskip("paramiko")
    wait_for_port("localhost", 2222, timeout=60)

    cfg = SftpConfig(
        host="localhost",
        port=2222,
        username="user",
        password="secret",
        auth_type=SftpAuthType.PASSWORD,
    )
    sftp = create_sftp_client(cfg)

    # Ensure we can list the upload directory created by the container
    entries = sftp.listdir("upload")
    # Atmoz image creates the directory but may or may not populate files; just ensure we got a list
    assert isinstance(entries, list)

    # Optionally upload a small file
    test_file = tmp_path / "hello.txt"
    test_file.write_text("hello")
    sftp.put(str(test_file), "upload/hello.txt")

    sftp.close()
