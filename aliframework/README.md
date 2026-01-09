# aliframework package documentation

This document focuses on how to use the `aliframework` Python package in your code.

## Overview

Main modules:

- `aliframework.config` – shared config dataclasses and enums
- `aliframework.db` – relational DB connections (Postgres, MySQL, MSSQL, Oracle)
- `aliframework.nosql` – MongoDB client helper
- `aliframework.api` – HTTP API client with multiple auth modes
- `aliframework.sftp` – SFTP client creation (password/key)
- `aliframework.secrets` – HashiCorp Vault client (token or GCP auth)
- `aliframework.gcp` – GCS, BigQuery, and pipeline helpers

## Installation

```bash
pip install -e .[all,dev]
```

Or, once published:

```bash
pip install "aliframework[all]"
```

## Configuration module (`config`)

Key types:

- `DatabaseType`, `DbConfig`
- `ApiAuthType`, `ApiConfig`
- `SftpAuthType`, `SftpConfig`
- `GcpConfig`
- `VaultConfig`

Example:

```python
from aliframework.config import DbConfig, DatabaseType

cfg = DbConfig(
    db_type=DatabaseType.POSTGRES,
    host="localhost",
    port=5432,
    user="pguser",
    password="pgpass",
    database="pgdb",
)
```

## DB module (`db`)

```python
from aliframework.config import DbConfig, DatabaseType
from aliframework.db import create_db_connection

cfg = DbConfig(
    db_type=DatabaseType.POSTGRES,
    host="localhost",
    port=5432,
    user="pguser",
    password="pgpass",
    database="pgdb",
)
conn = create_db_connection(cfg)
```

Basic CRUD demo (works for Postgres/MySQL):

```python
def demo_crud(conn):
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS items (id INT PRIMARY KEY, name TEXT)")
    cur.execute("DELETE FROM items")
    cur.execute("INSERT INTO items (id, name) VALUES (%s, %s)", (1, "foo"))
    cur.execute("SELECT name FROM items WHERE id = %s", (1,))
    print("read:", cur.fetchone())
    cur.execute("UPDATE items SET name = %s WHERE id = %s", ("bar", 1))
    cur.execute("SELECT name FROM items WHERE id = %s", (1,))
    print("after update:", cur.fetchone())
    cur.execute("DELETE FROM items WHERE id = %s", (1,))
    conn.commit()
```

## MongoDB module (`nosql`)

```python
from aliframework.nosql import create_mongo_client

client = create_mongo_client("mongodb://localhost:27017")
db = client["mydb"]
col = db["items"]
col.insert_one({"_id": 1, "name": "foo"})
print(col.find_one({"_id": 1}))
col.update_one({"_id": 1}, {"$set": {"name": "bar"}})
col.delete_one({"_id": 1})
```

## API module (`api`)

```python
from aliframework.api import ApiClient
from aliframework.config import ApiConfig, ApiAuthType

cfg = ApiConfig(
    base_url="https://httpbin.org",
    auth_type=ApiAuthType.NONE,
)
client = ApiClient(cfg)
resp = client.get("/get", params={"hello": "world"})
print(resp.json()["args"])
```

Auth modes supported:

- `NONE`
- `BASIC` – username/password
- `BEARER` – token
- `API_KEY_HEADER` – header-based API key
- `API_KEY_QUERY` – query parameter API key
- `OAUTH2_CLIENT_CREDENTIALS` – obtains token then uses Bearer

## SFTP module (`sftp`)

```python
from aliframework.config import SftpConfig, SftpAuthType
from aliframework.sftp import create_sftp_client

cfg = SftpConfig(
    host="localhost",
    port=2222,
    username="user",
    password="secret",
    auth_type=SftpAuthType.PASSWORD,
)
sftp = create_sftp_client(cfg)
print(sftp.listdir("upload"))
sftp.close()
```

## Secrets module (`secrets`)

```python
from aliframework.config import VaultConfig
from aliframework.secrets import create_vault_client

cfg = VaultConfig(url="http://localhost:8200", role="dev-role", token="root")
client = create_vault_client(cfg)
print(client.is_authenticated())
```

KV CRUD example is documented at the bottom of `aliframework/secrets.py` and in the
`notebook/secrets_vault.ipynb` notebook.

## GCP module (`gcp`)

Helpers for:

- GCS: `create_gcs_client`, `gcs_to_gcs`, `gcs_to_pandas`, `pandas_to_gcs`, `pyspark_df_to_gcs`
- BigQuery: `create_bigquery_client`, `gcs_to_bq`, `df_to_bq`, `bq_to_gcs`, `gcs_to_df`
- Pipelines: `create_dataproc_client`, `create_dataflow_client`,
  `gcs_to_dataflow_to_bq`, `gcs_to_dataproc_to_bq`

Example (GCS + pandas):

```python
from aliframework.config import GcpConfig
from aliframework.gcp import create_gcs_client, gcs_to_pandas, pandas_to_gcs

cfg = GcpConfig(project_id="my-project", credentials_path="/path/to/sa.json")
client = create_gcs_client(cfg)

df = gcs_to_pandas(client, "gs://my-bucket/input.csv")
pandas_to_gcs(client, df, "gs://my-bucket/output.csv", pandas_to_fn="to_csv", index=False)
```

See `notebook/gcp_storage_bq.ipynb` for a full demo including BigQuery.

## Testing and coverage

The `aliframework` package ships with both unit tests (under `tests/unit`) and
optional integration tests (under `tests/integration`). Together they provide
100% statement coverage for the package when run with the command shown in the
root `README.md`.

For detailed, module-specific notes on what is covered in tests and which
error paths are exercised, see `docs/testing-and-coverage.md`.

## CRUD examples overview

This package includes commented “Usage examples” at the bottom of each module showing
basic CRUD-style operations for DBs, MongoDB, HTTP APIs, SFTP, Vault, and GCP.
You can copy/paste them into your own scripts or run them via the notebooks.
