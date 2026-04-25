# Docs-to-Bifrost Sync Boundary

**Date:** 2026-04-24
**Status:** Design
**Related:** #19, #33, #34, #35, MTG-Thomas/bifrost#108

---

## Goal

Bifrost Docs should become a first-class Bifrost ecosystem application without becoming a fork-only downstream of the Bifrost platform.

The sync design should let Docs use Bifrost for generic connector/runtime capabilities while keeping documentation-specific behavior inside this repository. The upstream-compatible rule is: Bifrost can provide source data and execution primitives, but Bifrost Docs absorbs the adaptation needed to turn that data into useful MSP documentation.

---

## Responsibilities Split

### Bifrost Owns

Bifrost should stay responsible for generic integration runtime concerns:

- Connector execution for vendor systems and Bifrost-native workflows
- OAuth/token lifecycle and refresh behavior
- Secret storage and retrieval
- Scheduling, retries, backoff, and failure monitoring
- Connector health, run status, and operational telemetry
- Generic source payload delivery to downstream consumers

These capabilities should not know about Bifrost Docs entities, table layouts, custom asset schemas, documentation review flows, or field ownership rules.

### Bifrost Docs Owns

Bifrost Docs should own all downstream documentation behavior:

- Mapping source records into Docs entities and custom asset types
- Matching incoming records to existing Docs records
- Field ownership and conflict policy
- Reconciliation queues and review UX
- Provenance storage and display
- Documentation-specific normalization and validation
- Presentation choices for source metadata, confidence, and sync state
- User decisions about which fields are accepted, ignored, overridden, or pinned

Docs should treat Bifrost as a source/runtime provider, not as a documentation business-logic layer.

---

## Assumptions From Bifrost Generic Capabilities

Docs can assume Bifrost will eventually provide a generic contract for connector output and execution metadata. The minimum useful assumptions are:

- A source system identifier and connector/workflow identifier
- A stable source record identifier when the vendor provides one
- A source record type or entity kind
- A raw or normalized source payload
- Execution/run metadata such as run ID, started/finished timestamps, and status
- Error and retry information at the connector/run level
- Auth, token refresh, and secret handling outside Docs
- A scheduling mechanism that can call or publish sync output without Docs hosting connector workers

Docs should not assume that Bifrost will provide Docs-ready entity IDs, Docs field names, merge decisions, or reconciliation outcomes.

---

## What Lives In Docs

The sync boundary inside Docs should be built around ingestion, mapping, matching, provenance, and review.

### Mapping

Docs maps source records into target documentation shapes:

- Core entities such as organizations, locations, configurations, passwords, and documents
- Custom asset types and custom asset fields
- Per-source field transforms and display labels
- Documentation-specific defaults and validation

Mapping definitions should be versioned enough to explain how a synced value arrived at its current Docs field.

### Matching

Docs decides whether a source record maps to an existing Docs record, creates a candidate, or needs review. Matching can use:

- Source identity links
- Existing provenance records
- Vendor IDs and serial numbers
- Names, domains, hostnames, URLs, and other documentation identifiers
- Human-approved matches from prior reconciliation

Matching should be conservative. Ambiguous matches should create review work, not silent overwrites.

### Field Ownership And Conflicts

Docs owns the rules for what happens when source data differs from Docs data:

- Source-owned fields can update automatically when confidence is high
- Docs-owned fields should not be overwritten by sync
- Mixed fields require explicit conflict policy
- User-pinned values should block automated replacement
- Conflicts should preserve both the current Docs value and the incoming source value

### Provenance

Docs stores and displays enough metadata to answer:

- Which source system provided this value?
- Which source record and connector run produced it?
- When was it last observed?
- Was it accepted automatically, accepted by a user, ignored, or superseded?
- Is the value current, stale, conflicted, or manually pinned?

The detailed provenance UI is issue #35, but the data model should be shaped by this boundary.

### Reconciliation And Review UX

