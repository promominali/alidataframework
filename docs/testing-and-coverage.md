# Testing and coverage for `aliframework`

This document describes the test strategy and coverage for each module in the
`aliframework` package.

The full suite reaches **100% statement coverage** for `aliframework` when run
with:

```bash
python -m pytest --cov=aliframework --cov-report=term-missing tests/
```

This includes both unit tests (pure Python, no external services) and optional
integration tests that talk to real services via `docker-compose`.

## Test layout

- **Unit tests**: `tests/unit/`
  - Fast, isolated tests using stub modules and dummy clients.
  - Cover all success and error branches for each helper.
- **Integration tests**: `tests/integration/`
  - Use live services (Postgres, MySQL, MongoDB, SFTP, Vault) defined in
    `docker-compose.yml`.
  - Marked with `@pytest.mark.integration`.

To start the integration services:

```bash
make compose-up
```

Then you can run only the integration tests with:

```bash
PYTHONPATH=. pytest tests/integration -m integration
```

---

## Module-by-module details

### `aliframework.api` – HTTP client

The `ApiClient` wraps `requests.Session` and supports multiple authentication
modes defined by `ApiAuthType`:

- `NONE`
- `BASIC` (username/password)
- `BEARER` (Bearer token header)
- `API_KEY_HEADER` (custom header)
- `API_KEY_QUERY` (query parameter)
- `OAUTH2_CLIENT_CREDENTIALS` (client-credentials grant)

Unit tests in `tests/unit/test_api.py` verify:

- `_get_session` applies `default_headers` from `ApiConfig` to a new
  `requests.Session`.
- `_apply_auth` behaviour for all auth modes:
  - `NONE` leaves session unmodified.
  - `BASIC` sets `session.auth = (username, password)`.
  - `BEARER` sets the `Authorization: Bearer <token>` header.
  - `API_KEY_HEADER` adds the configured header only when both name and value
    are provided.
  - `API_KEY_QUERY` defers to per-request handling (see below).
  - `OAUTH2_CLIENT_CREDENTIALS` delegates to `_obtain_oauth2_token`.
  - Any unsupported `auth_type` raises `ValueError`.
- `_obtain_oauth2_token`:
  - Raises `ValueError` when required OAuth2 fields
    (`oauth2_token_url`, `oauth2_client_id`, `oauth2_client_secret`) are
    missing.
  - Performs a `POST` to the configured token URL with a
    `grant_type=client_credentials` payload.
  - On success, pulls `access_token` from the JSON body and sets a
    `Bearer` header.
  - Raises `RuntimeError` if `access_token` is missing from the response.
- `request()`:
  - Correctly joins `base_url` and `path`, regardless of trailing/leading
    slashes.
  - Upper-cases HTTP methods.
  - Merges any explicit `params` with an API key in the query string when
    `auth_type == API_KEY_QUERY`.
- Convenience methods `get()` and `post()` delegate directly to `request()`.

These tests use a dummy in-memory `Session` implementation so no real network
calls are made.

---

### `aliframework.db` – relational databases

`create_db_connection` normalises connection parameters and returns a
DB-API-compatible connection for:

- Postgres (`DatabaseType.POSTGRES` via `psycopg2`)
- MySQL (`DatabaseType.MYSQL` via `pymysql`)
- SQL Server (`DatabaseType.MSSQL` via `pyodbc`)
- Oracle (`DatabaseType.ORACLE` via `oracledb`)

Unit tests in `tests/unit/test_db.py` cover:

- **Missing driver errors**:
  - For each DB type, import of the corresponding driver is forced to fail
    using a `builtins.__import__` patch.
  - `MissingDriverError` is raised with a descriptive message.
- **Postgres**:
  - Uses a dummy `psycopg2` module to capture `connect` kwargs.
  - Verifies that `host`, `port`, `user`, `password`, and `database` map to
    `connect(host=..., port=..., dbname=...)`.
  - Ensures any `extra` dict entries (e.g. `connect_timeout`) are forwarded.
- **MySQL**:
  - Uses a dummy `pymysql` to assert that `database` is passed as `db`.
- **SQL Server (MSSQL)**:
  - When `extra["dsn"]` is provided, passes that DSN string directly to
    `pyodbc.connect`.
  - When no DSN is provided, constructs an ODBC connection string including
    driver, server, port, database, username, and password.
