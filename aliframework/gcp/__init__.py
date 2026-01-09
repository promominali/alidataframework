"""GCP helpers (GCS, BigQuery, Dataproc, Dataflow) and pipelines.

This package exposes:
- Client factory functions: create_gcs_client, create_bigquery_client, ...
- Higher-level pipelines: gcs_to_gcs, gcs_to_bq, gcs_to_pandas, pandas_to_gcs,
  pyspark_df_to_gcs, gcs_to_df, df_to_bq, bq_to_gcs, gcs_to_dataflow_to_bq,
  gcs_to_dataproc_to_bq.
"""

from .storage import (
    create_gcs_client,
    gcs_to_gcs,
    gcs_to_pandas,
    pandas_to_gcs,
    pyspark_df_to_gcs,
)
from .bigquery import (
    create_bigquery_client,
    gcs_to_bq,
    df_to_bq,
    bq_to_gcs,
    gcs_to_df,
)
from .pipelines import (
    create_dataproc_client,
    create_dataflow_client,
    gcs_to_dataflow_to_bq,
    gcs_to_dataproc_to_bq,
)

__all__ = [
    # storage
    "create_gcs_client",
    "gcs_to_gcs",
    "gcs_to_pandas",
    "pandas_to_gcs",
    "pyspark_df_to_gcs",
    # bigquery
    "create_bigquery_client",
    "gcs_to_bq",
    "df_to_bq",
    "bq_to_gcs",
    "gcs_to_df",
    # pipelines
    "create_dataproc_client",
    "create_dataflow_client",
    "gcs_to_dataflow_to_bq",
    "gcs_to_dataproc_to_bq",
]
