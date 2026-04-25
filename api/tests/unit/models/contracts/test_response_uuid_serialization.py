"""Response contract UUID serialization tests."""

from datetime import UTC, datetime
from uuid import uuid4

from src.models.contracts.configuration import (
    ConfigurationStatusPublic,
    ConfigurationTypePublic,
)
from src.models.contracts.custom_asset import CustomAssetTypePublic
from src.models.contracts.relationship import RelationshipPublic


def test_global_type_responses_accept_uuid_ids() -> None:
    """Global type response models should accept ORM UUID values."""
    type_id = uuid4()
    status_id = uuid4()
    now = datetime.now(UTC)

    config_type = ConfigurationTypePublic(
        id=type_id,
        name="Firewall",
        is_active=True,
        created_at=now,
    )
    config_status = ConfigurationStatusPublic(
        id=status_id,
        name="Active",
        is_active=True,
        created_at=now,
    )

    assert config_type.model_dump(mode="json")["id"] == str(type_id)
    assert config_status.model_dump(mode="json")["id"] == str(status_id)


def test_custom_asset_type_response_accepts_uuid_id() -> None:
    """Custom asset type response model should accept ORM UUID values."""
    type_id = uuid4()
    now = datetime.now(UTC)

    custom_asset_type = CustomAssetTypePublic(
        id=type_id,
        name="Licensing",
        fields=[],
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    assert custom_asset_type.model_dump(mode="json")["id"] == str(type_id)


def test_relationship_response_accepts_uuid_ids() -> None:
    """Relationship response model should accept ORM UUID values."""
    relationship_id = uuid4()
    org_id = uuid4()
    source_id = uuid4()
    target_id = uuid4()

    relationship = RelationshipPublic(
        id=relationship_id,
        organization_id=org_id,
        source_type="password",
        source_id=source_id,
        target_type="configuration",
        target_id=target_id,
        created_at=datetime.now(UTC),
    )

    dumped = relationship.model_dump(mode="json")
    assert dumped["id"] == str(relationship_id)
    assert dumped["organization_id"] == str(org_id)
    assert dumped["source_id"] == str(source_id)
    assert dumped["target_id"] == str(target_id)
