# Sync-Importer Parity Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Bring the sync system to full parity with the importer, adding document processing, empty value validation, duplicate detection, and attachment support.

**Architecture:** Add document processing and validation layers to sync_executor.py that mirror importers.py. Integrate DocumentProcessor for HTML-to-markdown conversion and image uploads. Add pre-sync validation for data quality warnings.

**Tech Stack:** Python 3.11, markdownify, BeautifulSoup4, existing DocumentProcessor class

---

## Task 1: Add Document HTML Processing to Sync Executor

**Files:**
- Modify: `tools/itglue-migrate/src/itglue_migrate/sync_executor.py`
- Test: `tools/itglue-migrate/tests/unit/test_sync_executor.py`

**Step 1: Add DocumentProcessor import and initialization**

Add to sync_executor.py imports:
```python
from pathlib import Path
from itglue_migrate.document_processor import DocumentProcessor
```

Update `SyncExecutor.__init__` to accept optional document processor:
```python
def __init__(
    self,
    client: APIClientProtocol,
    org_id: str,
    dry_run: bool = False,
    state: ExistingState | None = None,
    update_existing: bool = False,
    reporter: ProgressReporter | SimpleProgressReporter | None = None,
    doc_processor: DocumentProcessor | None = None,
    export_path: Path | None = None,
) -> None:
    # ... existing code ...
    self.doc_processor = doc_processor
    self.export_path = export_path
```

**Step 2: Update _execute_documents to use DocumentProcessor**

Replace the document creation logic in `_execute_documents` to process HTML:
```python
async def _execute_documents(
    self, plan: SyncPlan, result: SyncResult
) -> None:
    """Execute document creation with HTML processing."""
    for entity in plan.documents.to_create:
        itglue_id = str(entity.get("id", ""))
        doc_name = entity.get("name", "Untitled")

        if self.reporter:
            self.reporter.set_current_item(f"Document: {doc_name}")

        try:
            if self.dry_run:
                result.created["documents"] = result.created.get("documents", 0) + 1
                if self.reporter:
                    self.reporter.update_progress(succeeded=1)
                continue

            # Get content - process through DocumentProcessor if available
            content = entity.get("content", "")
            path = entity.get("path") or entity.get("locator") or "/"

            if self.doc_processor and content:
                # Process HTML: clean, extract images, convert to markdown
                processed_content, warnings = await self.doc_processor.process_document(
                    {"id": itglue_id, "name": doc_name},
                    org_uuid=self.org_id,
                )
                if processed_content:
                    content = processed_content
                for warning in warnings:
                    logger.warning(f"Document {doc_name}: {warning}")
            elif content:
                # Fallback: just ensure content is string
                content = str(content) if content else ""

            # Build metadata
            metadata = entity.get("metadata") or {}
            if itglue_id and "itglue_id" not in metadata:
                metadata["itglue_id"] = itglue_id

            # Handle archived -> is_enabled
            is_enabled = entity.get("is_enabled", True)
            archived = entity.get("archived")
            if archived is not None:
                archived_str = str(archived).lower()
                is_enabled = archived_str not in ("true", "1", "yes")

            response = await self.client.create_document(
                org_id=self.org_id,
                path=path,
                name=doc_name,
                content=content,
                metadata=metadata,
                is_enabled=is_enabled,
            )

            if itglue_id and response.get("id"):
                result.id_map[itglue_id] = response["id"]

            result.created["documents"] = result.created.get("documents", 0) + 1
            if self.reporter:
                disabled = 1 if not is_enabled else 0
                self.reporter.update_progress(succeeded=1, disabled=disabled)

        except Exception as e:
            result.failed["documents"] = result.failed.get("documents", 0) + 1
            result.errors.append(f"Document '{doc_name}': {e}")
            logger.warning(f"Failed to create document: {e}")
            if self.reporter:
                self.reporter.update_progress(failed=1)
```

**Step 3: Run tests**

Run: `pytest tests/unit/test_sync_executor.py -v`
Expected: All existing tests pass

