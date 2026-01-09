from __future__ import annotations

from types import ModuleType, SimpleNamespace
import builtins
import os
import sys

import pytest

from aliframework.config import GcpConfig
from aliframework.gcp.bigquery import (
    create_bigquery_client,
    gcs_to_bq,
    df_to_bq,
    bq_to_gcs,
    gcs_to_df,
)
from aliframework.gcp.pipelines import (
    create_dataproc_client,
    create_dataflow_client,
    gcs_to_dataflow_to_bq,
    gcs_to_dataproc_to_bq,
)
from aliframework.gcp.storage import (
    MissingDriverError,
    _prepare_credentials,
    create_gcs_client,
    gcs_to_gcs,
    gcs_to_pandas,
    pandas_to_gcs,
    pyspark_df_to_gcs,
)


@pytest.fixture(autouse=True)
def _cleanup_modules_and_env():
    original_modules = sys.modules.copy()
    original_env = os.environ.copy()
    yield
    for name in list(sys.modules.keys()):
        if name not in original_modules:
            sys.modules.pop(name, None)
    os.environ.clear()
    os.environ.update(original_env)


def _install_fake_google_storage():
    class DummyStorageClient:
        def __init__(self, project: str | None = None):
            self.project = project

    google = ModuleType("google")
    cloud = ModuleType("google.cloud")
    storage = ModuleType("google.cloud.storage")
    storage.Client = DummyStorageClient  # type: ignore[attr-defined]

    cloud.storage = storage  # type: ignore[attr-defined]
    google.cloud = cloud  # type: ignore[attr-defined]

    sys.modules["google"] = google
    sys.modules["google.cloud"] = cloud
    sys.modules["google.cloud.storage"] = storage

    return DummyStorageClient


def _install_fake_google_bigquery():
    class DummyJob:
        def __init__(self, result_value="result"):
            self._value = result_value

        def result(self):
            return self._value

    class DummySourceFormat:
        CSV = "CSV"
        PARQUET = "PARQUET"

    class DummyLoadJobConfig:
        def __init__(self, source_format=None):
            self.source_format = source_format

    class DummyExtractJobConfig:
        def __init__(self, destination_format=None):
            self.destination_format = destination_format

    class DummyBigQueryClient:
        def __init__(self, project: str | None = None):
            self.project = project
            self.load_calls = []
            self.extract_calls = []
            self.df_calls = []

        def load_table_from_uri(self, source_uri, table_id, job_config=None):
            self.load_calls.append((source_uri, table_id, job_config))
            return DummyJob("load-done")

        def load_table_from_dataframe(self, df, table_id, **kwargs):
            self.df_calls.append((df, table_id, kwargs))
            return DummyJob("df-done")

        def extract_table(self, table_id, destination_uri, job_config=None):
            self.extract_calls.append((table_id, destination_uri, job_config))
            return DummyJob("extract-done")

    bigquery = ModuleType("google.cloud.bigquery")
    bigquery.Client = DummyBigQueryClient  # type: ignore[attr-defined]
    bigquery.SourceFormat = DummySourceFormat  # type: ignore[attr-defined]
    bigquery.LoadJobConfig = DummyLoadJobConfig  # type: ignore[attr-defined]
    bigquery.job = SimpleNamespace(ExtractJobConfig=DummyExtractJobConfig)

    # Reuse/extend any existing google.cloud from storage helper if present
    google = sys.modules.get("google") or ModuleType("google")
    cloud = getattr(google, "cloud", ModuleType("google.cloud"))
    cloud.bigquery = bigquery  # type: ignore[attr-defined]
    google.cloud = cloud  # type: ignore[attr-defined]

    sys.modules["google"] = google
    sys.modules["google.cloud"] = cloud
    sys.modules["google.cloud.bigquery"] = bigquery

    return DummyBigQueryClient


