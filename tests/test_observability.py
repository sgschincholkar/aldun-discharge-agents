import os
import pytest


def test_init_tracing_runs_without_error(monkeypatch):
    monkeypatch.setenv("ARIZE_API_KEY", "test-key")
    monkeypatch.setenv("ARIZE_SPACE_ID", "test-space-id")
    import importlib
    import observability
    importlib.reload(observability)
    # Should not raise
    observability.init_tracing()


def test_init_tracing_missing_api_key(monkeypatch):
    monkeypatch.delenv("ARIZE_API_KEY", raising=False)
    monkeypatch.setenv("ARIZE_SPACE_ID", "test-space-id")
    import importlib
    import observability
    importlib.reload(observability)
    with pytest.raises(EnvironmentError, match="ARIZE_API_KEY"):
        observability.init_tracing()


def test_init_tracing_missing_space_id(monkeypatch):
    monkeypatch.setenv("ARIZE_API_KEY", "test-key")
    monkeypatch.delenv("ARIZE_SPACE_ID", raising=False)
    import importlib
    import observability
    importlib.reload(observability)
    with pytest.raises(EnvironmentError, match="ARIZE_SPACE_ID"):
        observability.init_tracing()


def test_init_tracing_idempotent(monkeypatch):
    monkeypatch.setenv("ARIZE_API_KEY", "test-key")
    monkeypatch.setenv("ARIZE_SPACE_ID", "test-space-id")
    import importlib
    import observability
    importlib.reload(observability)
    # First call
    observability.init_tracing()
    # Second call should not raise and should return silently
    observability.init_tracing()


def test_app_imports_without_error(monkeypatch):
    """app.py must load without error even when Arize env vars are missing."""
    monkeypatch.delenv("ARIZE_API_KEY", raising=False)
    monkeypatch.delenv("ARIZE_SPACE_ID", raising=False)
    import importlib
    import app as app_module
    importlib.reload(app_module)
    assert app_module.app is not None
