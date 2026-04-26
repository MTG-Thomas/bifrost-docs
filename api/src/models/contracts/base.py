"""Base classes for API contract models.

Provides common functionality for all public API response models:
- Automatic UUID-to-string serialization
- Automatic metadata_ → metadata field mapping
- Common fields (id, org_id, is_enabled, timestamps)
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class PublicEntityBase(BaseModel):
    """
    Base class for all public API response models.

    Features:
    - Automatic UUID-to-string serialization
    - Automatic metadata_ → metadata field mapping
    - Common fields (id, org_id, is_enabled, timestamps)

    Usage:
        class PasswordPublic(PublicEntityBase):
            name: str
            username: str | None = None
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    organization_id: UUID
    is_enabled: bool = True
    created_at: datetime
    updated_at: datetime
    metadata: dict = Field(default_factory=dict, validation_alias="metadata_")

    @field_serializer("id", "organization_id")
    def serialize_uuid(self, v: UUID) -> str:
        """Serialize UUID to string for JSON output."""
        return str(v)


class PublicOrganizationBase(BaseModel):
    """
    Base class for Organization public model (special case - no org_id field).

    Organization IS the organization, so it doesn't have an organization_id field.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    name: str
    is_enabled: bool = True
    created_at: datetime
    updated_at: datetime
    metadata: dict = Field(default_factory=dict, validation_alias="metadata_")

    @field_serializer("id")
    def serialize_uuid(self, v: UUID) -> str:
        """Serialize UUID to string for JSON output."""
        return str(v)