def _install_fake_google_dataproc():
    class DummyJobControllerClient:
        def __init__(self, client_options=None):
            self.client_options = client_options
            self.submitted_jobs = []

        def submit_job(self, request):
            self.submitted_jobs.append(request)
            return {"job": request}

    dataproc_v1 = ModuleType("google.cloud.dataproc_v1")
    dataproc_v1.JobControllerClient = DummyJobControllerClient  # type: ignore[attr-defined]

    google = sys.modules.get("google") or ModuleType("google")
    cloud = getattr(google, "cloud", ModuleType("google.cloud"))
    cloud.dataproc_v1 = dataproc_v1  # type: ignore[attr-defined]
    google.cloud = cloud  # type: ignore[attr-defined]

    sys.modules["google"] = google
    sys.modules["google.cloud"] = cloud
    sys.modules["google.cloud.dataproc_v1"] = dataproc_v1

    return DummyJobControllerClient


def _install_fake_googleapiclient():
    class FakeTemplates:
        def __init__(self):
            self.launch_calls = []

        def launch(self, **kwargs):
            self.launch_calls.append(kwargs)
            return SimpleNamespace(execute=lambda: {"launched": kwargs})

    class FakeLocations:
        def __init__(self, templates):
            self._templates = templates

        def templates(self):
            return self._templates

    class FakeProjects:
        def __init__(self, locations):
            self._locations = locations

        def locations(self):
            return self._locations

    class FakeDataflowClient:
        def __init__(self):
            self.templates = FakeTemplates()
            self.locations_obj = FakeLocations(self.templates)
            self.projects_obj = FakeProjects(self.locations_obj)

        def projects(self):
            return self.projects_obj

    def build(api_name: str, version: str):  # noqa: D401 - mimic googleapiclient.discovery.build
        return FakeDataflowClient()

    discovery = ModuleType("googleapiclient.discovery")
    discovery.build = build  # type: ignore[attr-defined]

    googleapiclient = ModuleType("googleapiclient")
    googleapiclient.discovery = discovery  # type: ignore[attr-defined]

    sys.modules["googleapiclient"] = googleapiclient
    sys.modules["googleapiclient.discovery"] = discovery

    return build


def test_prepare_credentials_sets_env_when_path_provided():
    cfg = GcpConfig(project_id="p", credentials_path="/tmp/creds.json")
    os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)

    _prepare_credentials(cfg)

    assert os.environ["GOOGLE_APPLICATION_CREDENTIALS"] == "/tmp/creds.json"


def test_bigquery_prepare_credentials_sets_env():
    # Use the helper from bigquery module specifically
    from aliframework.gcp.bigquery import _prepare_credentials as _bq_prepare

    cfg = GcpConfig(project_id="p", credentials_path="/tmp/bq-creds.json")
    os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)

    _bq_prepare(cfg)
    assert os.environ["GOOGLE_APPLICATION_CREDENTIALS"] == "/tmp/bq-creds.json"


def test_create_gcs_client_missing_driver_raises(monkeypatch):
    # Force ImportError when attempting to import google.cloud.storage
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name.startswith("google.cloud"):
            raise ImportError("google cloud not available")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    cfg = GcpConfig(project_id="p")
    with pytest.raises(MissingDriverError):
        create_gcs_client(cfg)


def test_create_gcs_client_uses_storage_client_and_project():
    DummyClient = _install_fake_google_storage()

    cfg = GcpConfig(project_id="my-project")
    client = create_gcs_client(cfg)

    assert isinstance(client, DummyClient)
    assert client.project == "my-project"


def test_create_bigquery_client_missing_driver_raises(monkeypatch):
    # Force ImportError when attempting to import google.cloud.bigquery
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name.startswith("google.cloud"):
            raise ImportError("google bigquery not available")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    cfg = GcpConfig(project_id="p")
    with pytest.raises(MissingDriverError):
        create_bigquery_client(cfg)


def test_bigquery_helpers_use_stub_client_successfully_and_apply_kwargs():
    DummyStorageClient = _install_fake_google_storage()
    DummyBigQueryClient = _install_fake_google_bigquery()

    cfg = GcpConfig(project_id="proj")
    bq_client = create_bigquery_client(cfg)
    assert isinstance(bq_client, DummyBigQueryClient)

    # gcs_to_bq with extra config kwargs to exercise setattr loop
    result = gcs_to_bq(
        bq_client,
        table_id="proj.ds.tbl",
        source_uri="gs://bucket/file.csv",
        file_format="CSV",
        field_delimiter="|",
    )
    assert result == "load-done"
    _, _, job_config = bq_client.load_calls[0]
    assert getattr(job_config, "field_delimiter") == "|"

    # df_to_bq (inject fake pandas so import succeeds)
    fake_pandas = ModuleType("pandas")
    sys.modules["pandas"] = fake_pandas
    dummy_df = object()
    df_result = df_to_bq(bq_client, dummy_df, table_id="proj.ds.tbl2")
    assert df_result == "df-done"

    # bq_to_gcs with kwargs to exercise setattr loop
    extract_result = bq_to_gcs(
        bq_client,
        table_id="proj.ds.tbl",
        destination_uri="gs://bucket/out.csv",
        file_format="CSV",
        compression="GZIP",
    )
    assert extract_result == "extract-done"
    _, _, extract_config = bq_client.extract_calls[0]
    assert getattr(extract_config, "compression") == "GZIP"


