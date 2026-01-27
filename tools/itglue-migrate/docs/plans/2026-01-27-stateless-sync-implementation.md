# Stateless Sync Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the stateful `preview`/`run` migration commands with a single stateless `sync` command that uses API metadata as the source of truth.

**Architecture:** The sync command fetches existing entities from the API (filtering by `metadata.itglue_id`), compares against CSV export data, and creates/updates only what's missing. No plan file or state file needed.

**Tech Stack:** Python 3.11+, Typer CLI, httpx async client, Pydantic, pytest

---

## Phase 1: Location Schema (API)

### Task 1.1: Create Alembic Migration for Location Fields

**Files:**
- Create: `api/alembic/versions/20260127_100000_add_location_address_fields.py`

**Step 1: Generate migration file**

```bash
cd /Users/jack/GitHub/bifrost-docs/api
source .venv/bin/activate
alembic revision -m "add_location_address_fields"
```

Then rename to `20260127_100000_add_location_address_fields.py`.

**Step 2: Write migration content**

```python
"""Add address fields to locations table

Revision ID: 20260127_100000
Revises: 20260126_001000
Create Date: 2026-01-27
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260127_100000"
down_revision: str | None = "20260126_001000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add address fields to locations table."""
    op.add_column("locations", sa.Column("address_1", sa.String(255), nullable=True))
    op.add_column("locations", sa.Column("address_2", sa.String(255), nullable=True))
    op.add_column("locations", sa.Column("city", sa.String(100), nullable=True))
    op.add_column("locations", sa.Column("region", sa.String(100), nullable=True))
    op.add_column("locations", sa.Column("postal_code", sa.String(20), nullable=True))
    op.add_column("locations", sa.Column("country", sa.String(100), nullable=True))
    op.add_column("locations", sa.Column("phone", sa.String(50), nullable=True))


def downgrade() -> None:
    """Remove address fields from locations table."""
    op.drop_column("locations", "phone")
    op.drop_column("locations", "country")
    op.drop_column("locations", "postal_code")
    op.drop_column("locations", "region")
    op.drop_column("locations", "city")
    op.drop_column("locations", "address_2")
    op.drop_column("locations", "address_1")
```

**Step 3: Run migration locally**

```bash
cd /Users/jack/GitHub/bifrost-docs/api
alembic upgrade head
```

**Step 4: Commit**

```bash
git add api/alembic/versions/20260127_100000_add_location_address_fields.py
git commit -m "feat(api): add address fields to locations table"
```

---

### Task 1.2: Update Location ORM Model

**Files:**
- Modify: `api/src/models/orm/location.py`

**Step 1: Add new columns to Location model**

Add after line 34 (`notes` field):

```python
    address_1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
```

**Step 2: Run type check**

```bash
cd /Users/jack/GitHub/bifrost-docs/api
pyright src/models/orm/location.py
```

Expected: No errors

**Step 3: Commit**

```bash
git add api/src/models/orm/location.py
git commit -m "feat(api): add address fields to Location ORM model"
```

---

### Task 1.3: Update Location API Contracts

**Files:**
- Modify: `api/src/models/contracts/location.py`

**Step 1: Update LocationCreate**

Replace the class with:

```python
class LocationCreate(BaseModel):
    """Location creation request model."""

    name: str = Field(..., min_length=1, max_length=255)
    address_1: str | None = Field(None, max_length=255)
    address_2: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    region: str | None = Field(None, max_length=100)
    postal_code: str | None = Field(None, max_length=20)
    country: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=50)
    notes: str | None = None
    metadata: dict | None = None
    is_enabled: bool | None = None
```

**Step 2: Update LocationUpdate**

Replace the class with:

```python
class LocationUpdate(BaseModel):
    """Location update request model."""

    name: str | None = Field(None, min_length=1, max_length=255)
    address_1: str | None = Field(None, max_length=255)
    address_2: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    region: str | None = Field(None, max_length=100)
    postal_code: str | None = Field(None, max_length=20)
    country: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=50)
    notes: str | None = None
    metadata: dict | None = None
    is_enabled: bool | None = None
```

**Step 3: Update LocationPublic**

Replace the class with:

```python
class LocationPublic(BaseModel):
    """Location public response model."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    name: str
    address_1: str | None = None
    address_2: str | None = None
    city: str | None = None
    region: str | None = None
    postal_code: str | None = None
    country: str | None = None
    phone: str | None = None
    notes: str | None = None
    metadata: dict = Field(default_factory=dict)
    is_enabled: bool = True
    created_at: datetime
    updated_at: datetime
    updated_by_user_id: str | None = None
    updated_by_user_name: str | None = None
```

**Step 4: Run type check**

```bash
cd /Users/jack/GitHub/bifrost-docs/api
pyright src/models/contracts/location.py
```

Expected: No errors

**Step 5: Commit**

```bash
git add api/src/models/contracts/location.py
git commit -m "feat(api): add address fields to Location contracts"
```

---

### Task 1.4: Update Location Router

**Files:**
- Modify: `api/src/routers/locations.py`

**Step 1: Update _location_to_public helper**

Find the `_location_to_public` function and add the new fields to the return:

```python
def _location_to_public(location: Location) -> LocationPublic:
    """Convert Location ORM model to public response."""
    return LocationPublic(
        id=str(location.id),
        organization_id=str(location.organization_id),
        name=location.name,
        address_1=location.address_1,
        address_2=location.address_2,
        city=location.city,
        region=location.region,
        postal_code=location.postal_code,
        country=location.country,
        phone=location.phone,
        notes=location.notes,
        metadata=location.metadata_ if isinstance(location.metadata_, dict) else {},
        is_enabled=location.is_enabled,
        created_at=location.created_at,
        updated_at=location.updated_at,
        updated_by_user_id=str(location.updated_by_user_id) if location.updated_by_user_id else None,
        updated_by_user_name=location.updated_by_user.email if location.updated_by_user else None,
    )
```

**Step 2: Update create_location endpoint**

In the `create_location` function, update the Location instantiation:

```python
    location = Location(
        organization_id=org_id,
        name=data.name,
        address_1=data.address_1,
        address_2=data.address_2,
        city=data.city,
        region=data.region,
        postal_code=data.postal_code,
        country=data.country,
        phone=data.phone,
        notes=data.notes,
        metadata_=data.metadata,
        is_enabled=data.is_enabled if data.is_enabled is not None else True,
    )
```

**Step 3: Update update_location endpoint**

In the `update_location` function, add handling for new fields after existing field updates:

```python
    if data.address_1 is not None:
        location.address_1 = data.address_1
    if data.address_2 is not None:
        location.address_2 = data.address_2
    if data.city is not None:
        location.city = data.city
    if data.region is not None:
        location.region = data.region
    if data.postal_code is not None:
        location.postal_code = data.postal_code
    if data.country is not None:
        location.country = data.country
    if data.phone is not None:
        location.phone = data.phone
```

