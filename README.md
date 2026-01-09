# alidataframework

A Python framework of composable helpers to connect to:

- Relational databases: Postgres, MySQL, SQL Server, Oracle
- NoSQL: MongoDB
- HTTP APIs with multiple auth methods
- SFTP servers (password / key / both)
- GCP services: GCS, BigQuery, Dataproc, Dataflow
- HashiCorp Vault (with token or GCP-based auth)

It is designed to be:

- **Thin** – standardises configuration, returns real drivers/clients
- **Testable** – unit tests with mocks + optional docker-based integration tests
- **Notebook-friendly** – ready-made notebooks under `notebook/` for quick exploration

## Installation

From this repo root:

```bash
pip install -e .[all,dev]
```

This installs:

- Core: `aliframework`
- Extras (`[all]`): DB drivers, Mongo, Paramiko, GCP clients, pandas, pyspark, hvac
- Dev tools: pytest, pytest-mock

## Quick start

### Databases (Postgres example)

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
cur = conn.cursor()
cur.execute("SELECT 1")
print(cur.fetchone())
conn.close()
```

### MongoDB

```python
from aliframework.nosql import create_mongo_client

client = create_mongo_client("mongodb://localhost:27017")
print(client.admin.command("ping"))
```

### HTTP APIs

```python
from aliframework.api import ApiClient
from aliframework.config import ApiConfig, ApiAuthType

cfg = ApiConfig(base_url="https://httpbin.org", auth_type=ApiAuthType.NONE)
client = ApiClient(cfg)
resp = client.get("/get", params={"hello": "world"})
print(resp.json()["args"])
```

### SFTP

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

### Vault

```python
from aliframework.config import VaultConfig
from aliframework.secrets import create_vault_client

cfg = VaultConfig(url="http://localhost:8200", role="dev-role", token="root")
client = create_vault_client(cfg)
print("authenticated", client.is_authenticated())
```

### GCP (GCS + BigQuery)

```python
from aliframework.config import GcpConfig
from aliframework.gcp import create_gcs_client, create_bigquery_client

cfg = GcpConfig(project_id="my-project", credentials_path="/path/to/sa.json")
gcs_client = create_gcs_client(cfg)
bq_client = create_bigquery_client(cfg)
```

See `notebook/gcp_storage_bq.ipynb` for an end-to-end example.

## Docker-based test environment

`docker-compose.yml` defines local services:

- Postgres, MySQL, Mongo
- SFTP (user/secret)
- Vault (dev mode, token `root`)

Use the Makefile targets:

```bash
make compose-up    # start services
make compose-down  # stop services
make test-unit     # run unit tests (no services required)
```

Integration tests live under `tests/integration` and can be run with:

```bash
PYTHONPATH=. pytest tests/integration -m integration
```

For a detailed, module-by-module breakdown of the test suite and how we
achieve 100% coverage for `aliframework`, see
`docs/testing-and-coverage.md`.

## Notebooks

The `notebook/` folder contains Jupyter notebooks to quickly try each module:

- `db.ipynb` – DB CRUD (Postgres by default)
- `nosql.ipynb` – MongoDB CRUD
- `api.ipynb` – HTTP CRUD-style calls
- `sftp.ipynb` – SFTP file lifecycle
- `secrets_vault.ipynb` – Vault KV CRUD
- `gcp_storage_bq.ipynb` – GCS + BigQuery pipelines

Launch with:

```bash
pip install notebook
jupyter notebook
```

## Full module docs

See `aliframework/README.md` for a more detailed feature breakdown and CRUD examples.