def test_df_to_bq_missing_pandas_raises_missing_driver(monkeypatch):
    # Force ImportError when importing pandas
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "pandas":
            raise ImportError("pandas not available")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    DummyBigQueryClient = _install_fake_google_bigquery()
    client = DummyBigQueryClient(project="p")

    with pytest.raises(MissingDriverError):
        df_to_bq(client, object(), table_id="proj.ds.tbl")


def test_gcs_to_df_delegates_to_storage_gcs_to_pandas(monkeypatch):
    # Provide a fake gcs_to_pandas implementation
    calls = []

    def fake_gcs_to_pandas(client, uri, pandas_read_fn="read_csv", **kwargs):
        calls.append((client, uri, pandas_read_fn, kwargs))
        return "df"

    monkeypatch.setattr("aliframework.gcp.storage.gcs_to_pandas", fake_gcs_to_pandas)

    client = object()
    result = gcs_to_df(client, "gs://bucket/file.csv", pandas_read_fn="read_parquet", option=True)

    assert result == "df"
    assert calls[0][1] == "gs://bucket/file.csv"
    assert calls[0][2] == "read_parquet"
    assert calls[0][3]["option"] is True


def test_create_dataproc_client_missing_driver_raises(monkeypatch):
    # Force ImportError when attempting to import google.cloud.dataproc_v1
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name.startswith("google.cloud"):
            raise ImportError("google dataproc not available")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    cfg = GcpConfig(project_id="p")
    with pytest.raises(MissingDriverError):
        create_dataproc_client(cfg, region="us-central1")


def test_dataproc_and_dataflow_clients_success_and_pipelines():
    DummyJobControllerClient = _install_fake_google_dataproc()
    _install_fake_googleapiclient()

    cfg = GcpConfig(project_id="proj")

    # Dataproc client
    dp_client = create_dataproc_client(cfg, region="europe-west1")
    assert isinstance(dp_client, DummyJobControllerClient)

    # Dataflow client
    df_client = create_dataflow_client(cfg)

    # gcs_to_dataflow_to_bq launches a template
    result = gcs_to_dataflow_to_bq(
        config=cfg,
        template_path="gs://templates/my-template",
        parameters={"tempLocation": "gs://tmp"},
        region="us-central1",
        job_name="job-1",
    )
    assert "launched" in result

    # gcs_to_dataproc_to_bq submits a job
    op = gcs_to_dataproc_to_bq(
        config=cfg,
        region="us-central1",
        cluster_name="cluster",
        main_python_file_uri="gs://code/main.py",
        args=["--x=1"],
    )
    assert "job" in op


