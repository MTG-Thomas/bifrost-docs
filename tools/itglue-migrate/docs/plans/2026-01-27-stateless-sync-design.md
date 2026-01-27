# Stateless Sync Redesign

## Overview

Redesign the IT Glue migration tool to be stateless - no plan file, no state file. Use `metadata.itglue_id` on entities as the source of truth for what's already migrated.

## Problem

The current migration tool relies on:
- **Plan file** - Generated during preview, required for run
- **State file** - Tracks progress, can get out of sync with reality

This creates operational problems:
- Lost or misused plan/state files break the migration
- Hard to know what actually migrated vs what the state says
- Can't easily fix relationships after the fact
- Running one company at a time is fragile

## Solution

Replace `preview` and `run` commands with a single `sync` command that:
- Fetches existing state from the API (via `metadata.itglue_id`)
- Compares against CSV export
- Creates missing entities
- Creates missing relationships
- Optionally updates existing entities

## Command Structure

```bash
itglue-migrate sync \
  --export-path /path/to/export \
  --api-url https://api.example.com \
  --token $TOKEN \
  [--org "Company Name" | --all] \
  [--dry-run] \
  [--update-existing]
```

### Flags

| Flag | Required | Description |
|------|----------|-------------|
| `--export-path` | Yes | Path to IT Glue CSV export directory |
| `--api-url` | Yes | BifrostDocs API URL |
| `--token` | Yes | API authentication token |
| `--org` / `--all` | Yes (one of) | Sync single org or all orgs |
| `--dry-run` | No | Preview changes without making them |
| `--update-existing` | No | Update entities that already exist |

## Sync Flow

```
1. FETCH EXISTING STATE (from API)
   ├── List all orgs → build lookup by metadata.itglue_id and name
   ├── List all configurations → build lookup by metadata.itglue_id
   ├── List all custom asset types → build lookup by name
   ├── List all custom assets → build lookup by metadata.itglue_id
   ├── List all passwords → build lookup by metadata.itglue_id
   ├── List all documents → build lookup by metadata.itglue_id
   ├── List all locations → build lookup by metadata.itglue_id
   └── List all relationships → build lookup by source+target

2. PARSE CSV (from export)
   └── Parse all entity CSVs, including resource_type/resource_id on passwords

3. DIFF
   ├── Missing: in CSV but not in API lookup
   ├── Existing: in both (skip unless --update-existing)
   └── Relationships: password has resource_type/resource_id but no relationship exists

4. EXECUTE (unless --dry-run)
   ├── Create missing entities (in dependency order)
   ├── Update existing entities (if --update-existing)
   ├── Handle ::Cell passwords (write to custom asset field)
   ├── Handle ::Row passwords (create relationship)
   └── Create missing relationships
```

## Entity Dependencies & Sync Order

```
1. Organizations (no dependencies)
2. Configuration Types (no dependencies)
3. Configuration Statuses (no dependencies)
4. Custom Asset Types (no dependencies)
5. Locations (depends on: organizations)
6. Configurations (depends on: organizations, config types, config statuses)
7. Custom Assets (depends on: organizations, custom asset types)
8. Documents (depends on: organizations)
9. Passwords (depends on: organizations, AND targets for ::Cell)
10. Relationships (depends on: all entities exist)
```

## Organization Matching

When syncing, organizations are matched by:
1. **metadata.itglue_id** - If org was previously migrated
2. **name** - Fall back to name match for new orgs

No manual mapping required.

## Custom Asset Type Handling

- If custom asset type exists in BifrostDocs (matched by name or metadata), use its schema
- Only infer schema from CSV for new types

## Password Resource Types

| resource_type | Count | Handling |
|---------------|-------|----------|
| (empty) | ~4,400 | Standalone password |
| Configuration | ~3,400 | Password + relationship to config |
| StructuredData::Cell | ~220 | Value → custom asset field |
| Location | ~30 | Password + relationship to location |
| StructuredData::Row | ~25 | Password + relationship to custom asset |
| Document | ~12 | Password + relationship to document |

### ::Cell Handling (Embedded Password Field)

```
1. Find custom asset where metadata.itglue_id = password.resource_id
2. Find field on asset type where field.name = password.name AND field.type = "password"
3. If found:
   - Update custom asset's field value with password.password
   - Do NOT create the password as a standalone entity
4. If not found:
   - Warn: "Could not find matching password field"
   - Create as standalone password (fallback)
```

### ::Row Handling (Embedded Password Relationship)

```
1. Find custom asset where metadata.itglue_id = password.resource_id
2. Create password as standalone entity
3. Create relationship: password → custom_asset
```

## Error Handling

- Failures don't stop processing
- Continue with remaining entities
- Report all failures at end with actionable details
- Re-running sync retries failed items (idempotent)

## Dry-Run Output

```
Syncing organization: Acme Corp

Fetching existing state...
  Organizations: 1 found
  Configurations: 45 found
  Custom Assets: 120 found
  Passwords: 89 found

Comparing with export...

  Organizations:       0 to create,   1 existing (skip)
  Configuration Types: 2 to create,   5 existing (skip)
  Locations:           1 to create,   5 existing (skip)
  Configurations:     12 to create,  45 existing (skip)
  Custom Asset Types:  0 to create,   8 existing (skip)
  Custom Assets:      34 to create, 120 existing (skip)
  Documents:           3 to create,  23 existing (skip)
  Passwords:          15 to create,  89 existing (skip)
    └── ::Cell:        4 to write into custom asset fields
    └── ::Row:         2 to create with relationships
  Relationships:      28 to create

DRY RUN - No changes made.
```

## Location Schema Changes

Add proper fields to Location entity instead of stuffing into notes:

**New fields:**
- address_1
- address_2
- city
- region
- postal_code
- country
- phone

Requires database migration and API contract updates.

## Implementation Phases

### Phase 1: Location Schema (API)
- Add fields to Location entity
- Database migration
- Update API contracts and router

### Phase 2: Core Sync Command (Migration Tool)
- New `sync` command replacing `preview` and `run`
- Fetch existing state from API via metadata.itglue_id
- Create missing entities in dependency order
- Handle Configuration, Location, Document relationships
- Dry-run support
- Error handling with continue-on-failure

### Phase 3: Embedded Passwords (Migration Tool)
- ::Cell handling (write to custom asset fields)
- ::Row handling (password + relationship)
- Matching logic for finding target custom assets

### Phase 4: Update Existing (Migration Tool)
- `--update-existing` flag
- Compare and update entities that already exist

### Phase 5: Location UI (Frontend)
- Render location address fields as editable form
- Display formatted address in detail view

## Key Design Decisions

1. **No plan file** - Infer everything from CSV + existing API state
2. **No state file** - API metadata IS the state
3. **Idempotent** - Safe to run multiple times
4. **Continue on failure** - Don't block on single entity errors
5. **Org matching by metadata + name** - No manual mapping needed
6. **::Cell writes to field, ::Row creates relationship** - Handle IT Glue's embedded password patterns correctly