**Step 4: Update get_location_preview**

Update the preview content builder to use actual fields:

```python
    # Build address string
    address_parts = []
    if location.address_1:
        address_parts.append(location.address_1)
    if location.address_2:
        address_parts.append(location.address_2)

    city_parts = []
    if location.city:
        city_parts.append(location.city)
    if location.region:
        city_parts.append(location.region)
    if location.postal_code:
        city_parts.append(location.postal_code)

    if address_parts:
        content_parts.append(f"\n**Address:** {', '.join(address_parts)}")
    if city_parts:
        content_parts.append(f"\n**City:** {' '.join(city_parts)}")
    if location.country:
        content_parts.append(f"\n**Country:** {location.country}")
    if location.phone:
        content_parts.append(f"\n**Phone:** {location.phone}")
```

**Step 5: Run tests and type check**

```bash
cd /Users/jack/GitHub/bifrost-docs/api
pyright src/routers/locations.py
pytest tests/ -k location -v
```

**Step 6: Commit**

```bash
git add api/src/routers/locations.py
git commit -m "feat(api): handle address fields in Location router"
```

---

### Task 1.5: Update Migration Tool API Client

**Files:**
- Modify: `tools/itglue-migrate/src/itglue_migrate/api_client.py`

**Step 1: Update create_location method signature**

Find `async def create_location` and update to:

```python
    async def create_location(
        self,
        org_id: str | UUID,
        name: str,
        address_1: str | None = None,
        address_2: str | None = None,
        city: str | None = None,
        region: str | None = None,
        postal_code: str | None = None,
        country: str | None = None,
        phone: str | None = None,
        notes: str | None = None,
        metadata: dict[str, Any] | None = None,
        is_enabled: bool = True,
    ) -> dict[str, Any]:
        """
        Create a new location.

        Args:
            org_id: Organization UUID
            name: Location name
            address_1: Address line 1
            address_2: Address line 2
            city: City
            region: State/province/region
            postal_code: Postal/ZIP code
            country: Country
            phone: Phone number
            notes: Location notes
            metadata: External system metadata
            is_enabled: Whether the location is enabled

        Returns:
            Created location object
        """
        payload: dict[str, Any] = {
            "name": name,
            "is_enabled": is_enabled,
        }
        if address_1 is not None:
            payload["address_1"] = address_1
        if address_2 is not None:
            payload["address_2"] = address_2
        if city is not None:
            payload["city"] = city
        if region is not None:
            payload["region"] = region
        if postal_code is not None:
            payload["postal_code"] = postal_code
        if country is not None:
            payload["country"] = country
        if phone is not None:
            payload["phone"] = phone
        if notes is not None:
            payload["notes"] = notes
        if metadata is not None:
            payload["metadata"] = metadata

        return await self._request(
            "POST",
            f"/api/organizations/{org_id}/locations",
            json=payload,
        )
```

**Step 2: Run type check**

```bash
cd /Users/jack/GitHub/bifrost-docs/tools/itglue-migrate
pyright src/itglue_migrate/api_client.py
```

**Step 3: Commit**

```bash
git add tools/itglue-migrate/src/itglue_migrate/api_client.py
git commit -m "feat(migrate): update API client for location address fields"
```

---

### Task 1.6: Update Location Import in Migration Tool

**Files:**
- Modify: `tools/itglue-migrate/src/itglue_migrate/importers.py`

**Step 1: Update import_locations method**

Find the `import_locations` method and replace the location creation logic. Remove the `format_location_notes_html` usage and pass fields directly:

```python
                # Create location via API with address fields
                metadata = {"itglue_id": itglue_id}

                result = await self.client.create_location(
                    org_id=org_uuid,
                    name=location_name,
                    address_1=location.get("address_1"),
                    address_2=location.get("address_2"),
                    city=location.get("city"),
                    region=location.get("region"),
                    postal_code=location.get("postal_code"),
                    country=location.get("country"),
                    phone=location.get("phone"),
                    notes=None,  # No longer stuffing address into notes
                    metadata=metadata,
                )
```

**Step 2: Run tests**

```bash
cd /Users/jack/GitHub/bifrost-docs/tools/itglue-migrate
pytest tests/unit/test_importers.py -v
```

**Step 3: Commit**

```bash
git add tools/itglue-migrate/src/itglue_migrate/importers.py
git commit -m "feat(migrate): use location address fields instead of notes"
```

---

## Phase 2: Core Sync Command

### Task 2.1: Create State Fetcher Module

**Files:**
- Create: `tools/itglue-migrate/src/itglue_migrate/state_fetcher.py`
- Create: `tools/itglue-migrate/tests/unit/test_state_fetcher.py`

**Step 1: Write the failing test**

```python
"""Tests for state_fetcher module."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from itglue_migrate.state_fetcher import StateFetcher, ExistingState


@pytest.fixture
def mock_client():
    """Create a mock API client."""
    client = MagicMock()
    client.list_organizations = AsyncMock(return_value=[
        {"id": "uuid-1", "name": "Acme Corp", "metadata": {"itglue_id": "123"}},
        {"id": "uuid-2", "name": "Beta Inc", "metadata": {}},
    ])
    client.list_configurations = AsyncMock(return_value={
        "items": [
            {"id": "cfg-1", "name": "Server 1", "metadata": {"itglue_id": "456"}},
        ],
        "total": 1,
    })
    return client


@pytest.mark.asyncio
async def test_fetch_organizations_builds_lookup(mock_client):
    """StateFetcher builds lookup by itglue_id and name."""
    fetcher = StateFetcher(mock_client)
    state = await fetcher.fetch_for_org("uuid-1")

    # Should have org lookup
    assert state.org_by_itglue_id.get("123") == "uuid-1"
    assert state.org_by_name.get("acme corp") == "uuid-1"


@pytest.mark.asyncio
async def test_fetch_configurations_paginates(mock_client):
    """StateFetcher paginates through all configurations."""
    fetcher = StateFetcher(mock_client)
    state = await fetcher.fetch_for_org("uuid-1")

    assert state.config_by_itglue_id.get("456") == "cfg-1"
```

**Step 2: Run test to verify it fails**

```bash
cd /Users/jack/GitHub/bifrost-docs/tools/itglue-migrate
pytest tests/unit/test_state_fetcher.py -v
```

Expected: FAIL with "No module named 'itglue_migrate.state_fetcher'"

**Step 3: Write implementation**