def test_create_dataflow_client_missing_driver_raises(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name.startswith("googleapiclient"):
            raise ImportError("googleapiclient not available")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    cfg = GcpConfig(project_id="p")
    with pytest.raises(MissingDriverError):
        create_dataflow_client(cfg)


class _DummyBlob:
    def __init__(self):
        self.upload_calls = []

    def download_as_bytes(self):
        return b"data"

    def upload_from_file(self, buf, rewind: bool):
        # Record that we were called and that the buffer is at position 0
        self.upload_calls.append((buf.read(), rewind))


class _DummyBucket:
    def __init__(self, name: str):
        self.name = name
        self.created_blobs: list[_DummyBlob] = []

    def blob(self, name: str):
        b = _DummyBlob()
        self.created_blobs.append(b)
        return b


class _DummyStorageClientForOps:
    def __init__(self):
        self.buckets: dict[str, _DummyBucket] = {}
        self.copy_calls = []

    def bucket(self, name: str):
        if name not in self.buckets:
            self.buckets[name] = _DummyBucket(name)
        return self.buckets[name]

    def copy_blob(self, src_blob: _DummyBlob, dest_bucket: _DummyBucket, dest_name: str):
        self.copy_calls.append((src_blob, dest_bucket, dest_name))


def test_gcs_to_gcs_happy_path_and_invalid_uri():
    client = _DummyStorageClientForOps()

    # Successful copy
    gcs_to_gcs(client, "gs://src-bucket/path/to/src.txt", "gs://dst-bucket/other/dst.txt")
    assert len(client.copy_calls) == 1
    src_blob, dest_bucket, dest_name = client.copy_calls[0]
    assert isinstance(src_blob, _DummyBlob)
    assert dest_bucket.name == "dst-bucket"
    assert dest_name == "other/dst.txt"

    # Non-GCS URI should raise
    with pytest.raises(ValueError):
        gcs_to_gcs(client, "http://not-gcs/file.txt", "gs://dst/file.txt")


def test_gcs_to_pandas_and_missing_pandas(monkeypatch):
    client = _DummyStorageClientForOps()

    # Provide fake pandas first for successful path
    class _FakePandas(ModuleType):
        def read_csv(self, buf, **kwargs):  # type: ignore[override]
            # Just ensure we can read from the buffer
            data = buf.read()
            return {"data": data, "kwargs": kwargs}

    fake_pd = _FakePandas("pandas")
    sys.modules["pandas"] = fake_pd

    result = gcs_to_pandas(client, "gs://bucket/file.csv", sep=";")
    assert result["data"] == b"data"
    assert result["kwargs"]["sep"] == ";"

    # Non-GCS URI should raise ValueError
    with pytest.raises(ValueError):
        gcs_to_pandas(client, "http://not-gcs/file.csv")

    # Now force ImportError to exercise MissingDriverError path
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "pandas":
            raise ImportError("pandas missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(MissingDriverError):
        gcs_to_pandas(client, "gs://bucket/file.csv")


def test_pandas_to_gcs_and_invalid_uri(monkeypatch):
    client = _DummyStorageClientForOps()

    # Successful path with fake pandas present
    sys.modules["pandas"] = ModuleType("pandas")

    class DummyDF:
        def __init__(self):
            self.calls = []

        def to_csv(self, buf, **kwargs):  # type: ignore[override]
            self.calls.append((buf, kwargs))
            buf.write(b"csvdata")

    df = DummyDF()
    pandas_to_gcs(client, df, "gs://bucket/out.csv")

    bucket = client.buckets["bucket"]
    blob = bucket.created_blobs[0]
    uploaded_data, rewind = blob.upload_calls[0]
    assert uploaded_data == b"csvdata"
    assert rewind is True

    # Non-GCS URI should raise
    with pytest.raises(ValueError):
        pandas_to_gcs(client, df, "http://not-gcs/out.csv")

    # Now force ImportError to exercise MissingDriverError path
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "pandas":
            raise ImportError("pandas missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(MissingDriverError):
        pandas_to_gcs(client, df, "gs://bucket/out2.csv")


def test_pyspark_df_to_gcs_and_missing_driver(monkeypatch):
    # Successful path with fake pyspark module and dummy df
    sys.modules["pyspark"] = ModuleType("pyspark")

    class DummyWriter:
        def __init__(self):
            self.calls = []

        def format(self, fmt):
            self.calls.append(("format", fmt))
            return self

        def options(self, **opts):
            self.calls.append(("options", opts))
            return self

        def mode(self, mode):
            self.calls.append(("mode", mode))
            return self

        def save(self, uri):
            self.calls.append(("save", uri))

    class DummyDF:
        def __init__(self):
            self.write = DummyWriter()

    df = DummyDF()
    pyspark_df_to_gcs(df, "gs://bucket/df", format="parquet", partitionBy="col1")
    assert ("save", "gs://bucket/df") in df.write.calls

    # Now force ImportError to exercise MissingDriverError path
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "pyspark":
            raise ImportError("pyspark not available")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(MissingDriverError):
        pyspark_df_to_gcs(df, "gs://bucket/df2")