- **Oracle**:
  - Uses a dummy `oracledb` with `makedsn` and `connect`.
  - Asserts that the DSN combines host, port, and service name correctly, and
    that `extra` options (e.g. `encoding`) are forwarded to `connect`.
- Unsupported `db_type` values result in a `ValueError`.

Integration tests in `tests/integration/test_databases_and_mongo.py`:

- Connect to real Postgres and MySQL instances from `docker-compose.yml`.
- Create a simple table, perform basic CRUD (insert, select, update, delete),
  and assert expected results.

---

### `aliframework.nosql` – MongoDB helper

`create_mongo_client` builds a `pymongo.MongoClient` given a MongoDB URI and
optional username/password.

Unit tests in `tests/unit/test_nosql.py`:

- Use a dummy `pymongo` module with a custom `MongoClient` implementation.
- Verify:
  - Missing `pymongo` import raises `MissingDriverError`.
  - Without credentials, the URI and extra kwargs (e.g. `connectTimeoutMS`)
    are passed through as-is.
  - With `username` and `password`, these parameters plus any additional
    kwargs (e.g. `authSource`) are included when constructing the client.

Integration tests (in `tests/integration/test_databases_and_mongo.py`) use a
real MongoDB service to:

- Connect and run the `admin.command("ping")` health check.

---

### `aliframework.secrets` – Vault client

`create_vault_client` wraps `hvac.Client` and supports:

- Direct token auth using `VaultConfig.token`.
- GCP auth flow using `VaultConfig.jwt` and `VaultConfig.role`.

Unit tests in `tests/unit/test_secrets.py`:

- Stub the `hvac` module and `Client` class.
- Cover:
  - Import failure for `hvac` -> `MissingDriverError`.
  - Direct-token auth: constructs a client with the provided URL and token,
    and does not call GCP login.
  - GCP auth: constructs a client without a direct token, then calls
    `client.auth.gcp.login(role=<role>, jwt=<jwt>)`.

Integration tests in `tests/integration/test_vault.py`:

- Talk to a real Vault dev server (`docker-compose` service).
- Authenticate using token, enable a KVv2 engine if needed, and perform
  KV CRUD (write, read, assert value).

---

### `aliframework.sftp` – SFTP client

`create_sftp_client` constructs a `paramiko.Transport` and wraps it in an
`SFTPClient`. It supports:

- `SftpAuthType.PASSWORD`
- `SftpAuthType.PRIVATE_KEY`
- `SftpAuthType.PASSWORD_AND_KEY`

Unit tests in `tests/unit/test_sftp_unit.py`:

- Replace `paramiko` with a stub module containing dummy `Transport`,
  `RSAKey`, and `SFTPClient` classes.
- Verify:
  - Import failure for `paramiko` -> `MissingDriverError`.
  - Password-only auth calls `transport.connect(username=..., password=...)`.
  - Private-key auth loads a key via `RSAKey.from_private_key_file` and calls
    `transport.connect(username=..., pkey=<key>)` with no password.
  - Password+key auth calls `transport.connect` with both `password` and
    `pkey`.
  - Unsupported `auth_type` values raise `ValueError`.

Integration tests in `tests/integration/test_sftp.py`:

- Connect to a real SFTP server from `docker-compose`.
- List a known directory, upload a small file, and close the connection.

---

### `aliframework.gcp.storage` – GCS & DataFrames

This module provides:

- `_prepare_credentials` – sets `GOOGLE_APPLICATION_CREDENTIALS` when
  `credentials_path` is provided in `GcpConfig`.
- `create_gcs_client` – returns a `google.cloud.storage.Client` for the
  configured project.
- `gcs_to_gcs` – copies an object between two `gs://` URIs.
- `gcs_to_pandas` – reads a `gs://` file into a pandas DataFrame.
- `pandas_to_gcs` – writes a pandas DataFrame to a `gs://` URI.
- `pyspark_df_to_gcs` – writes a PySpark DataFrame to GCS using its
  `.write` API.

Unit tests in `tests/unit/test_gcp.py` cover:

- `_prepare_credentials`:
  - Sets `GOOGLE_APPLICATION_CREDENTIALS` when a credentials path is present.
- `create_gcs_client`:
  - Uses a fake `google.cloud.storage.Client` to assert the project ID is
    passed through.
  - Forces an `ImportError` for `google.cloud.storage` to trigger
    `MissingDriverError`.
- `gcs_to_gcs`:
  - Uses a dummy storage client with in-memory buckets and blobs.
  - Copies an object between two `gs://` URIs and asserts the destination
    bucket and object name.
  - Raises `ValueError` for non-`gs://` URIs.