**Step 4: Commit**
```bash
git add src/itglue_migrate/sync_executor.py
git commit -m "feat(sync): add DocumentProcessor integration for HTML processing"
```

---

## Task 2: Add Empty Content Validation

**Files:**
- Modify: `tools/itglue-migrate/src/itglue_migrate/sync_executor.py`
- Test: `tools/itglue-migrate/tests/unit/test_sync_executor.py`

**Step 1: Add _is_content_empty helper function**

Add near top of sync_executor.py (after imports):
```python
import re

def _is_content_empty(html_content: str) -> bool:
    """Check if HTML content is empty after stripping tags.

    Args:
        html_content: HTML string to check.

    Returns:
        True if content is empty or whitespace-only after stripping HTML.
    """
    if not html_content:
        return True
    text = re.sub(r"<[^>]+>", "", html_content)
    return not text.strip()
```

**Step 2: Add empty document validation in _execute_documents**

Add check before creating document:
```python
# Check for empty content
raw_content = entity.get("content", "")
if _is_content_empty(raw_content):
    result.skipped["documents"] = result.skipped.get("documents", 0) + 1
    logger.warning(f"Skipping document '{doc_name}': empty content")
    if self.reporter:
        self.reporter.update_progress(skipped=1)
        self.reporter.warning(f"Document '{doc_name}' has empty content")
    continue
```

**Step 3: Add empty password validation in _execute_passwords**

Add check before creating password:
```python
password_value = entity.get("password", "")
if not password_value:
    result.skipped["passwords"] = result.skipped.get("passwords", 0) + 1
    logger.warning(f"Skipping password '{pwd_name}': empty password value")
    if self.reporter:
        self.reporter.update_progress(skipped=1)
        self.reporter.warning(f"Password '{pwd_name}' has empty password value")
    continue
```

**Step 4: Write test for empty content skipping**
```python
class TestSyncExecutorEmptyValueSkipping:
    """Tests for empty value validation."""

    @pytest.mark.asyncio
    async def test_skips_empty_document_content(self, mock_client: MagicMock) -> None:
        """Documents with empty content are skipped."""
        plan = SyncPlan()
        plan.documents.to_create = [
            {"id": "123", "name": "Empty Doc", "content": ""},
            {"id": "124", "name": "Whitespace Doc", "content": "   "},
            {"id": "125", "name": "HTML Only", "content": "<br><p></p>"},
        ]

        executor = SyncExecutor(mock_client, org_id="org-uuid", dry_run=False)
        result = await executor.execute(plan)

        assert result.skipped.get("documents", 0) == 3
        assert result.created.get("documents", 0) == 0
        mock_client.create_document.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_empty_password_value(self, mock_client: MagicMock) -> None:
        """Passwords with empty password field are skipped."""
        plan = SyncPlan()
        plan.passwords.to_create = [
            {"id": "123", "name": "Empty Password", "password": ""},
            {"id": "124", "name": "None Password", "password": None},
        ]

        executor = SyncExecutor(mock_client, org_id="org-uuid", dry_run=False)
        result = await executor.execute(plan)

        assert result.skipped.get("passwords", 0) == 2
        assert result.created.get("passwords", 0) == 0
        mock_client.create_password.assert_not_called()
```

**Step 5: Run tests**

Run: `pytest tests/unit/test_sync_executor.py::TestSyncExecutorEmptyValueSkipping -v`
Expected: PASS

**Step 6: Commit**
```bash
git add src/itglue_migrate/sync_executor.py tests/unit/test_sync_executor.py
git commit -m "feat(sync): add empty content/password validation"
```

---

## Task 3: Add Configuration Interfaces JSON Parsing

**Files:**
- Modify: `tools/itglue-migrate/src/itglue_migrate/sync_executor.py`

**Step 1: Add JSON parsing in _execute_configurations**

