from __future__ import annotations

"""BigQuery helpers and pipelines with GCS/DataFrames."""

from typing import Any
import os

from ..config import GcpConfig
from .storage import MissingDriverError


def _prepare_credentials(config: GcpConfig) -> None:
    if config.credentials_path:
        os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", config.credentials_path)


def create_bigquery_client(config: GcpConfig) -> Any:
    _prepare_credentials(config)
    try:
        from google.cloud import bigquery  # type: ignore
    except ImportError as exc:
        raise MissingDriverError("google-cloud-bigquery is required for BigQuery") from exc

    return bigquery.Client(project=config.project_id)


def gcs_to_bq(client: Any, *, table_id: str, source_uri: str, file_format: str = "CSV", **kwargs: Any) -> Any:
    """Load data from GCS into BigQuery.

    :param table_id: Fully qualified table id, e.g. "project.dataset.table".
    :param source_uri: GCS URI like gs://bucket/path/file.*
    :param file_format: CSV, PARQUET, NEWLINE_DELIMITED_JSON, etc.
    :param kwargs: Extra attributes to set on the LoadJobConfig.
    """
    from google.cloud import bigquery  # type: ignore

    load_config = bigquery.LoadJobConfig(
        source_format=getattr(bigquery.SourceFormat, file_format)
    )
    for k, v in (kwargs or {}).items():
        setattr(load_config, k, v)

    load_job = client.load_table_from_uri(source_uri, table_id, job_config=load_config)
    return load_job.result()


def df_to_bq(client: Any, df, *, table_id: str, **kwargs: Any) -> Any:
    """Load a pandas DataFrame into BigQuery."""
    try:
        import pandas  # noqa: F401
    except ImportError as exc:
        raise MissingDriverError("pandas is required for df_to_bq") from exc

    job = client.load_table_from_dataframe(df, table_id, **kwargs)
    return job.result()


def bq_to_gcs(client: Any, *, table_id: str, destination_uri: str, file_format: str = "CSV", **kwargs: Any) -> Any:
    """Export a BigQuery table to GCS.

    :param table_id: Fully qualified table id, e.g. "project.dataset.table".
    :param destination_uri: GCS URI like gs://bucket/path/file.* (can contain wildcards)
    :param file_format: CSV, AVRO, PARQUET, etc.
    :param kwargs: Extra attributes to set on the ExtractJobConfig.
    """
    from google.cloud import bigquery  # type: ignore

    extract_config = bigquery.job.ExtractJobConfig(destination_format=file_format)
    for k, v in (kwargs or {}).items():
        setattr(extract_config, k, v)

    job = client.extract_table(table_id, destination_uri, job_config=extract_config)
    return job.result()


def gcs_to_df(client: Any, uri: str, *, pandas_read_fn: str = "read_csv", **kwargs: Any):
    """Shortcut via storage.gcs_to_pandas."""
    from .storage import gcs_to_pandas

    return gcs_to_pandas(client, uri, pandas_read_fn=pandas_read_fn, **kwargs)

# ---------------------------------------------------------------------------
# Simple table CRUD via BigQuery (conceptual):
# from aliframework.config import GcpConfig
# from aliframework.gcp import create_bigquery_client, df_to_bq
# import pandas as pd
#
# cfg = GcpConfig(project_id="my-project", credentials_path="/path/to/sa.json")
# client = create_bigquery_client(cfg)
#
# table_id = "my-project.my_dataset.items"
# df = pd.DataFrame([{"id": 1, "name": "foo"}])
# # CREATE/INSERT
# df_to_bq(client, df, table_id=table_id)
# # READ/QUERY and UPDATE/DELETE are typically done via SQL queries using client.query(...).
