from __future__ import annotations

"""Higher-level GCP pipelines using Dataflow and Dataproc.

These are intentionally generic and assume you know which templates or
Dataproc jobs you want to run. They only wire up clients & requests.
"""

from typing import Any
import os

from ..config import GcpConfig
from .storage import MissingDriverError, _prepare_credentials  # type: ignore[attr-defined]


def create_dataproc_client(config: GcpConfig, region: str) -> Any:
    _prepare_credentials(config)
    try:
        from google.cloud import dataproc_v1  # type: ignore
    except ImportError as exc:
        raise MissingDriverError("google-cloud-dataproc is required for Dataproc") from exc

    return dataproc_v1.JobControllerClient(
        client_options={"api_endpoint": f"{region}-dataproc.googleapis.com:443"}
    )


def create_dataflow_client(config: GcpConfig) -> Any:
    _prepare_credentials(config)
    try:
        from googleapiclient.discovery import build  # type: ignore
    except ImportError as exc:
        raise MissingDriverError("google-api-python-client is required for Dataflow") from exc

    return build("dataflow", "v1b3")


def gcs_to_dataflow_to_bq(
    *,
    config: GcpConfig,
    template_path: str,
    parameters: dict,
    region: str,
    job_name: str,
) -> Any:
    """Launch a Dataflow template that reads from GCS and writes to BigQuery.

    You must provide a ready Dataflow template and the correct parameters
    (typically including inputFilePattern, outputTable, tempLocation, etc.).
    """
    client = create_dataflow_client(config)
    project = config.project_id

    body = {
        "jobName": job_name,
        "parameters": parameters,
        "environment": {"tempLocation": parameters.get("tempLocation")},
    }

    request = (
        client.projects()
        .locations()
        .templates()
        .launch(projectId=project, location=region, gcsPath=template_path, body=body)
    )
    return request.execute()


def gcs_to_dataproc_to_bq(
    *,
    config: GcpConfig,
    region: str,
    cluster_name: str,
    main_python_file_uri: str,
    args: list[str],
) -> Any:
    """Submit a Dataproc PySpark job that reads from GCS and writes to BigQuery.

    main_python_file_uri should point to a PySpark script in GCS.
    """
    client = create_dataproc_client(config, region)
    project = config.project_id

    job = {
        "placement": {"cluster_name": cluster_name},
        "pyspark_job": {
            "main_python_file_uri": main_python_file_uri,
            "args": args,
        },
    }

    op = client.submit_job(request={"project_id": project, "region": region, "job": job})
    return op