```python
"""State fetcher - retrieves existing state from API.

This module fetches all existing entities from the BifrostDocs API
and builds lookup tables by metadata.itglue_id for comparison with
CSV export data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from itglue_migrate.api_client import BifrostDocsClient


@dataclass
class ExistingState:
    """Container for existing entity state fetched from API."""

    # Organization lookups
    org_by_itglue_id: dict[str, str] = field(default_factory=dict)
    org_by_name: dict[str, str] = field(default_factory=dict)

    # Entity lookups by itglue_id -> uuid
    config_by_itglue_id: dict[str, str] = field(default_factory=dict)
    config_type_by_name: dict[str, str] = field(default_factory=dict)
    config_status_by_name: dict[str, str] = field(default_factory=dict)
    location_by_itglue_id: dict[str, str] = field(default_factory=dict)
    document_by_itglue_id: dict[str, str] = field(default_factory=dict)
    password_by_itglue_id: dict[str, str] = field(default_factory=dict)
    custom_asset_type_by_name: dict[str, str] = field(default_factory=dict)
    custom_asset_by_itglue_id: dict[str, str] = field(default_factory=dict)

    # Full entity data for update comparisons
    configs: dict[str, dict[str, Any]] = field(default_factory=dict)
    locations: dict[str, dict[str, Any]] = field(default_factory=dict)
    documents: dict[str, dict[str, Any]] = field(default_factory=dict)
    passwords: dict[str, dict[str, Any]] = field(default_factory=dict)
    custom_assets: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Relationships: set of "source_type:source_id:target_type:target_id"
    relationships: set[str] = field(default_factory=set)


class StateFetcher:
    """Fetches existing state from API for comparison."""

    def __init__(self, client: BifrostDocsClient):
        self.client = client

    async def fetch_all_orgs(self) -> ExistingState:
        """Fetch all organizations and build lookup."""
        state = ExistingState()

        orgs = await self.client.list_organizations()
        for org in orgs:
            org_id = org.get("id")
            name = org.get("name", "").lower()
            metadata = org.get("metadata", {})
            itglue_id = metadata.get("itglue_id")

            if itglue_id:
                state.org_by_itglue_id[str(itglue_id)] = org_id
            if name:
                state.org_by_name[name] = org_id

        return state

    async def fetch_for_org(self, org_id: str) -> ExistingState:
        """Fetch all entities for a specific organization."""
        state = await self.fetch_all_orgs()

        # Fetch configuration types (global)
        await self._fetch_config_types(state)

        # Fetch configuration statuses (global)
        await self._fetch_config_statuses(state)

        # Fetch custom asset types (global)
        await self._fetch_custom_asset_types(state)

        # Fetch org-scoped entities
        await self._fetch_configurations(state, org_id)
        await self._fetch_locations(state, org_id)
        await self._fetch_documents(state, org_id)
        await self._fetch_passwords(state, org_id)
        await self._fetch_custom_assets(state, org_id)
        await self._fetch_relationships(state, org_id)

        return state

    async def _fetch_config_types(self, state: ExistingState) -> None:
        """Fetch all configuration types."""
        types = await self.client.list_configuration_types()
        for ct in types:
            name = ct.get("name", "").lower()
            if name:
                state.config_type_by_name[name] = ct.get("id")

    async def _fetch_config_statuses(self, state: ExistingState) -> None:
        """Fetch all configuration statuses."""
        statuses = await self.client.list_configuration_statuses()
        for cs in statuses:
            name = cs.get("name", "").lower()
            if name:
                state.config_status_by_name[name] = cs.get("id")

    async def _fetch_custom_asset_types(self, state: ExistingState) -> None:
        """Fetch all custom asset types."""
        types = await self.client.list_custom_asset_types()
        for cat in types:
            name = cat.get("name", "").lower()
            if name:
                state.custom_asset_type_by_name[name] = cat.get("id")

    async def _paginate_all(
        self,
        fetch_fn,
        org_id: str,
        **kwargs,
    ) -> list[dict[str, Any]]:
        """Paginate through all results from a list endpoint."""
        all_items = []
        offset = 0
        limit = 100

        while True:
            result = await fetch_fn(org_id, limit=limit, offset=offset, **kwargs)
            items = result.get("items", [])
            all_items.extend(items)

            if len(items) < limit:
                break
            offset += limit

        return all_items

    async def _fetch_configurations(self, state: ExistingState, org_id: str) -> None:
        """Fetch all configurations for an org."""
        items = await self._paginate_all(
            self.client.list_configurations,
            org_id,
            show_disabled=True,
        )
        for item in items:
            metadata = item.get("metadata", {})
            itglue_id = metadata.get("itglue_id")
            item_id = item.get("id")

            if itglue_id:
                state.config_by_itglue_id[str(itglue_id)] = item_id
            state.configs[item_id] = item

    async def _fetch_locations(self, state: ExistingState, org_id: str) -> None:
        """Fetch all locations for an org."""
        items = await self._paginate_all(
            self.client.list_locations,
            org_id,
            show_disabled=True,
        )
        for item in items:
            metadata = item.get("metadata", {})
            itglue_id = metadata.get("itglue_id")
            item_id = item.get("id")

            if itglue_id:
                state.location_by_itglue_id[str(itglue_id)] = item_id
            state.locations[item_id] = item

    async def _fetch_documents(self, state: ExistingState, org_id: str) -> None:
        """Fetch all documents for an org."""
        items = await self._paginate_all(
            self.client.list_documents,
            org_id,
            show_disabled=True,
        )
        for item in items:
            metadata = item.get("metadata", {})
            itglue_id = metadata.get("itglue_id")
            item_id = item.get("id")

            if itglue_id:
                state.document_by_itglue_id[str(itglue_id)] = item_id
            state.documents[item_id] = item

    async def _fetch_passwords(self, state: ExistingState, org_id: str) -> None:
        """Fetch all passwords for an org."""
        items = await self._paginate_all(
            self.client.list_passwords,
            org_id,
            show_disabled=True,
        )
        for item in items:
            metadata = item.get("metadata", {})
            itglue_id = metadata.get("itglue_id")
            item_id = item.get("id")

            if itglue_id:
                state.password_by_itglue_id[str(itglue_id)] = item_id
            state.passwords[item_id] = item

    async def _fetch_custom_assets(self, state: ExistingState, org_id: str) -> None:
        """Fetch all custom assets for an org (across all types)."""
        # Need to fetch for each custom asset type
        for type_name, type_id in state.custom_asset_type_by_name.items():
            items = await self._paginate_all(
                self.client.list_custom_assets,
                org_id,
                type_id=type_id,
                show_disabled=True,
            )
            for item in items:
                metadata = item.get("metadata", {})
                itglue_id = metadata.get("itglue_id")
                item_id = item.get("id")

                if itglue_id:
                    state.custom_asset_by_itglue_id[str(itglue_id)] = item_id
                state.custom_assets[item_id] = item

    async def _fetch_relationships(self, state: ExistingState, org_id: str) -> None:
        """Fetch relationships for all passwords in org."""
        for password_id in state.passwords:
            try:
                rels = await self.client.list_relationships(
                    org_id,
                    entity_type="password",
                    entity_id=password_id,
                )
                for rel in rels:
                    # Build relationship key
                    key = f"password:{password_id}:{rel.get('target_type')}:{rel.get('target_id')}"
                    state.relationships.add(key)
            except Exception:
                # Continue if relationship fetch fails
                pass
```