Update configuration creation to parse interfaces:
```python
import json

# In _execute_configurations, before creating configuration:
interfaces = entity.get("configuration_interfaces")
if isinstance(interfaces, str):
    try:
        interfaces = json.loads(interfaces)
    except json.JSONDecodeError:
        interfaces = None
```

**Step 2: Pass interfaces to API call**

Update the create_configuration call to include interfaces parameter.

**Step 3: Run tests**

Run: `pytest tests/unit/test_sync_executor.py -v`
Expected: PASS

**Step 4: Commit**
```bash
git add src/itglue_migrate/sync_executor.py
git commit -m "feat(sync): add configuration_interfaces JSON parsing"
```

---

## Task 4: Add Organization Status Mapping

**Files:**
- Modify: `tools/itglue-migrate/src/itglue_migrate/sync_executor.py`

**Step 1: Add map_org_status_to_is_enabled function**

```python
def _map_org_status_to_is_enabled(status: str | None) -> bool:
    """Convert IT Glue organization_status to is_enabled boolean.

    Args:
        status: "Active" or other status from IT Glue export

    Returns:
        True if Active, False otherwise
    """
    if not status:
        return True
    return str(status).lower() == "active"
```

**Step 2: Update _execute_organizations**

```python
# Get organization_status and map to is_enabled
org_status = entity.get("organization_status")
is_enabled = _map_org_status_to_is_enabled(org_status)
```

**Step 3: Run tests**

Run: `pytest tests/unit/test_sync_executor.py -v`
Expected: PASS

**Step 4: Commit**
```bash
git add src/itglue_migrate/sync_executor.py
git commit -m "feat(sync): add organization status to is_enabled mapping"
```

---

## Task 5: Add Duplicate Detection to SyncDiffer

**Files:**
- Modify: `tools/itglue-migrate/src/itglue_migrate/sync_differ.py`
- Test: `tools/itglue-migrate/tests/unit/test_sync_differ.py`

**Step 1: Add duplicate detection in diff_organizations**

Track seen names and skip duplicates:
```python
def diff_organizations(self, csv_orgs: list[dict[str, Any]]) -> EntityPlan:
    """Diff organizations - identify which need to be created."""
    plan = EntityPlan()
    seen_names: set[str] = set()

    for org in csv_orgs:
        org_name = org.get("name", "")
        itglue_id = str(org.get("id", ""))

        if not org_name:
            continue

        # Check for duplicates
        name_lower = org_name.lower()
        if name_lower in seen_names:
            plan.skipped.append({
                "name": org_name,
                "itglue_id": itglue_id,
                "reason": "duplicate_name",
            })
            continue
        seen_names.add(name_lower)

        # ... rest of existing logic ...
```

**Step 2: Add duplicate detection in diff_documents**

Track seen doc names per organization:
```python
def diff_documents(self, csv_docs: list[dict[str, Any]]) -> EntityPlan:
    """Diff documents - identify which need to be created."""
    plan = EntityPlan()
    seen_docs: dict[str, set[str]] = {}  # org_id -> set of doc names

    for doc in csv_docs:
        # ... existing logic ...

        # Check for duplicates within same org
        org_id = str(doc.get("organization_id", ""))
        doc_name_lower = doc_name.lower()

        if org_id in seen_docs and doc_name_lower in seen_docs[org_id]:
            plan.skipped.append({
                "name": doc_name,
                "itglue_id": itglue_id,
                "reason": "duplicate_name",
            })
            continue

        seen_docs.setdefault(org_id, set()).add(doc_name_lower)
        # ... rest of logic ...
```

**Step 3: Add EntityPlan.skipped field**

Update EntityPlan dataclass:
```python
@dataclass
class EntityPlan:
    to_create: list[dict[str, Any]] = field(default_factory=list)
    to_update: list[dict[str, Any]] = field(default_factory=list)
    existing: list[dict[str, Any]] = field(default_factory=list)
    skipped: list[dict[str, Any]] = field(default_factory=list)  # NEW
```

**Step 4: Write tests**

