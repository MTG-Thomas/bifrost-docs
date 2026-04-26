"""Tests for storage backend and rate-limiting configuration."""

import importlib

from src.config import Settings


def test_storage_configured_uses_s3_backend_by_default():
    settings = Settings(secret_key="x" * 32, s3_access_key="key", s3_secret_key="secret")

    assert settings.storage_backend == "s3"
    assert settings.s3_configured is True
    assert settings.storage_configured is True


def test_storage_configured_uses_azure_blob_backend():
    settings = Settings(
        secret_key="x" * 32,
        storage_backend="azure_blob",
        azure_storage_account_url="https://docsproof.blob.core.windows.net",
        azure_storage_account_key="account-key",
    )

    assert settings.azure_blob_configured is True
    assert settings.storage_configured is True


def test_storage_configured_is_false_for_incomplete_azure_blob_backend():
    settings = Settings(
        secret_key="x" * 32,
        storage_backend="azure_blob",
        azure_storage_account_url="https://docsproof.blob.core.windows.net",
    )

    assert settings.azure_blob_configured is False
    assert settings.storage_configured is False


def test_rate_limiting_can_be_disabled(monkeypatch):
    monkeypatch.setenv("BIFROST_DOCS_SECRET_KEY", "x" * 32)
    monkeypatch.setenv("BIFROST_DOCS_RATE_LIMITING_ENABLED", "false")

    import src.config as config
    import src.core.rate_limiting as rate_limiting

    config.clear_settings_cache()
    reloaded = importlib.reload(rate_limiting)

    assert reloaded.RATE_LIMITING_ENABLED is False
    assert reloaded.limiter.middleware_class is None


def test_noop_limiter_decorator_returns_original_function():
    import src.core.rate_limiting as rate_limiting

    limiter = rate_limiting._NoOpLimiter()

    def endpoint():
        return "ok"

    assert limiter.limit("1/minute")(endpoint) is endpoint