**Step 4: Run tests to verify they pass**

```bash
cd /Users/jack/GitHub/bifrost-docs/tools/itglue-migrate
pytest tests/unit/test_state_fetcher.py -v
```

**Step 5: Commit**

```bash
git add tools/itglue-migrate/src/itglue_migrate/state_fetcher.py
git add tools/itglue-migrate/tests/unit/test_state_fetcher.py
git commit -m "feat(migrate): add StateFetcher for API state retrieval"
```

---

### Task 2.2: Create Sync Differ Module

**Files:**
- Create: `tools/itglue-migrate/src/itglue_migrate/sync_differ.py`
- Create: `tools/itglue-migrate/tests/unit/test_sync_differ.py`

**Step 1: Write the failing test**

```python
"""Tests for sync_differ module."""

import pytest

from itglue_migrate.sync_differ import SyncDiffer, SyncPlan
from itglue_migrate.state_fetcher import ExistingState


def test_diff_finds_missing_configurations():
    """SyncDiffer identifies configs in CSV but not in API."""
    state = ExistingState()
    state.config_by_itglue_id["123"] = "uuid-existing"

    csv_configs = [
        {"id": "123", "name": "Existing Server"},
        {"id": "456", "name": "New Server"},
    ]

    differ = SyncDiffer(state)
    plan = differ.diff_configurations(csv_configs)

    assert len(plan.to_create) == 1
    assert plan.to_create[0]["id"] == "456"
    assert len(plan.existing) == 1


def test_diff_finds_missing_relationships():
    """SyncDiffer identifies relationships to create."""
    state = ExistingState()
    state.password_by_itglue_id["pwd-1"] = "pwd-uuid-1"
    state.config_by_itglue_id["cfg-1"] = "cfg-uuid-1"
    # No existing relationship

    csv_passwords = [
        {
            "id": "pwd-1",
            "name": "Admin Password",
            "resource_type": "Configuration",
            "resource_id": "cfg-1",
        },
    ]

    differ = SyncDiffer(state)
    plan = differ.diff_relationships(csv_passwords)

    assert len(plan.to_create) == 1
    assert plan.to_create[0]["source_id"] == "pwd-uuid-1"
    assert plan.to_create[0]["target_id"] == "cfg-uuid-1"
```

**Step 2: Run test to verify it fails**

```bash
cd /Users/jack/GitHub/bifrost-docs/tools/itglue-migrate
pytest tests/unit/test_sync_differ.py::test_diff_finds_missing_configurations -v
```

Expected: FAIL with "No module named 'itglue_migrate.sync_differ'"

**Step 3: Write implementation**

```python
"""Sync differ - compares CSV data against API state.

This module compares parsed CSV export data against the existing
state fetched from the API and produces a plan of what needs to
be created, updated, or skipped.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from itglue_migrate.state_fetcher import ExistingState


@dataclass
class EntityPlan:
    """Plan for a single entity type."""

    to_create: list[dict[str, Any]] = field(default_factory=list)
    to_update: list[dict[str, Any]] = field(default_factory=list)
    existing: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class RelationshipPlan:
    """Plan for relationships."""

    to_create: list[dict[str, Any]] = field(default_factory=list)
    existing: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class PasswordPlan:
    """Plan for passwords including embedded handling."""

    to_create: list[dict[str, Any]] = field(default_factory=list)
    to_update: list[dict[str, Any]] = field(default_factory=list)
    existing: list[dict[str, Any]] = field(default_factory=list)
    cell_writes: list[dict[str, Any]] = field(default_factory=list)  # ::Cell
    row_creates: list[dict[str, Any]] = field(default_factory=list)  # ::Row


@dataclass
class SyncPlan:
    """Complete sync plan for an organization."""

    organizations: EntityPlan = field(default_factory=EntityPlan)
    config_types: EntityPlan = field(default_factory=EntityPlan)
    config_statuses: EntityPlan = field(default_factory=EntityPlan)
    custom_asset_types: EntityPlan = field(default_factory=EntityPlan)
    locations: EntityPlan = field(default_factory=EntityPlan)
    configurations: EntityPlan = field(default_factory=EntityPlan)
    custom_assets: EntityPlan = field(default_factory=EntityPlan)
    documents: EntityPlan = field(default_factory=EntityPlan)
    passwords: PasswordPlan = field(default_factory=PasswordPlan)
    relationships: RelationshipPlan = field(default_factory=RelationshipPlan)


class SyncDiffer:
    """Compares CSV data against API state to produce sync plan."""

    def __init__(self, state: ExistingState):
        self.state = state

    def diff_configurations(self, csv_configs: list[dict[str, Any]]) -> EntityPlan:
        """Diff configurations between CSV and API state."""
        plan = EntityPlan()

        for config in csv_configs:
            itglue_id = str(config.get("id", ""))
            if not itglue_id:
                continue

            if itglue_id in self.state.config_by_itglue_id:
                plan.existing.append(config)
            else:
                plan.to_create.append(config)

        return plan

    def diff_locations(self, csv_locations: list[dict[str, Any]]) -> EntityPlan:
        """Diff locations between CSV and API state."""
        plan = EntityPlan()

        for location in csv_locations:
            itglue_id = str(location.get("id", ""))
            if not itglue_id:
                continue

            if itglue_id in self.state.location_by_itglue_id:
                plan.existing.append(location)
            else:
                plan.to_create.append(location)

        return plan

    def diff_documents(self, csv_documents: list[dict[str, Any]]) -> EntityPlan:
        """Diff documents between CSV and API state."""
        plan = EntityPlan()

        for doc in csv_documents:
            itglue_id = str(doc.get("id", ""))
            if not itglue_id:
                continue

            if itglue_id in self.state.document_by_itglue_id:
                plan.existing.append(doc)
            else:
                plan.to_create.append(doc)

        return plan

    def diff_passwords(self, csv_passwords: list[dict[str, Any]]) -> PasswordPlan:
        """Diff passwords, handling ::Cell and ::Row specially."""
        plan = PasswordPlan()

        for pwd in csv_passwords:
            itglue_id = str(pwd.get("id", ""))
            if not itglue_id:
                continue

            resource_type = (pwd.get("resource_type") or "").lower()

            # Handle ::Cell - write to custom asset field
            if "structureddata::cell" in resource_type:
                plan.cell_writes.append(pwd)
                continue

            # Handle ::Row - create password + relationship
            if "structureddata::row" in resource_type:
                if itglue_id not in self.state.password_by_itglue_id:
                    plan.row_creates.append(pwd)
                else:
                    plan.existing.append(pwd)
                continue

            # Regular password
            if itglue_id in self.state.password_by_itglue_id:
                plan.existing.append(pwd)
            else:
                plan.to_create.append(pwd)

        return plan

    def diff_custom_assets(self, csv_assets: list[dict[str, Any]]) -> EntityPlan:
        """Diff custom assets between CSV and API state."""
        plan = EntityPlan()

        for asset in csv_assets:
            itglue_id = str(asset.get("id", ""))
            if not itglue_id:
                continue

            if itglue_id in self.state.custom_asset_by_itglue_id:
                plan.existing.append(asset)
            else:
                plan.to_create.append(asset)

        return plan

    def diff_config_types(self, csv_configs: list[dict[str, Any]]) -> EntityPlan:
        """Extract unique config types and diff against existing."""
        plan = EntityPlan()
        seen = set()

        for config in csv_configs:
            type_name = config.get("configuration_type")
            if not type_name or type_name.lower() in seen:
                continue
            seen.add(type_name.lower())

            if type_name.lower() in self.state.config_type_by_name:
                plan.existing.append({"name": type_name})
            else:
                plan.to_create.append({"name": type_name})

        return plan

    def diff_relationships(self, csv_passwords: list[dict[str, Any]]) -> RelationshipPlan:
        """Identify relationships to create from password resource links."""
        plan = RelationshipPlan()

        for pwd in csv_passwords:
            resource_type = (pwd.get("resource_type") or "").lower()
            resource_id = str(pwd.get("resource_id") or "")
            itglue_id = str(pwd.get("id", ""))

            if not resource_type or not resource_id:
                continue

            # Skip ::Cell - handled separately
            if "structureddata::cell" in resource_type:
                continue

            # Get password UUID
            password_uuid = self.state.password_by_itglue_id.get(itglue_id)
            if not password_uuid:
                continue

            # Determine target type and UUID
            target_type = None
            target_uuid = None

            if resource_type == "configuration":
                target_type = "configuration"
                target_uuid = self.state.config_by_itglue_id.get(resource_id)
            elif resource_type == "location":
                target_type = "location"
                target_uuid = self.state.location_by_itglue_id.get(resource_id)
            elif resource_type == "document":
                target_type = "document"
                target_uuid = self.state.document_by_itglue_id.get(resource_id)
            elif "structureddata" in resource_type:
                # ::Row points to custom asset
                target_type = "custom_asset"
                target_uuid = self.state.custom_asset_by_itglue_id.get(resource_id)

            if not target_uuid:
                continue

            # Check if relationship already exists
            rel_key = f"password:{password_uuid}:{target_type}:{target_uuid}"
            if rel_key in self.state.relationships:
                plan.existing.append({
                    "source_type": "password",
                    "source_id": password_uuid,
                    "target_type": target_type,
                    "target_id": target_uuid,
                })
            else:
                plan.to_create.append({
                    "source_type": "password",
                    "source_id": password_uuid,
                    "target_type": target_type,
                    "target_id": target_uuid,
                })

        return plan
```