```python
class TestSyncDifferDuplicateDetection:
    """Tests for duplicate detection."""

    def test_diff_organizations_skips_duplicates(self, mock_state: MagicMock) -> None:
        """Duplicate org names are skipped."""
        differ = SyncDiffer(mock_state)
        csv_orgs = [
            {"id": "1", "name": "Acme Inc"},
            {"id": "2", "name": "ACME INC"},  # Duplicate (case-insensitive)
            {"id": "3", "name": "Other Corp"},
        ]

        plan = differ.diff_organizations(csv_orgs)

        assert len(plan.to_create) == 2
        assert len(plan.skipped) == 1
        assert plan.skipped[0]["reason"] == "duplicate_name"
```

**Step 5: Run tests**

Run: `pytest tests/unit/test_sync_differ.py::TestSyncDifferDuplicateDetection -v`
Expected: PASS

**Step 6: Commit**
```bash
git add src/itglue_migrate/sync_differ.py tests/unit/test_sync_differ.py
git commit -m "feat(sync): add duplicate name detection for orgs and docs"
```

---

## Task 6: Add Attachment Upload Support

**Files:**
- Modify: `tools/itglue-migrate/src/itglue_migrate/sync_executor.py`
- Modify: `tools/itglue-migrate/src/itglue_migrate/sync_differ.py`

**Step 1: Add attachment upload after entity creation**

In sync_executor.py, add helper method:
```python
async def _upload_entity_attachments(
    self,
    entity_type: str,
    itglue_id: str,
    our_entity_id: str,
) -> int:
    """Upload attachments for an entity if doc_processor is available."""
    if not self.doc_processor or not self.export_path:
        return 0

    try:
        count = await self.doc_processor.upload_entity_attachments(
            entity_type=entity_type,
            entity_id=itglue_id,
            org_uuid=self.org_id,
            our_entity_id=our_entity_id,
        )
        return count
    except Exception as e:
        logger.warning(f"Failed to upload attachments for {entity_type}/{itglue_id}: {e}")
        return 0
```

**Step 2: Call attachment upload after creating entities**

In _execute_configurations, after successful creation:
```python
if bifrost_id := response.get("id"):
    result.id_map[itglue_id] = bifrost_id

    # Upload attachments
    if self.doc_processor and self.export_path:
        attachment_count = await self._upload_entity_attachments(
            "configurations", itglue_id, bifrost_id
        )
        if attachment_count > 0 and self.reporter:
            self.reporter.info(f"Uploaded {attachment_count} attachments")
```

Apply same pattern to:
- _execute_locations
- _execute_documents
- _execute_passwords
- _execute_custom_assets

**Step 3: Run tests**

Run: `pytest tests/unit/test_sync_executor.py -v`
Expected: PASS

**Step 4: Commit**
```bash
git add src/itglue_migrate/sync_executor.py
git commit -m "feat(sync): add attachment upload support for all entity types"
```

---

## Task 7: Update CLI to Pass DocumentProcessor to Sync

**Files:**
- Modify: `tools/itglue-migrate/src/itglue_migrate/cli.py`

**Step 1: Import DocumentProcessor**

```python
from itglue_migrate.document_processor import DocumentProcessor
```

**Step 2: Create DocumentProcessor in sync command**

In the sync command handler:
```python
# Create document processor for HTML processing and attachments
doc_processor = None
if export_path:
    doc_processor = DocumentProcessor(client, export_path)

executor = SyncExecutor(
    client,
    org_id=org_uuid,
    dry_run=dry_run,
    state=state,
    update_existing=update_existing,
    reporter=reporter,
    doc_processor=doc_processor,
    export_path=export_path,
)
```

**Step 3: Run full sync test**

Run: `python -m itglue_migrate sync --org "Test Org" --dry-run`
Expected: No errors

**Step 4: Commit**
```bash
git add src/itglue_migrate/cli.py
git commit -m "feat(sync): wire up DocumentProcessor in CLI sync command"
```

---

## Task 8: Add Pre-Sync Validation Warnings

