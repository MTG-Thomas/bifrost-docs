# Fix: Add configurations_count to sidebar

## Problem
Configurations count is always 0 in the sidebar because there's no total `configurations_count` field. The code only counts configurations broken down by type, missing configs without a type.

## Root Cause
- `SidebarData` schema has `passwords_count`, `locations_count`, `documents_count` but NOT `configurations_count`
- The sidebar endpoint loops through configuration types and counts by type, but never counts total configurations
- Configurations with `configuration_type_id = null` are never counted

## Files to Modify

### 1. `api/src/models/contracts/organization.py`
Add `configurations_count: int` field to `SidebarData` class (after `documents_count`)

### 2. `api/src/repositories/configuration.py`
Add `count_by_organization()` method (similar to password/location/document repos):
```python
async def count_by_organization(self, organization_id: UUID) -> int:
    from sqlalchemy import func
    result = await self.session.execute(
        select(func.count(Configuration.id)).where(
            Configuration.organization_id == organization_id,
            Configuration.is_enabled.is_(True),
        )
    )
    return result.scalar_one()
```

### 3. `api/src/routers/organizations.py` (line ~359-361)
Add configurations count call after documents_count:
```python
configurations_count = await config_repo.count_by_organization(org_id)
```

Update return statement (~line 387):
```python
return SidebarData(
    passwords_count=passwords_count,
    locations_count=locations_count,
    documents_count=documents_count,
    configurations_count=configurations_count,  # Add this
    configuration_types=configuration_types,
    custom_asset_types=custom_asset_types,
)
```

## Verification
1. Create a configuration without a type
2. Call `GET /api/organizations/{org_id}/sidebar`
3. Verify `configurations_count` shows correct count
4. Run existing tests: `pytest api/`
