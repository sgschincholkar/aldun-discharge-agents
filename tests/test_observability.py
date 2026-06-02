import os
import pytest


def test_init_tracing_runs_without_error(monkeypatch):
    monkeypatch.setenv("PHOENIX_API_KEY", "test-key")
    monkeypatch.setenv("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006/v1/traces")
    import importlib
    import observability
    importlib.reload(observability)
    # Should not raise
    observability.init_tracing()


def test_init_tracing_missing_api_key(monkeypatch):
    monkeypatch.delenv("PHOENIX_API_KEY", raising=False)
    monkeypatch.setenv("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006/v1/traces")
    import importlib
    import observability
    importlib.reload(observability)
    with pytest.raises(EnvironmentError, match="PHOENIX_API_KEY"):
        observability.init_tracing()


def test_init_tracing_missing_endpoint(monkeypatch):
    monkeypatch.setenv("PHOENIX_API_KEY", "test-key")
    monkeypatch.delenv("PHOENIX_COLLECTOR_ENDPOINT", raising=False)
    import importlib
    import observability
    importlib.reload(observability)
    with pytest.raises(EnvironmentError, match="PHOENIX_COLLECTOR_ENDPOINT"):
        observability.init_tracing()
