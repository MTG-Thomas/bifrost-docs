"""Tests for sync provenance metadata contracts."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.models.contracts.configuration import ConfigurationPublic
from src.models.contracts.custom_asset import CustomAssetPublic
from src.models.contracts.sync import SyncMetadata, sync_metadata_to_storage


def test_sync_metadata_accepts_plan_fields() -> None:
    """Sync metadata stores the plan's source/provenance fields."""
    synced_at = datetime.now(UTC)

    metadata = SyncMetadata(
        source_system="itglue",
        source_tenant_id="tenant-123",
        external_id="config-456",
        last_synced_at=synced_at,
        sync_status="synced",
        sync_hash="sha256:abc123",
        source_url="https://example.test/configs/456",
    )

    assert metadata.source_system == "itglue"
    assert metadata.source_tenant_id == "tenant-123"
    assert metadata.external_id == "config-456"
    assert metadata.last_synced_at == synced_at
    assert metadata.sync_status == "synced"
    assert metadata.sync_hash == "sha256:abc123"
    assert metadata.source_url == "https://example.test/configs/456"


def test_sync_metadata_accepts_source_record_aliases() -> None:
    """Older source-record names are normalized to the Docs sync fields."""
    observed_at = datetime.now(UTC)

    metadata = SyncMetadata.model_validate(
        {
            "source_system": "bifrost",
            "source_tenant_id": "tenant-123",
            "source_record_id": "asset-789",
            "observed_at": observed_at,
            "sync_status": "observed",
            "payload_hash": "hash-from-payload",
        }
    )

    assert metadata.external_id == "asset-789"
    assert metadata.last_synced_at == observed_at
    assert metadata.sync_hash == "hash-from-payload"
    assert "source_record_id" not in metadata.model_dump()
    assert "observed_at" not in metadata.model_dump()
    assert "payload_hash" not in metadata.model_dump()


def test_sync_metadata_requires_identifying_fields() -> None:
    """A provenance record must identify the source, record, state, and hash."""
    with pytest.raises(ValidationError):
        SyncMetadata.model_validate({"source_system": "itglue"})


def test_sync_metadata_storage_shape_is_json_safe() -> None:
    """Sync metadata is stored with canonical field names and JSON-safe datetimes."""
    synced_at = datetime.now(UTC)

    metadata = SyncMetadata(
        source_system="itglue",
        source_tenant_id="tenant-123",
        external_id="config-456",
        last_synced_at=synced_at,
        sync_status="synced",
        sync_hash="sha256:abc123",
    )

    storage = sync_metadata_to_storage(metadata)

    assert storage == {
        "source_system": "itglue",
        "source_tenant_id": "tenant-123",
        "external_id": "config-456",
        "last_synced_at": synced_at.isoformat().replace("+00:00", "Z"),
        "sync_status": "synced",
        "sync_hash": "sha256:abc123",
        "source_url": None,
    }


def test_configuration_public_exposes_sync_metadata_from_orm_attribute() -> None:
    """Configuration responses expose non-secret sync provenance."""
    now = datetime.now(UTC)

    class FakeConfiguration:
        id = uuid4()
        organization_id = uuid4()
        configuration_type_id = None
        configuration_status_id = None
        name = "Firewall"
        serial_number = None
        asset_tag = None
        manufacturer = None
        model = None
        ip_address = None
        mac_address = None
        notes = None
        interfaces = []
        is_enabled = True
        created_at = now
        updated_at = now
        metadata_ = {}
        sync_metadata = {
            "source_system": "itglue",
            "source_tenant_id": "tenant-123",
            "external_id": "config-456",
            "last_synced_at": now,
            "sync_status": "synced",
            "sync_hash": "sha256:abc123",
        }

    public = ConfigurationPublic.model_validate(FakeConfiguration())

    assert public.sync_metadata is not None
    assert public.sync_metadata.external_id == "config-456"
    assert public.model_dump()["sync_metadata"]["source_system"] == "itglue"


def test_custom_asset_public_exposes_sync_metadata_from_orm_attribute() -> None:
    """Custom asset responses expose non-secret sync provenance."""
    now = datetime.now(UTC)

    class FakeCustomAsset:
        id = uuid4()
        organization_id = uuid4()
        custom_asset_type_id = str(uuid4())
        values = {"name": "Tenant"}
        is_enabled = True
        created_at = now
        updated_at = now
        metadata_ = {}
        sync_metadata = {
            "source_system": "halo",
            "source_tenant_id": "tenant-abc",
            "external_id": "asset-789",
            "last_synced_at": now,
            "sync_status": "synced",
            "sync_hash": "sha256:def456",
        }

    public = CustomAssetPublic.model_validate(FakeCustomAsset())

    assert public.sync_metadata is not None
    assert public.sync_metadata.source_system == "halo"
    assert public.model_dump()["sync_metadata"]["external_id"] == "asset-789"
