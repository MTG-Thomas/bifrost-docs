"""
Location contracts (API request/response schemas).
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LocationCreate(BaseModel):
    """Location creation request model."""

    name: str = Field(..., min_length=1, max_length=255)
    notes: str | None = None
    metadata: dict | None = None
    is_enabled: bool | None = None  # Defaults to True if not provided
    address_1: str | None = Field(None, max_length=255)
    address_2: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    region: str | None = Field(None, max_length=100)
    postal_code: str | None = Field(None, max_length=20)
    country: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=50)


class LocationUpdate(BaseModel):
    """Location update request model."""

    name: str | None = Field(None, min_length=1, max_length=255)
    notes: str | None = None
    metadata: dict | None = None
    is_enabled: bool | None = None  # Don't change if not provided
    address_1: str | None = Field(None, max_length=255)
    address_2: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    region: str | None = Field(None, max_length=100)
    postal_code: str | None = Field(None, max_length=20)
    country: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=50)


class LocationPublic(BaseModel):
    """Location public response model."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    name: str
    notes: str | None
    metadata: dict = Field(default_factory=dict)
    is_enabled: bool = True
    address_1: str | None = None
    address_2: str | None = None
    city: str | None = None
    region: str | None = None
    postal_code: str | None = None
    country: str | None = None
    phone: str | None = None
    created_at: datetime
    updated_at: datetime
    updated_by_user_id: str | None = None
    updated_by_user_name: str | None = None
