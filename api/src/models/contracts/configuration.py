"""Configuration contracts (API request/response schemas).

Includes contracts for:
- ConfigurationType
- ConfigurationStatus
- Configuration
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_serializer

from src.models.contracts.base import PublicEntityBase
from src.models.contracts.sync import SyncMetadata

# =============================================================================
# Configuration Type Contracts
# =============================================================================


class ConfigurationTypeCreate(BaseModel):
    """Configuration type creation request model."""

    name: str


class ConfigurationTypePublic(BaseModel):
    """Configuration type public response model (global, not org-scoped)."""

    id: UUID
    name: str
    is_active: bool
    created_at: datetime
    configuration_count: int = 0

    @field_serializer("id")
    def serialize_uuid(self, v: UUID) -> str:
        return str(v)


# =============================================================================
# Configuration Status Contracts
# =============================================================================


class ConfigurationStatusCreate(BaseModel):
    """Configuration status creation request model."""

    name: str


class ConfigurationStatusPublic(BaseModel):
    """Configuration status public response model (global, not org-scoped)."""

    id: UUID
    name: str
    is_active: bool
    created_at: datetime
    configuration_count: int = 0

    @field_serializer("id")
    def serialize_uuid(self, v: UUID) -> str:
        return str(v)


# =============================================================================
# Configuration Contracts
# =============================================================================


class ConfigurationCreate(BaseModel):
    """Configuration creation request model."""

    name: str
    configuration_type_id: str | None = None
    configuration_status_id: str | None = None
    serial_number: str | None = None
    asset_tag: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    ip_address: str | None = None
    mac_address: str | None = None
    notes: str | None = None
    metadata: dict | None = None
    sync_metadata: SyncMetadata | None = None
    interfaces: list | None = None
    is_enabled: bool | None = None  # Defaults to True if not provided


class ConfigurationUpdate(BaseModel):
    """Configuration update request model."""

    name: str | None = None
    configuration_type_id: str | None = None
    configuration_status_id: str | None = None
    serial_number: str | None = None
    asset_tag: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    ip_address: str | None = None
    mac_address: str | None = None
    notes: str | None = None
    metadata: dict | None = None
    sync_metadata: SyncMetadata | None = None
    interfaces: list | None = None
    is_enabled: bool | None = None  # Don't change if not provided


class ConfigurationPublic(PublicEntityBase):
    """Configuration public response model."""

    configuration_type_id: UUID | str | None = None
    configuration_status_id: UUID | str | None = None
    name: str
    serial_number: str | None = None
    asset_tag: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    ip_address: str | None = None
    mac_address: str | None = None
    notes: str | None = None
    sync_metadata: SyncMetadata | None = None
    interfaces: list = Field(default_factory=list)
    # Joined fields from relationships (not from ORM directly)
    configuration_type_name: str | None = None
    configuration_status_name: str | None = None
    updated_by_user_id: str | None = None
    updated_by_user_name: str | None = None

    @field_serializer("configuration_type_id", "configuration_status_id")
    def serialize_fk_uuid(self, v: UUID | None) -> str | None:
        """Serialize foreign key UUIDs to strings."""
        return str(v) if v else None
