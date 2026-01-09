from __future__ import annotations

"""GCS and dataframe helpers."""

from typing import Any, Optional
import os

from ..config import GcpConfig
from ..errors import MissingDriverError


def _prepare_credentials(config: GcpConfig) -> None:
    if config.credentials_path:
        os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", config.credentials_path)


def create_gcs_client(config: GcpConfig) -> Any:
    _prepare_credentials(config)
    try:
        from google.cloud import storage  # type: ignore
    except ImportError as exc:
        raise MissingDriverError("google-cloud-storage is required for GCS") from exc

    return storage.Client(project=config.project_id)


def gcs_to_gcs(client: Any, src_uri: str, dest_uri: str) -> None:
    """Copy object from one GCS URI to another.

    URIs must be in the form gs://bucket/path/to/object.
    """
    from urllib.parse import urlparse

    def parse(uri: str):
        parsed = urlparse(uri)
        if parsed.scheme != "gs":
            raise ValueError(f"Not a GCS URI: {uri}")
        return parsed.netloc, parsed.path.lstrip("/")

    src_bucket_name, src_blob_name = parse(src_uri)
    dest_bucket_name, dest_blob_name = parse(dest_uri)

    src_bucket = client.bucket(src_bucket_name)
    src_blob = src_bucket.blob(src_blob_name)
    dest_bucket = client.bucket(dest_bucket_name)

    client.copy_blob(src_blob, dest_bucket, dest_blob_name)


def gcs_to_pandas(client: Any, uri: str, *, pandas_read_fn: str = "read_csv", **kwargs: Any):
    """Read a GCS file into a pandas DataFrame.

    :param pandas_read_fn: Name of pandas read function, e.g. "read_csv" or "read_parquet".
    """
    try:
        import pandas as pd  # type: ignore
    except ImportError as exc:
        raise MissingDriverError("pandas is required for gcs_to_pandas") from exc

    from urllib.parse import urlparse

    parsed = urlparse(uri)
    if parsed.scheme != "gs":
        raise ValueError(f"Not a GCS URI: {uri}")
    bucket = client.bucket(parsed.netloc)
    blob = bucket.blob(parsed.path.lstrip("/"))
    data = blob.download_as_bytes()

    read_fn = getattr(pd, pandas_read_fn)
    from io import BytesIO

    return read_fn(BytesIO(data), **kwargs)


def pandas_to_gcs(client: Any, df, uri: str, *, pandas_to_fn: str = "to_csv", **kwargs: Any) -> None:
    """Write a pandas DataFrame to GCS.

    :param pandas_to_fn: Name of DataFrame method to use, e.g. "to_csv" or "to_parquet".
    """
    try:
        import pandas  # noqa: F401  # just to ensure pandas is installed
    except ImportError as exc:
        raise MissingDriverError("pandas is required for pandas_to_gcs") from exc

    from urllib.parse import urlparse
    from io import BytesIO

    parsed = urlparse(uri)
    if parsed.scheme != "gs":
        raise ValueError(f"Not a GCS URI: {uri}")
    bucket = client.bucket(parsed.netloc)
    blob = bucket.blob(parsed.path.lstrip("/"))

    buf = BytesIO()
    to_fn = getattr(df, pandas_to_fn)
    to_fn(buf, **kwargs)
    buf.seek(0)
    blob.upload_from_file(buf, rewind=True)


def pyspark_df_to_gcs(df, uri: str, format: str = "parquet", **options: Any) -> None:
    """Write a PySpark DataFrame to GCS using the configured Spark session.

    This assumes your Spark cluster is configured with the appropriate
    GCS connector and credentials.
    """
    try:
        import pyspark  # noqa: F401
    except ImportError as exc:
        raise MissingDriverError("pyspark is required for pyspark_df_to_gcs") from exc

    (df.write
       .format(format)
       .options(**options)
       .mode("overwrite")
       .save(uri))

# ---------------------------------------------------------------------------
# CRUD-ish object lifecycle example for GCS:
# from aliframework.config import GcpConfig
# from aliframework.gcp import create_gcs_client, gcs_to_gcs, gcs_to_pandas, pandas_to_gcs
#
# cfg = GcpConfig(project_id="my-project", credentials_path="/path/to/sa.json")
# client = create_gcs_client(cfg)
#
# src = "gs://my-bucket/input.csv"
# dst = "gs://my-bucket/copy.csv"
# gcs_to_gcs(client, src, dst)  # COPY (create new object)
# df = gcs_to_pandas(client, dst)  # READ into DataFrame
# pandas_to_gcs(client, df, "gs://my-bucket/output.csv")  # WRITE processed data back
# (Delete can be done via client.bucket(...).blob(...).delete())