**Files:**
- Modify: `tools/itglue-migrate/src/itglue_migrate/sync_differ.py`
- Test: `tools/itglue-migrate/tests/unit/test_sync_differ.py`

**Step 1: Add validation_warnings to SyncPlan**

```python
@dataclass
class SyncPlan:
    # ... existing fields ...
    validation_warnings: list[str] = field(default_factory=list)
```

**Step 2: Add validate method to SyncDiffer**

```python
def validate_data_quality(
    self,
    csv_orgs: list[dict[str, Any]],
    csv_docs: list[dict[str, Any]],
    csv_passwords: list[dict[str, Any]],
) -> list[str]:
    """Check data quality and return warnings.

    Checks for:
    - Duplicate organization names
    - Duplicate document names within orgs
    - Empty password values
    - Empty document content
    """
    warnings = []

    # Check for duplicate org names
    org_names = [o.get("name", "").lower() for o in csv_orgs if o.get("name")]
    duplicates = [n for n in org_names if org_names.count(n) > 1]
    if duplicates:
        warnings.append(f"Found {len(set(duplicates))} duplicate organization names")

    # Check for empty passwords
    empty_pwds = [p for p in csv_passwords if not p.get("password")]
    if empty_pwds:
        warnings.append(f"Found {len(empty_pwds)} passwords with empty values")

    # Check for empty documents
    empty_docs = [d for d in csv_docs if _is_content_empty(d.get("content", ""))]
    if empty_docs:
        warnings.append(f"Found {len(empty_docs)} documents with empty content")

    return warnings
```

**Step 3: Run tests**

Run: `pytest tests/unit/test_sync_differ.py -v`
Expected: PASS

**Step 4: Commit**
```bash
git add src/itglue_migrate/sync_differ.py tests/unit/test_sync_differ.py
git commit -m "feat(sync): add pre-sync data quality validation"
```

---

## Task 9: Display Validation Warnings in CLI

**Files:**
- Modify: `tools/itglue-migrate/src/itglue_migrate/cli.py`

**Step 1: Call validation before sync**

```python
# Validate data quality
warnings = differ.validate_data_quality(csv_orgs, csv_docs, csv_passwords)
if warnings:
    console.print("[yellow]Data Quality Warnings:[/yellow]")
    for warning in warnings:
        console.print(f"  [yellow]⚠️  {warning}[/yellow]")
    console.print()
```

**Step 2: Run full test**

Run: `python -m itglue_migrate sync --org "Test Org" --dry-run`
Expected: Warnings displayed before sync

**Step 3: Commit**
```bash
git add src/itglue_migrate/cli.py
git commit -m "feat(sync): display data quality warnings before sync"
```

---

## Task 10: Final Integration Test

**Step 1: Run full test suite**

Run: `pytest tests/unit/ -v`
Expected: All tests pass

**Step 2: Run type check**

Run: `pyright src/itglue_migrate/`
Expected: No errors

**Step 3: Run linting**

Run: `ruff check src/itglue_migrate/`
Expected: No errors

**Step 4: Manual integration test**

Run: `python -m itglue_migrate sync --org "Test Org" --dry-run`
Expected: Full sync preview with all features working

**Step 5: Final commit**
```bash
git add -A
git commit -m "feat(sync): complete sync-importer parity implementation"
```

---

## Summary of Changes

| Feature | File | Description |
|---------|------|-------------|
| Document HTML Processing | sync_executor.py | Integrate DocumentProcessor for HTML→Markdown |
| Empty Content Validation | sync_executor.py | Skip empty documents and passwords |
| Config Interfaces | sync_executor.py | Parse JSON configuration_interfaces |
| Org Status Mapping | sync_executor.py | Map organization_status to is_enabled |
| Duplicate Detection | sync_differ.py | Skip duplicate org/doc names |
| Attachment Uploads | sync_executor.py | Upload attachments after entity creation |
| CLI Integration | cli.py | Wire up DocumentProcessor and validation |
| Data Quality Warnings | sync_differ.py, cli.py | Pre-sync validation display |
