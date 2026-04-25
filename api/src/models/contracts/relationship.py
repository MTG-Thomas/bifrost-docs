"""
Relationship contracts (API request/response schemas).
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class RelationshipCreate(BaseModel):
    """Relationship creation request model."""

    source_type: str = Field(
        ...,
        description="Entity type: password, configuration, location, document, custom_asset",
    )
    source_id: str = Field(..., description="Source entity UUID")
    target_type: str = Field(
        ...,
        description="Entity type: password, configuration, location, document, custom_asset",
    )
    target_id: str = Field(..., description="Target entity UUID")


class RelationshipPublic(BaseModel):
    """Relationship public response model."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    source_type: str
    source_id: UUID
    target_type: str
    target_id: UUID
    created_at: datetime

    @field_serializer("id", "organization_id", "source_id", "target_id")
    def serialize_uuid(self, v: UUID) -> str:
        return str(v)


class RelatedEntity(BaseModel):
    """Resolved entity info for display."""

    relationship_id: str
    entity_type: str
    entity_id: str
    name: str


class RelatedItemsResponse(BaseModel):
    """Response containing resolved related entities."""

    items: list[RelatedEntity]