**Step 4: Run tests to verify they pass**

```bash
cd /Users/jack/GitHub/bifrost-docs/tools/itglue-migrate
pytest tests/unit/test_sync_differ.py -v
```

**Step 5: Commit**

```bash
git add tools/itglue-migrate/src/itglue_migrate/sync_differ.py
git add tools/itglue-migrate/tests/unit/test_sync_differ.py
git commit -m "feat(migrate): add SyncDiffer for CSV vs API comparison"
```

---

### Task 2.3: Create Sync Executor Module

**Files:**
- Create: `tools/itglue-migrate/src/itglue_migrate/sync_executor.py`
- Create: `tools/itglue-migrate/tests/unit/test_sync_executor.py`

**Step 1: Write the failing test**

```python
"""Tests for sync_executor module."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from itglue_migrate.sync_executor import SyncExecutor, SyncResult
from itglue_migrate.sync_differ import SyncPlan, EntityPlan


@pytest.fixture
def mock_client():
    """Create a mock API client."""
    client = MagicMock()
    client.create_configuration = AsyncMock(return_value={"id": "new-uuid"})
    client.create_location = AsyncMock(return_value={"id": "new-uuid"})
    return client


@pytest.mark.asyncio
async def test_execute_creates_missing_entities(mock_client):
    """SyncExecutor creates entities marked for creation."""
    plan = SyncPlan()
    plan.configurations.to_create = [
        {"id": "123", "name": "New Server", "organization_id": "org-1"}
    ]

    executor = SyncExecutor(mock_client, org_id="org-uuid", dry_run=False)
    result = await executor.execute(plan)

    assert result.created["configurations"] == 1
    mock_client.create_configuration.assert_called_once()


@pytest.mark.asyncio
async def test_dry_run_does_not_call_api(mock_client):
    """SyncExecutor in dry_run mode doesn't make API calls."""
    plan = SyncPlan()
    plan.configurations.to_create = [
        {"id": "123", "name": "New Server", "organization_id": "org-1"}
    ]

    executor = SyncExecutor(mock_client, org_id="org-uuid", dry_run=True)
    result = await executor.execute(plan)

    assert result.created["configurations"] == 1  # Still counts
    mock_client.create_configuration.assert_not_called()
```

**Step 2: Run test to verify it fails**

```bash
cd /Users/jack/GitHub/bifrost-docs/tools/itglue-migrate
pytest tests/unit/test_sync_executor.py::test_execute_creates_missing_entities -v
```

Expected: FAIL

**Step 3: Write implementation**

