"""Azure Blob storage security contract tests."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.services.file_storage import FileStorageService


def _settings(**overrides):
    values = {
        "storage_backend": "azure_blob",
        "azure_blob_configured": True,
        "azure_storage_connection_string": "DefaultEndpointsProtocol=https;AccountName=testacct;AccountKey=testkey;EndpointSuffix=core.windows.net",
        "azure_storage_account_url": None,
        "azure_storage_account_key": None,
        "azure_blob_container": "attachments",
        "azure_blob_sas_expiry": 300,
        "azure_blob_download_sas_expiry": 120,
        "s3_configured": False,
        "s3_presigned_url_expiry": 900,
        "s3_download_url_expiry": 900,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.mark.asyncio
async def test_azure_upload_sas_uses_write_permission_and_short_expiry():
    service = FileStorageService(settings=_settings())

    with patch.object(service, "_generate_blob_sas_url", return_value="https://blob/upload") as sas:
        url = await service.generate_upload_url("org/document/file.txt", "text/plain")

    assert url == "https://blob/upload"
    sas.assert_called_once_with(
        "org/document/file.txt",
        expires_in=300,
        permission="w",
        content_type="text/plain",
    )


@pytest.mark.asyncio
async def test_azure_download_sas_uses_read_permission_and_content_disposition_filename():
    service = FileStorageService(settings=_settings())

    with patch.object(
        service, "_generate_blob_sas_url", return_value="https://blob/download"
    ) as sas:
        url = await service.generate_download_url("org/document/file.txt", filename="file.txt")

    assert url == "https://blob/download"
    sas.assert_called_once_with(
        "org/document/file.txt",
        expires_in=120,
        permission="r",
        filename="file.txt",
    )


@pytest.mark.asyncio
async def test_azure_delete_targets_private_configured_container():
    settings = _settings(azure_blob_container="private-attachments")
    service = FileStorageService(settings=settings)
    blob = MagicMock()
    blob_service = MagicMock()
    blob_service.get_blob_client.return_value = blob

    with patch.object(service, "_get_blob_service_client", return_value=blob_service):
        deleted = await service.delete_file("org/document/file.txt")

    assert deleted is True
    blob_service.get_blob_client.assert_called_once_with(
        container="private-attachments",
        blob="org/document/file.txt",
    )
    blob.delete_blob.assert_called_once_with(delete_snapshots="include")


@pytest.mark.asyncio
async def test_azure_container_creation_does_not_request_public_access():
    settings = _settings(azure_blob_container="private-attachments")
    service = FileStorageService(settings=settings)
    container = MagicMock()
    container.exists.return_value = False
    blob_service = MagicMock()
    blob_service.get_container_client.return_value = container

    with patch.object(service, "_get_blob_service_client", return_value=blob_service):
        ensured = await service.ensure_bucket_exists()

    assert ensured is True
    blob_service.get_container_client.assert_called_once_with("private-attachments")
    container.create_container.assert_called_once_with()