- `gcs_to_pandas`:
  - Successful path: mocks `pandas.read_csv` to read from a `BytesIO` buffer
    and returns structured data, verifying kwargs are forwarded.
  - Non-`gs://` URI -> `ValueError`.
  - Forced `ImportError` of `pandas` -> `MissingDriverError`.
- `pandas_to_gcs`:
  - Successful path: uses a dummy DataFrame object with a `to_csv` method
    writing bytes to a buffer, and asserts that `upload_from_file(...,
    rewind=True)` is called with the expected bytes.
  - Non-`gs://` URI -> `ValueError`.
  - Forced `ImportError` of `pandas` -> `MissingDriverError`.
- `pyspark_df_to_gcs`:
  - Successful path: injects a fake `pyspark` module and a dummy DataFrame
    whose `.write` chain records `format`, `options`, `mode`, and `save`
    calls.
  - Forced `ImportError` of `pyspark` -> `MissingDriverError`.

---

### `aliframework.gcp.bigquery` – BigQuery helpers

Functions:

- `_prepare_credentials` – identical behaviour to `storage._prepare_credentials`.
- `create_bigquery_client` – returns a `google.cloud.bigquery.Client`.
- `gcs_to_bq` – loads from GCS into a BigQuery table with a configurable
  `LoadJobConfig`.
- `df_to_bq` – loads a pandas DataFrame into BigQuery.
- `bq_to_gcs` – exports a BigQuery table to GCS with an `ExtractJobConfig`.
- `gcs_to_df` – convenience wrapper delegating to `storage.gcs_to_pandas`.

Unit tests in `tests/unit/test_gcp.py`:

- Stub `google.cloud.bigquery` with:
  - `Client`, `SourceFormat`, `LoadJobConfig`, and `job.ExtractJobConfig`.
  - Job objects whose `.result()` returns sentinel values.
- Cover:
  - `_prepare_credentials` sets the env var when called from this module.
  - `create_bigquery_client` happy path and missing-driver path
    (`ImportError` -> `MissingDriverError`).
  - `gcs_to_bq`:
    - Invokes `client.load_table_from_uri`.
    - Applies extra kwargs (e.g. `field_delimiter`) to the `LoadJobConfig`
      via the `setattr` loop.
  - `df_to_bq`:
    - Successful path with a stub `pandas` module present.
    - Forced `ImportError` of `pandas` -> `MissingDriverError`.
  - `bq_to_gcs`:
    - Invokes `client.extract_table` and applies extra kwargs (e.g.
      `compression`) to the `ExtractJobConfig`.
  - `gcs_to_df`:
    - Delegates to `storage.gcs_to_pandas` and forwards arguments.

---

### `aliframework.gcp.pipelines` – Dataflow & Dataproc

Functions:

- `create_dataproc_client` – returns a `google.cloud.dataproc_v1.JobControllerClient`.
- `create_dataflow_client` – returns a discovery-based Dataflow client.
- `gcs_to_dataflow_to_bq` – launches a Dataflow template that reads from GCS
  and writes to BigQuery.
- `gcs_to_dataproc_to_bq` – submits a Dataproc PySpark job reading from GCS
  and writing to BigQuery.

Unit tests in `tests/unit/test_gcp.py`:

- Stub `google.cloud.dataproc_v1.JobControllerClient` to capture
  `submit_job` requests.
- Stub `googleapiclient.discovery.build` to return a client with the chained
  `projects().locations().templates().launch(...).execute()` API.
- Verify:
  - `create_dataproc_client` passes the correct `api_endpoint` for the
    configured region and raises `MissingDriverError` when the import fails.
  - `create_dataflow_client` returns a stub client and raises
    `MissingDriverError` on missing `googleapiclient`.
  - `gcs_to_dataflow_to_bq` constructs the expected request body and that
    `launch(...).execute()` is invoked.
  - `gcs_to_dataproc_to_bq` submits a job with the expected placement,
    `pyspark_job` fields, and arguments.

---

## Summary

- Every module in `aliframework` has both behavioural tests (unit) and, where
  applicable, real-service integration tests.
- Error handling for missing third-party drivers is explicitly exercised via
  import patching, ensuring clear `MissingDriverError` messages.
- The test suite is designed to be fast by default (unit tests only) while
  still allowing end-to-end verification via `docker-compose`-backed
  integration tests.
