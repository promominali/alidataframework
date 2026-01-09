"""Shared helpers for integration tests.

These tests assume docker-compose services are running:
  docker compose up -d

They use real network connections to Postgres, MySQL, Mongo, SFTP, and Vault.
"""

from __future__ import annotations

import socket
import time
from typing import Optional


def wait_for_port(host: str, port: int, timeout: float = 30.0) -> None:
  """Wait until a TCP port is accepting connections or timeout.

  Raises TimeoutError if the port is not open in time.
  """
  deadline = time.time() + timeout
  while time.time() < deadline:
      try:
          with socket.create_connection((host, port), timeout=2):
              return
      except OSError:
          time.sleep(1)
  raise TimeoutError(f"Timed out waiting for {host}:{port}")