Docs owns the human-facing workflow for unresolved sync decisions:

- New candidate records
- Possible duplicate matches
- Field-level conflicts
- Source deletions or missing records
- Low-confidence updates
- Bulk accept/ignore where safe

The review experience should be designed for documentation operators, not connector developers.

---

## Non-Goals

This design does not require:

- Docs-specific entity mapping inside MTG-Thomas/bifrost
- Bifrost platform changes that know about Docs tables, custom asset schemas, or review queues
- A new connector runtime inside Bifrost Docs
- Direct vendor token handling inside Docs for Bifrost-managed connectors
- Solving every vendor integration before the first pilot
- Bidirectional sync from Docs back into vendor systems
- Replacing the existing migration tooling
- A full generic ETL framework in Docs

Docs may later expose APIs that Bifrost can call, but the semantics of mapping, matching, provenance, and reconciliation remain Docs-owned.

---

## Minimal Sync Contract Concepts

Issue #34 should define the source metadata contract in enough detail for Docs to store provenance and process sync candidates. The contract can stay small at first:

| Concept | Purpose |
|---|---|
| `source_system` | Identifies the vendor or upstream system, such as Autotask, Halo, NinjaOne, or IT Glue |
| `connector_id` / `workflow_id` | Identifies the Bifrost connector or workflow that produced the record |
| `run_id` | Links records to an execution attempt for troubleshooting |
| `source_record_type` | Describes the upstream entity kind |
| `source_record_id` | Stable upstream ID when available |
| `observed_at` | Timestamp when Bifrost observed the source state |
| `payload` | Raw or normalized source content for Docs mapping |
| `payload_hash` | Helps detect unchanged source records |
| `schema_version` | Allows contract evolution without guessing |
| `source_url` | Optional operator-facing link back to the upstream record |

Docs can extend this internally with mapping version, match confidence, target entity references, field-level provenance, and reconciliation state.

---

## Pilot Integration Assumptions

The first pilot should prove the boundary with one narrow integration path rather than a broad sync platform.

Recommended pilot shape:

- Bifrost executes a generic connector/workflow and produces source metadata records
- Docs ingests those records through a small import endpoint, file handoff, or queued message
- Docs maps only a limited set of fields into one or two target entity types
- Matching starts with source identity and a small number of deterministic identifiers
- Conflicts go to review rather than being overwritten automatically
- Provenance is stored even if the first UI is simple
- The pilot can be rerun safely without duplicating records

The pilot should validate the contract boundary before optimizing for scale, broad vendor coverage, or polished UX.

---

## Execution Breakdown

### Issue #34: Source Metadata Contract

Define the contract Docs expects from Bifrost-managed connector output:

- Required and optional metadata fields
- Source identity semantics
- Run/execution metadata
- Payload versioning and hash behavior
- Error/staleness signals that Docs should preserve
- Example payloads for the pilot source

Acceptance for #34 should be a contract that lets Docs create sync candidates and provenance records without Bifrost knowing Docs-specific schemas.

### Issue #35: Provenance UI

Build the operator-facing display and review surface after the metadata contract is clear:

- Field-level source badges or detail panels
- Last observed and last accepted timestamps
- Source system and source record links
- Conflict/stale/pinned states
- Review actions for accept, ignore, pin, and resolve

Acceptance for #35 should focus on whether a technician can understand where a value came from and what action, if any, is needed.

---

## Acceptance Criteria

- The boundary between Bifrost and Bifrost Docs is explicit and practical
- Bifrost responsibilities are limited to generic connector/runtime capabilities
- Docs responsibilities include mapping, matching, reconciliation, provenance, field ownership, and review UX
- Non-goals clearly reject Docs-specific platform behavior in MTG-Thomas/bifrost
- The minimal contract concepts are sufficient to unblock #34
- The provenance and review expectations are sufficient to shape #35
- The pilot assumptions keep the first implementation narrow, repeatable, and upstream-compatible
- No code changes are required for issue #33