```python
"""Sync executor - executes the sync plan against the API.

This module takes a SyncPlan and executes it against the API,
creating missing entities and relationships. Supports dry-run
mode for preview.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from itglue_migrate.api_client import BifrostDocsClient
from itglue_migrate.sync_differ import SyncPlan

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Results from sync execution."""

    created: dict[str, int] = field(default_factory=lambda: {
        "organizations": 0,
        "config_types": 0,
        "config_statuses": 0,
        "custom_asset_types": 0,
        "locations": 0,
        "configurations": 0,
        "custom_assets": 0,
        "documents": 0,
        "passwords": 0,
        "relationships": 0,
        "cell_writes": 0,
    })
    failed: dict[str, int] = field(default_factory=lambda: {
        "organizations": 0,
        "config_types": 0,
        "config_statuses": 0,
        "custom_asset_types": 0,
        "locations": 0,
        "configurations": 0,
        "custom_assets": 0,
        "documents": 0,
        "passwords": 0,
        "relationships": 0,
        "cell_writes": 0,
    })
    skipped: dict[str, int] = field(default_factory=lambda: {
        "organizations": 0,
        "config_types": 0,
        "config_statuses": 0,
        "custom_asset_types": 0,
        "locations": 0,
        "configurations": 0,
        "custom_assets": 0,
        "documents": 0,
        "passwords": 0,
        "relationships": 0,
    })
    errors: list[dict[str, Any]] = field(default_factory=list)

    # ID mappings for created entities (itglue_id -> uuid)
    id_map: dict[str, dict[str, str]] = field(default_factory=lambda: {
        "organization": {},
        "configuration": {},
        "location": {},
        "document": {},
        "password": {},
        "custom_asset": {},
        "config_type": {},
        "config_status": {},
        "custom_asset_type": {},
    })


class SyncExecutor:
    """Executes sync plan against the API."""

    def __init__(
        self,
        client: BifrostDocsClient,
        org_id: str,
        dry_run: bool = False,
        update_existing: bool = False,
    ):
        self.client = client
        self.org_id = org_id
        self.dry_run = dry_run
        self.update_existing = update_existing

    async def execute(self, plan: SyncPlan) -> SyncResult:
        """Execute the full sync plan."""
        result = SyncResult()

        # Execute in dependency order
        await self._execute_config_types(plan, result)
        await self._execute_config_statuses(plan, result)
        await self._execute_custom_asset_types(plan, result)
        await self._execute_locations(plan, result)
        await self._execute_configurations(plan, result)
        await self._execute_custom_assets(plan, result)
        await self._execute_documents(plan, result)
        await self._execute_passwords(plan, result)
        await self._execute_relationships(plan, result)

        return result

    async def _execute_config_types(self, plan: SyncPlan, result: SyncResult) -> None:
        """Create missing configuration types."""
        for item in plan.config_types.to_create:
            try:
                if not self.dry_run:
                    resp = await self.client.create_configuration_type(item["name"])
                    result.id_map["config_type"][item["name"].lower()] = resp["id"]
                result.created["config_types"] += 1
            except Exception as e:
                result.failed["config_types"] += 1
                result.errors.append({
                    "type": "config_type",
                    "item": item["name"],
                    "error": str(e),
                })

        result.skipped["config_types"] = len(plan.config_types.existing)

    async def _execute_config_statuses(self, plan: SyncPlan, result: SyncResult) -> None:
        """Create missing configuration statuses."""
        for item in plan.config_statuses.to_create:
            try:
                if not self.dry_run:
                    resp = await self.client.create_configuration_status(item["name"])
                    result.id_map["config_status"][item["name"].lower()] = resp["id"]
                result.created["config_statuses"] += 1
            except Exception as e:
                result.failed["config_statuses"] += 1
                result.errors.append({
                    "type": "config_status",
                    "item": item["name"],
                    "error": str(e),
                })

        result.skipped["config_statuses"] = len(plan.config_statuses.existing)

    async def _execute_custom_asset_types(self, plan: SyncPlan, result: SyncResult) -> None:
        """Create missing custom asset types."""
        for item in plan.custom_asset_types.to_create:
            try:
                if not self.dry_run:
                    resp = await self.client.create_custom_asset_type(
                        name=item["name"],
                        fields=item.get("fields", []),
                    )
                    result.id_map["custom_asset_type"][item["name"].lower()] = resp["id"]
                result.created["custom_asset_types"] += 1
            except Exception as e:
                result.failed["custom_asset_types"] += 1
                result.errors.append({
                    "type": "custom_asset_type",
                    "item": item["name"],
                    "error": str(e),
                })

        result.skipped["custom_asset_types"] = len(plan.custom_asset_types.existing)

    async def _execute_locations(self, plan: SyncPlan, result: SyncResult) -> None:
        """Create missing locations."""
        for item in plan.locations.to_create:
            itglue_id = str(item.get("id", ""))
            try:
                if not self.dry_run:
                    resp = await self.client.create_location(
                        org_id=self.org_id,
                        name=item.get("name", ""),
                        address_1=item.get("address_1"),
                        address_2=item.get("address_2"),
                        city=item.get("city"),
                        region=item.get("region"),
                        postal_code=item.get("postal_code"),
                        country=item.get("country"),
                        phone=item.get("phone"),
                        metadata={"itglue_id": itglue_id},
                    )
                    result.id_map["location"][itglue_id] = resp["id"]
                result.created["locations"] += 1
            except Exception as e:
                result.failed["locations"] += 1
                result.errors.append({
                    "type": "location",
                    "item": item.get("name", itglue_id),
                    "error": str(e),
                })

        result.skipped["locations"] = len(plan.locations.existing)

    async def _execute_configurations(self, plan: SyncPlan, result: SyncResult) -> None:
        """Create missing configurations."""
        for item in plan.configurations.to_create:
            itglue_id = str(item.get("id", ""))
            try:
                if not self.dry_run:
                    resp = await self.client.create_configuration(
                        org_id=self.org_id,
                        name=item.get("name", ""),
                        serial_number=item.get("serial"),
                        asset_tag=item.get("asset_tag"),
                        manufacturer=item.get("manufacturer"),
                        model=item.get("model"),
                        ip_address=item.get("ip"),
                        mac_address=item.get("mac"),
                        notes=item.get("notes"),
                        metadata={"itglue_id": itglue_id},
                    )
                    result.id_map["configuration"][itglue_id] = resp["id"]
                result.created["configurations"] += 1
            except Exception as e:
                result.failed["configurations"] += 1
                result.errors.append({
                    "type": "configuration",
                    "item": item.get("name", itglue_id),
                    "error": str(e),
                })

        result.skipped["configurations"] = len(plan.configurations.existing)

    async def _execute_custom_assets(self, plan: SyncPlan, result: SyncResult) -> None:
        """Create missing custom assets."""
        for item in plan.custom_assets.to_create:
            itglue_id = str(item.get("id", ""))
            try:
                if not self.dry_run:
                    # TODO: Need type_id lookup and field value mapping
                    pass
                result.created["custom_assets"] += 1
            except Exception as e:
                result.failed["custom_assets"] += 1
                result.errors.append({
                    "type": "custom_asset",
                    "item": itglue_id,
                    "error": str(e),
                })

        result.skipped["custom_assets"] = len(plan.custom_assets.existing)

    async def _execute_documents(self, plan: SyncPlan, result: SyncResult) -> None:
        """Create missing documents."""
        for item in plan.documents.to_create:
            itglue_id = str(item.get("id", ""))
            try:
                if not self.dry_run:
                    resp = await self.client.create_document(
                        org_id=self.org_id,
                        name=item.get("name", ""),
                        content=item.get("content", ""),
                        metadata={"itglue_id": itglue_id},
                    )
                    result.id_map["document"][itglue_id] = resp["id"]
                result.created["documents"] += 1
            except Exception as e:
                result.failed["documents"] += 1
                result.errors.append({
                    "type": "document",
                    "item": item.get("name", itglue_id),
                    "error": str(e),
                })

        result.skipped["documents"] = len(plan.documents.existing)

    async def _execute_passwords(self, plan: SyncPlan, result: SyncResult) -> None:
        """Create missing passwords and handle ::Row."""
        # Regular passwords
        for item in plan.passwords.to_create:
            itglue_id = str(item.get("id", ""))
            try:
                if not self.dry_run:
                    resp = await self.client.create_password(
                        org_id=self.org_id,
                        name=item.get("name", ""),
                        password=item.get("password", ""),
                        username=item.get("username"),
                        url=item.get("url"),
                        notes=item.get("notes"),
                        totp_secret=item.get("otp_secret"),
                        metadata={
                            "itglue_id": itglue_id,
                            "resource_type": item.get("resource_type"),
                            "resource_id": item.get("resource_id"),
                        },
                    )
                    result.id_map["password"][itglue_id] = resp["id"]
                result.created["passwords"] += 1
            except Exception as e:
                result.failed["passwords"] += 1
                result.errors.append({
                    "type": "password",
                    "item": item.get("name", itglue_id),
                    "error": str(e),
                })

        # ::Row passwords (create password + relationship later)
        for item in plan.passwords.row_creates:
            itglue_id = str(item.get("id", ""))
            try:
                if not self.dry_run:
                    resp = await self.client.create_password(
                        org_id=self.org_id,
                        name=item.get("name", ""),
                        password=item.get("password", ""),
                        username=item.get("username"),
                        url=item.get("url"),
                        notes=item.get("notes"),
                        totp_secret=item.get("otp_secret"),
                        metadata={
                            "itglue_id": itglue_id,
                            "resource_type": item.get("resource_type"),
                            "resource_id": item.get("resource_id"),
                        },
                    )
                    result.id_map["password"][itglue_id] = resp["id"]
                result.created["passwords"] += 1
            except Exception as e:
                result.failed["passwords"] += 1
                result.errors.append({
                    "type": "password",
                    "item": item.get("name", itglue_id),
                    "error": str(e),
                })

        result.skipped["passwords"] = len(plan.passwords.existing)

    async def _execute_relationships(self, plan: SyncPlan, result: SyncResult) -> None:
        """Create missing relationships."""
        for rel in plan.relationships.to_create:
            try:
                if not self.dry_run:
                    await self.client.create_relationship(
                        org_id=self.org_id,
                        source_type=rel["source_type"],
                        source_id=rel["source_id"],
                        target_type=rel["target_type"],
                        target_id=rel["target_id"],
                    )
                result.created["relationships"] += 1
            except Exception as e:
                result.failed["relationships"] += 1
                result.errors.append({
                    "type": "relationship",
                    "item": f"{rel['source_type']}:{rel['source_id']} -> {rel['target_type']}:{rel['target_id']}",
                    "error": str(e),
                })

        result.skipped["relationships"] = len(plan.relationships.existing)
```

**Step 4: Run tests**

```bash
cd /Users/jack/GitHub/bifrost-docs/tools/itglue-migrate
pytest tests/unit/test_sync_executor.py -v
```

**Step 5: Commit**

```bash
git add tools/itglue-migrate/src/itglue_migrate/sync_executor.py
git add tools/itglue-migrate/tests/unit/test_sync_executor.py
git commit -m "feat(migrate): add SyncExecutor for plan execution"
```

---

### Task 2.4: Create Sync CLI Command

**Files:**
- Modify: `tools/itglue-migrate/src/itglue_migrate/cli.py`

**Step 1: Add sync command imports at top of file**

Add after existing imports:

```python
from itglue_migrate.state_fetcher import StateFetcher
from itglue_migrate.sync_differ import SyncDiffer
from itglue_migrate.sync_executor import SyncExecutor
```

**Step 2: Add sync command**

Add before the `if __name__ == "__main__"` block:

```python
@app.command()
def sync(
    export_path: Path = typer.Option(
        ...,
        "--export-path",
        "-e",
        help="Path to IT Glue export directory",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    api_url: str = typer.Option(
        ...,
        "--api-url",
        "-u",
        help="BifrostDocs API URL",
    ),
    token: str = typer.Option(
        ...,
        "--token",
        "-t",
        help="API authentication token",
        envvar="BIFROST_API_TOKEN",
    ),
    org: str | None = typer.Option(
        None,
        "--org",
        "-o",
        help="Organization name to sync (mutually exclusive with --all)",
    ),
    all_orgs: bool = typer.Option(
        False,
        "--all",
        help="Sync all organizations (mutually exclusive with --org)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="Preview changes without making them",
    ),
    update_existing: bool = typer.Option(
        False,
        "--update-existing",
        help="Update entities that already exist",
    ),
) -> None:
    """
    Sync IT Glue export to BifrostDocs.

    Compares CSV export against existing API state and creates/updates
    missing entities. No plan file or state file required.

    Examples:
        # Sync a single organization
        itglue-migrate sync -e ./export -u https://api.example.com -t $TOKEN --org "Acme Corp"

        # Preview what would be synced
        itglue-migrate sync -e ./export -u https://api.example.com -t $TOKEN --org "Acme Corp" --dry-run

        # Sync all organizations
        itglue-migrate sync -e ./export -u https://api.example.com -t $TOKEN --all
    """
    import asyncio

    # Validate mutually exclusive options
    if not org and not all_orgs:
        console.print("[red]Error:[/red] Must specify either --org or --all")
        raise typer.Exit(1)

    if org and all_orgs:
        console.print("[red]Error:[/red] Cannot specify both --org and --all")
        raise typer.Exit(1)

    # Validate export path
    validation = _validate_export_path(export_path)
    if not validation.get("valid"):
        console.print(f"[red]Error:[/red] Invalid export path: {validation.get('errors')}")
        raise typer.Exit(1)

    # Run async sync
    exit_code = asyncio.run(_run_sync(
        export_path=export_path,
        api_url=api_url,
        token=token,
        org_name=org,
        all_orgs=all_orgs,
        dry_run=dry_run,
        update_existing=update_existing,
    ))

    raise typer.Exit(exit_code)


async def _run_sync(
    export_path: Path,
    api_url: str,
    token: str,
    org_name: str | None,
    all_orgs: bool,
    dry_run: bool,
    update_existing: bool,
) -> int:
    """Run the sync operation."""
    from itglue_migrate.csv_parser import CSVParser

    parser = CSVParser()

    # Parse all CSV files
    parsed_orgs = parser.parse_organizations(export_path / "organizations.csv") if (export_path / "organizations.csv").exists() else []
    parsed_configs = parser.parse_configurations(export_path / "configurations.csv") if (export_path / "configurations.csv").exists() else []
    parsed_locations = parser.parse_locations(export_path / "locations.csv") if (export_path / "locations.csv").exists() else []
    parsed_documents = parser.parse_documents(export_path / "documents.csv") if (export_path / "documents.csv").exists() else []
    parsed_passwords = parser.parse_passwords(export_path / "passwords.csv") if (export_path / "passwords.csv").exists() else []

    # Parse custom assets
    custom_types = parser.discover_custom_asset_types(export_path)
    parsed_custom_assets: dict[str, list] = {}
    for type_slug in custom_types:
        csv_path = export_path / f"{type_slug}.csv"
        if csv_path.exists():
            _, assets = parser.parse_custom_asset_csv(csv_path, type_slug)
            parsed_custom_assets[type_slug] = assets

    # Determine which orgs to sync
    if org_name:
        target_orgs = [o for o in parsed_orgs if o.get("name") == org_name]
        if not target_orgs:
            console.print(f"[red]Error:[/red] Organization '{org_name}' not found in export")
            return 1
    else:
        target_orgs = parsed_orgs

    async with BifrostDocsClient(base_url=api_url, api_key=token) as client:
        fetcher = StateFetcher(client)

        total_errors = 0

        for csv_org in target_orgs:
            org_name_display = csv_org.get("name", "Unknown")
            console.print(f"\n[bold]Syncing organization: {org_name_display}[/bold]")

            if dry_run:
                console.print("[yellow]DRY RUN - No changes will be made[/yellow]")

            # Fetch existing state
            console.print("\nFetching existing state...")
            state = await fetcher.fetch_all_orgs()

            # Find or match org
            itglue_id = str(csv_org.get("id", ""))
            org_uuid = state.org_by_itglue_id.get(itglue_id) or state.org_by_name.get(org_name_display.lower())

            if not org_uuid:
                console.print(f"  Organization not found in API, will create")
                # TODO: Create org first
                continue

            # Fetch org-specific state
            state = await fetcher.fetch_for_org(org_uuid)

            console.print(f"  Configurations: {len(state.configs)} found")
            console.print(f"  Locations: {len(state.locations)} found")
            console.print(f"  Documents: {len(state.documents)} found")
            console.print(f"  Passwords: {len(state.passwords)} found")
            console.print(f"  Custom Assets: {len(state.custom_assets)} found")

            # Filter CSV data for this org
            org_itglue_id = str(csv_org.get("id", ""))
            org_configs = [c for c in parsed_configs if str(c.get("organization_id")) == org_itglue_id]
            org_locations = [l for l in parsed_locations if str(l.get("organization_id")) == org_itglue_id]
            org_documents = [d for d in parsed_documents if str(d.get("organization_id")) == org_itglue_id]
            org_passwords = [p for p in parsed_passwords if str(p.get("organization_id")) == org_itglue_id]

            # Diff
            console.print("\nComparing with export...")
            differ = SyncDiffer(state)

            from itglue_migrate.sync_differ import SyncPlan
            plan = SyncPlan()
            plan.config_types = differ.diff_config_types(org_configs)
            plan.configurations = differ.diff_configurations(org_configs)
            plan.locations = differ.diff_locations(org_locations)
            plan.documents = differ.diff_documents(org_documents)
            plan.passwords = differ.diff_passwords(org_passwords)
            plan.relationships = differ.diff_relationships(org_passwords)

            # Display plan summary
            console.print(f"\n  Configuration Types: {len(plan.config_types.to_create)} to create, {len(plan.config_types.existing)} existing")
            console.print(f"  Locations: {len(plan.locations.to_create)} to create, {len(plan.locations.existing)} existing")
            console.print(f"  Configurations: {len(plan.configurations.to_create)} to create, {len(plan.configurations.existing)} existing")
            console.print(f"  Documents: {len(plan.documents.to_create)} to create, {len(plan.documents.existing)} existing")
            console.print(f"  Passwords: {len(plan.passwords.to_create)} to create, {len(plan.passwords.existing)} existing")
            console.print(f"    └── ::Cell: {len(plan.passwords.cell_writes)} to write into custom asset fields")
            console.print(f"    └── ::Row: {len(plan.passwords.row_creates)} to create with relationships")
            console.print(f"  Relationships: {len(plan.relationships.to_create)} to create, {len(plan.relationships.existing)} existing")

            if dry_run:
                console.print("\n[yellow]DRY RUN - No changes made[/yellow]")
                continue

            # Execute
            console.print("\nExecuting sync...")
            executor = SyncExecutor(
                client=client,
                org_id=org_uuid,
                dry_run=dry_run,
                update_existing=update_existing,
            )
            result = await executor.execute(plan)

            # Display results
            console.print("\n[bold]Results:[/bold]")
            console.print(f"  Created: {sum(result.created.values())} entities")
            console.print(f"  Skipped: {sum(result.skipped.values())} entities (existing)")
            console.print(f"  Failed: {sum(result.failed.values())} entities")

            if result.errors:
                console.print("\n[red]Errors:[/red]")
                for error in result.errors[:10]:  # Show first 10
                    console.print(f"  - {error['type']} '{error['item']}': {error['error']}")
                if len(result.errors) > 10:
                    console.print(f"  ... and {len(result.errors) - 10} more errors")

            total_errors += sum(result.failed.values())

        return 1 if total_errors > 0 else 0
```

**Step 3: Run type check**

```bash
cd /Users/jack/GitHub/bifrost-docs/tools/itglue-migrate
pyright src/itglue_migrate/cli.py
```

**Step 4: Test the command**

```bash
cd /Users/jack/GitHub/bifrost-docs/tools/itglue-migrate
python -m itglue_migrate.cli sync --help
```

**Step 5: Commit**

```bash
git add tools/itglue-migrate/src/itglue_migrate/cli.py
git commit -m "feat(migrate): add sync CLI command"
```

---

## Phase 3: Embedded Passwords (Tasks 3.1-3.3)

*Detailed implementation for ::Cell and ::Row handling - to be expanded after Phase 2 is complete.*

---

## Phase 4: Update Existing (Tasks 4.1-4.2)

*Detailed implementation for --update-existing flag - to be expanded after Phase 3 is complete.*

---

## Phase 5: Location UI (Tasks 5.1-5.3)

*Frontend changes for location address form - to be expanded after API phases are complete.*

---

## Summary

| Phase | Tasks | Description |
|-------|-------|-------------|
| 1 | 1.1-1.6 | Location schema (API + migration tool) |
| 2 | 2.1-2.4 | Core sync command |
| 3 | 3.1-3.3 | Embedded passwords (::Cell, ::Row) |
| 4 | 4.1-4.2 | Update existing entities |
| 5 | 5.1-5.3 | Location UI (frontend) |

**Total estimated tasks:** ~15 tasks across 5 phases

Run each task sequentially, committing after each step passes tests.
