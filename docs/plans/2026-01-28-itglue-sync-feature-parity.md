# ITGlue Sync Feature Parity Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the `itglue sync` command to achieve feature parity with the old `itglue run` command - documents, custom assets, and folder paths should all migrate correctly.

**Architecture:** The sync command uses a stateless approach (fetch state once, diff against CSV, execute changes). Three critical bugs prevent successful migration: (1) documents check for empty content before loading HTML from files, (2) custom asset type state isn't updated after creation so assets can't find their types, (3) document folder paths aren't extracted from the filesystem. We'll fix these in the SyncExecutor and DocumentProcessor classes.

**Tech Stack:** Python 3.11+, pytest, asyncio, Typer CLI, SQLAlchemy/Alembic

---

## Task 1: Add Document Folder Map to DocumentProcessor

**Files:**
- Modify: `tools/itglue-migrate/src/itglue_migrate/document_processor.py`
- Test: `tools/itglue-migrate/tests/unit/test_document_processor.py`

**Step 1: Write the failing test for document folder map**

```python
# In tests/unit/test_document_processor.py

import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock

from itglue_migrate.document_processor import DocumentProcessor


class TestDocumentFolderMap:
    """Tests for _build_document_folder_map functionality."""

    def test_build_folder_map_root_level_document(self, tmp_path: Path) -> None:
        """Document at root level should have path '/'."""
        # Create export structure: documents/DOC-123-456 My Document/index.html
        docs_dir = tmp_path / "documents"
        doc_folder = docs_dir / "DOC-123-456 My Document"
        doc_folder.mkdir(parents=True)
        (doc_folder / "index.html").write_text("<html>content</html>")

        mock_client = Mock()
        processor = DocumentProcessor(mock_client, tmp_path)

        folder_map = processor.document_folder_map

        assert "456" in folder_map
        folder_path, html_file = folder_map["456"]
        assert folder_path == "/"
        assert html_file is not None
        assert html_file.name == "index.html"

    def test_build_folder_map_nested_document(self, tmp_path: Path) -> None:
        """Document in subfolder should have correct nested path."""
        # Create: documents/_Archive/DOC-123-789 Archived Doc/doc.html
        docs_dir = tmp_path / "documents" / "_Archive"
        doc_folder = docs_dir / "DOC-123-789 Archived Doc"
        doc_folder.mkdir(parents=True)
        (doc_folder / "doc.html").write_text("<html>archived</html>")

        mock_client = Mock()
        processor = DocumentProcessor(mock_client, tmp_path)

        folder_map = processor.document_folder_map

        assert "789" in folder_map
        folder_path, html_file = folder_map["789"]
        assert folder_path == "/_Archive"

    def test_build_folder_map_deeply_nested_document(self, tmp_path: Path) -> None:
        """Document in deep subfolder should have full path."""
        # Create: documents/_Archive/Projects/2024/DOC-1-999 Deep Doc/index.html
        docs_dir = tmp_path / "documents" / "_Archive" / "Projects" / "2024"
        doc_folder = docs_dir / "DOC-1-999 Deep Doc"
        doc_folder.mkdir(parents=True)
        (doc_folder / "index.html").write_text("<html>deep</html>")

        mock_client = Mock()
        processor = DocumentProcessor(mock_client, tmp_path)

        folder_map = processor.document_folder_map

        assert "999" in folder_map
        folder_path, _ = folder_map["999"]
        assert folder_path == "/_Archive/Projects/2024"

    def test_build_folder_map_no_html_file(self, tmp_path: Path) -> None:
        """Document folder without HTML returns None for html_file."""
        docs_dir = tmp_path / "documents"
        doc_folder = docs_dir / "DOC-123-111 No HTML"
        doc_folder.mkdir(parents=True)
        # No HTML file created

        mock_client = Mock()
        processor = DocumentProcessor(mock_client, tmp_path)

        folder_map = processor.document_folder_map

        assert "111" in folder_map
        folder_path, html_file = folder_map["111"]
        assert folder_path == "/"
        assert html_file is None

    def test_build_folder_map_empty_documents_dir(self, tmp_path: Path) -> None:
        """Empty documents directory returns empty map."""
        (tmp_path / "documents").mkdir()

        mock_client = Mock()
        processor = DocumentProcessor(mock_client, tmp_path)

        assert processor.document_folder_map == {}

    def test_build_folder_map_no_documents_dir(self, tmp_path: Path) -> None:
        """Missing documents directory returns empty map."""
        mock_client = Mock()
        processor = DocumentProcessor(mock_client, tmp_path)

        assert processor.document_folder_map == {}
```

**Step 2: Run test to verify it fails**

Run: `cd tools/itglue-migrate && pytest tests/unit/test_document_processor.py::TestDocumentFolderMap -v`
Expected: FAIL with AttributeError - `document_folder_map` doesn't exist

**Step 3: Implement document_folder_map property**

Add to `document_processor.py` after the `__init__` method (around line 160):

```python
import re
from functools import cached_property

# Add this pattern near the top with other constants (around line 30)
DOC_FOLDER_PATTERN = re.compile(r"^DOC-\d+-(\d+)\s")
```

```python
# Add this property to DocumentProcessor class (after __init__)

@cached_property
def document_folder_map(self) -> dict[str, tuple[str, Path | None]]:
    """Build map of document IDs to (folder_path, html_file).

    Scans the documents/ directory in the export for DOC-{org}-{id} folders
    and extracts the folder path based on nesting level.

    Returns:
        Dict mapping doc_id (string) to tuple of (folder_path, html_file_path).
        folder_path is "/" for root level, "/_Archive" for nested, etc.
        html_file_path is Path to HTML file or None if not found.
    """
    result: dict[str, tuple[str, Path | None]] = {}
    documents_path = self.export_path / "documents"

    if not documents_path.exists():
        return result

    for item in documents_path.rglob("*"):
        if not item.is_dir():
            continue

        match = DOC_FOLDER_PATTERN.match(item.name)
        if not match:
            continue

        doc_id = match.group(1)

        # Determine folder path from relative position
        rel_path = item.relative_to(documents_path)
        parts = rel_path.parts

        if len(parts) == 1:
            # Root level: documents/DOC-xxx-123 Name/
            folder_path = "/"
        else:
            # Nested: documents/FolderName/DOC-xxx-123 Name/
            folder_parts = parts[:-1]
            folder_path = "/" + "/".join(folder_parts)

        # Find HTML file - prefer index.html
        html_files = list(item.glob("*.html"))
        if not html_files:
            html_files = list(item.glob("*.htm"))

        html_file: Path | None = None
        for f in html_files:
            if f.name.lower() in ("index.html", "index.htm"):
                html_file = f
                break
        if html_file is None and html_files:
            html_file = html_files[0]

        result[doc_id] = (folder_path, html_file)

    return result
```

**Step 4: Run test to verify it passes**

Run: `cd tools/itglue-migrate && pytest tests/unit/test_document_processor.py::TestDocumentFolderMap -v`
Expected: All 6 tests PASS

**Step 5: Commit**

```bash
cd tools/itglue-migrate
git add src/itglue_migrate/document_processor.py tests/unit/test_document_processor.py
git commit -m "feat(sync): add document_folder_map to DocumentProcessor

Builds a map of document IDs to folder paths by scanning the export's
documents/ directory for DOC-{org}-{id} folders. This enables the sync
command to preserve document folder hierarchy during migration."
```

---

## Task 2: Add load_document_content Method to DocumentProcessor

**Files:**
- Modify: `tools/itglue-migrate/src/itglue_migrate/document_processor.py`
- Modify: `tools/itglue-migrate/tests/unit/test_document_processor.py`

**Step 1: Write the failing test for load_document_content**

```python
# Add to tests/unit/test_document_processor.py

class TestLoadDocumentContent:
    """Tests for load_document_content functionality."""

    def test_load_content_from_html_file(self, tmp_path: Path) -> None:
        """Should load HTML content from document folder."""
        docs_dir = tmp_path / "documents"
        doc_folder = docs_dir / "DOC-123-456 Test Doc"
        doc_folder.mkdir(parents=True)
        html_content = "<html><body><p>Test content</p></body></html>"
        (doc_folder / "index.html").write_text(html_content)

        mock_client = Mock()
        processor = DocumentProcessor(mock_client, tmp_path)

        content = processor.load_document_content("456")

        assert content == html_content

    def test_load_content_document_not_found(self, tmp_path: Path) -> None:
        """Should return None if document ID not in folder map."""
        (tmp_path / "documents").mkdir()

        mock_client = Mock()
        processor = DocumentProcessor(mock_client, tmp_path)

        content = processor.load_document_content("nonexistent")

        assert content is None

    def test_load_content_no_html_file(self, tmp_path: Path) -> None:
        """Should return None if document folder has no HTML file."""
        docs_dir = tmp_path / "documents"
        doc_folder = docs_dir / "DOC-123-789 No HTML"
        doc_folder.mkdir(parents=True)
        # No HTML file

        mock_client = Mock()
        processor = DocumentProcessor(mock_client, tmp_path)

        content = processor.load_document_content("789")

        assert content is None

    def test_load_content_utf8_encoding(self, tmp_path: Path) -> None:
        """Should handle UTF-8 encoded content."""
        docs_dir = tmp_path / "documents"
        doc_folder = docs_dir / "DOC-1-100 Unicode Doc"
        doc_folder.mkdir(parents=True)
        html_content = "<html><body>Caf\u00e9 \u2603 \u2764</body></html>"
        (doc_folder / "index.html").write_text(html_content, encoding="utf-8")

        mock_client = Mock()
        processor = DocumentProcessor(mock_client, tmp_path)

        content = processor.load_document_content("100")

        assert "Café" in content
        assert "\u2603" in content

    def test_load_content_latin1_fallback(self, tmp_path: Path) -> None:
        """Should fall back to latin-1 if UTF-8 fails."""
        docs_dir = tmp_path / "documents"
        doc_folder = docs_dir / "DOC-1-200 Latin Doc"
        doc_folder.mkdir(parents=True)
        # Write with latin-1 encoding (has bytes invalid in UTF-8)
        html_content = "<html><body>Caf\xe9</body></html>"
        (doc_folder / "index.html").write_bytes(html_content.encode("latin-1"))

        mock_client = Mock()
        processor = DocumentProcessor(mock_client, tmp_path)

        content = processor.load_document_content("200")

        assert content is not None
        assert "Café" in content
```

**Step 2: Run test to verify it fails**

Run: `cd tools/itglue-migrate && pytest tests/unit/test_document_processor.py::TestLoadDocumentContent -v`
Expected: FAIL with AttributeError - `load_document_content` doesn't exist

**Step 3: Implement load_document_content method**

Add to `document_processor.py` in the DocumentProcessor class (after document_folder_map property):

```python
def load_document_content(self, doc_id: str) -> str | None:
    """Load HTML content for a document from the export folder.

    Args:
        doc_id: The IT Glue document ID (numeric string).

    Returns:
        HTML content as string, or None if document not found or no HTML file.
    """
    folder_info = self.document_folder_map.get(doc_id)
    if folder_info is None:
        return None

    _folder_path, html_file = folder_info
    if html_file is None or not html_file.exists():
        return None

    try:
        return html_file.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return html_file.read_text(encoding="latin-1")
        except Exception as e:
            logger.warning(f"Failed to read HTML file {html_file}: {e}")
            return None
    except Exception as e:
        logger.warning(f"Failed to read HTML file {html_file}: {e}")
        return None
```

**Step 4: Run test to verify it passes**

Run: `cd tools/itglue-migrate && pytest tests/unit/test_document_processor.py::TestLoadDocumentContent -v`
Expected: All 5 tests PASS

**Step 5: Commit**

```bash
cd tools/itglue-migrate
git add src/itglue_migrate/document_processor.py tests/unit/test_document_processor.py
git commit -m "feat(sync): add load_document_content to DocumentProcessor

Loads HTML content from document folders in the export directory,
with UTF-8/latin-1 encoding fallback. Used by sync executor to load
document content before the empty check."
```

---

## Task 3: Fix Document Loading Order in SyncExecutor

**Files:**
- Modify: `tools/itglue-migrate/src/itglue_migrate/sync_executor.py`
- Modify: `tools/itglue-migrate/tests/unit/test_sync_executor.py`

**Step 1: Write the failing test**

```python
# Add to tests/unit/test_sync_executor.py

import pytest
from unittest.mock import Mock, AsyncMock, patch
from itglue_migrate.sync_executor import SyncExecutor, SyncResult
from itglue_migrate.sync_differ import SyncPlan, EntityPlan


class TestExecuteDocumentsLoadOrder:
    """Tests for document content loading from filesystem."""

    @pytest.mark.asyncio
    async def test_loads_html_when_csv_content_empty(self) -> None:
        """Should load HTML from filesystem when CSV content is empty."""
        mock_client = AsyncMock()
        mock_client.create_document = AsyncMock(return_value={"id": "new-doc-uuid"})

        mock_doc_processor = Mock()
        mock_doc_processor.load_document_content = Mock(return_value="<html>Loaded from file</html>")
        mock_doc_processor.document_folder_map = {"123": ("/", None)}
        mock_doc_processor.process_document = AsyncMock(return_value=("Processed content", []))

        executor = SyncExecutor(
            client=mock_client,
            org_id="org-uuid",
            dry_run=False,
            doc_processor=mock_doc_processor,
        )

        plan = SyncPlan(
            documents=EntityPlan(
                to_create=[{"id": "123", "name": "Test Doc", "content": ""}],  # Empty CSV content
            )
        )

        result = await executor.execute(plan)

        # Should have loaded content from filesystem
        mock_doc_processor.load_document_content.assert_called_once_with("123")
        # Should have created the document (not skipped)
        assert result.created.get("documents", 0) == 1
        assert result.skipped.get("documents", 0) == 0

    @pytest.mark.asyncio
    async def test_skips_document_when_both_csv_and_file_empty(self) -> None:
        """Should skip document when CSV is empty AND file content is empty."""
        mock_client = AsyncMock()

        mock_doc_processor = Mock()
        mock_doc_processor.load_document_content = Mock(return_value="")  # Empty file too
        mock_doc_processor.document_folder_map = {"456": ("/", None)}

        executor = SyncExecutor(
            client=mock_client,
            org_id="org-uuid",
            dry_run=False,
            doc_processor=mock_doc_processor,
        )

        plan = SyncPlan(
            documents=EntityPlan(
                to_create=[{"id": "456", "name": "Empty Doc", "content": ""}],
            )
        )

        result = await executor.execute(plan)

        # Should be skipped as empty
        assert result.skipped.get("documents", 0) == 1
        assert result.created.get("documents", 0) == 0

    @pytest.mark.asyncio
    async def test_uses_csv_content_when_present(self) -> None:
        """Should use CSV content directly when it's not empty."""
        mock_client = AsyncMock()
        mock_client.create_document = AsyncMock(return_value={"id": "new-doc-uuid"})

        mock_doc_processor = Mock()
        mock_doc_processor.load_document_content = Mock()  # Should not be called
        mock_doc_processor.document_folder_map = {}
        mock_doc_processor.process_document = AsyncMock(return_value=("Processed", []))

        executor = SyncExecutor(
            client=mock_client,
            org_id="org-uuid",
            dry_run=False,
            doc_processor=mock_doc_processor,
        )

        plan = SyncPlan(
            documents=EntityPlan(
                to_create=[{"id": "789", "name": "Has Content", "content": "<html>CSV content</html>"}],
            )
        )

        result = await executor.execute(plan)

        # Should NOT have called load_document_content since CSV had content
        mock_doc_processor.load_document_content.assert_not_called()
        assert result.created.get("documents", 0) == 1

    @pytest.mark.asyncio
    async def test_uses_folder_path_from_map(self) -> None:
        """Should use folder path from document_folder_map."""
        mock_client = AsyncMock()
        mock_client.create_document = AsyncMock(return_value={"id": "new-doc-uuid"})

        mock_doc_processor = Mock()
        mock_doc_processor.load_document_content = Mock(return_value="<html>content</html>")
        mock_doc_processor.document_folder_map = {"999": ("/_Archive/Projects", None)}
        mock_doc_processor.process_document = AsyncMock(return_value=("Processed", []))

        executor = SyncExecutor(
            client=mock_client,
            org_id="org-uuid",
            dry_run=False,
            doc_processor=mock_doc_processor,
        )

        plan = SyncPlan(
            documents=EntityPlan(
                to_create=[{"id": "999", "name": "Archived Doc", "content": ""}],
            )
        )

        await executor.execute(plan)

        # Check that create_document was called with the correct path
        mock_client.create_document.assert_called_once()
        call_kwargs = mock_client.create_document.call_args.kwargs
        assert call_kwargs["path"] == "/_Archive/Projects"
```

**Step 2: Run test to verify it fails**

Run: `cd tools/itglue-migrate && pytest tests/unit/test_sync_executor.py::TestExecuteDocumentsLoadOrder -v`
Expected: FAIL - documents with empty CSV content are skipped before file loading

**Step 3: Fix _execute_documents in sync_executor.py**

Modify `_execute_documents` method (around line 601). Replace the content loading and empty check logic:

```python
async def _execute_documents(self, plan: SyncPlan, result: SyncResult) -> None:
    """Execute document creation with HTML processing.

    Handles CSV format: {id, name, locator, content, organization_id}
    Transforms to API format with defaults for missing content.
    If DocumentProcessor is available, processes HTML content to clean it,
    extract images, and convert to markdown.
    """
    for entity in plan.documents.to_create:
        itglue_id = str(entity.get("id", ""))
        doc_name = entity.get("name", "Untitled")

        if self.reporter:
            self.reporter.set_current_item(f"Document: {doc_name}")

        # FIRST: Get content - try CSV, then load from filesystem
        raw_content = entity.get("content", "")

        # If CSV content is empty and we have a doc_processor, try loading from file
        if not raw_content and self.doc_processor:
            loaded_content = self.doc_processor.load_document_content(itglue_id)
            if loaded_content:
                raw_content = loaded_content

        # SECOND: Check for empty content (after attempting to load from file)
        if _is_content_empty(raw_content):
            result.skipped["documents"] = result.skipped.get("documents", 0) + 1
            logger.warning(f"Skipping document '{doc_name}': empty content")
            if self.reporter:
                self.reporter.update_progress(skipped=1)
                self.reporter.warning(f"Document '{doc_name}' has empty content")
            continue

        try:
            if self.dry_run:
                result.created["documents"] = (
                    result.created.get("documents", 0) + 1
                )
                if self.reporter:
                    self.reporter.update_progress(succeeded=1)
                continue

            # Get folder path from document_folder_map, fallback to CSV path/locator
            path = entity.get("path") or entity.get("locator") or "/"
            if self.doc_processor:
                folder_info = self.doc_processor.document_folder_map.get(itglue_id)
                if folder_info:
                    folder_path, _ = folder_info
                    path = folder_path

            # Process content through DocumentProcessor if available
            content = raw_content
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

            if bifrost_id := response.get("id"):
                result.id_map[itglue_id] = bifrost_id

                # Upload attachments
                if self.doc_processor and self.export_path:
                    attachment_count = await self._upload_entity_attachments(
                        "documents", itglue_id, bifrost_id
                    )
                    if attachment_count > 0 and self.reporter:
                        self.reporter.info(f"Uploaded {attachment_count} attachments")

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
                self.reporter.error(f"Document '{doc_name}': {e}")
```

**Step 4: Run test to verify it passes**

Run: `cd tools/itglue-migrate && pytest tests/unit/test_sync_executor.py::TestExecuteDocumentsLoadOrder -v`
Expected: All 4 tests PASS

**Step 5: Commit**

```bash
cd tools/itglue-migrate
git add src/itglue_migrate/sync_executor.py tests/unit/test_sync_executor.py
git commit -m "fix(sync): load document HTML before empty check

Previously, documents with empty CSV content were skipped before
attempting to load from HTML files. Now:
1. Try CSV content first
2. If empty, load from filesystem via DocumentProcessor
3. Then check for empty content
4. Use folder path from document_folder_map for correct hierarchy"
```

---

## Task 4: Fix Custom Asset Type State Update

**Files:**
- Modify: `tools/itglue-migrate/src/itglue_migrate/sync_executor.py`
- Modify: `tools/itglue-migrate/tests/unit/test_sync_executor.py`

**Step 1: Write the failing test**

```python
# Add to tests/unit/test_sync_executor.py

class TestCustomAssetTypeStateUpdate:
    """Tests for state update after custom asset type creation."""

    @pytest.mark.asyncio
    async def test_state_updated_after_type_creation(self) -> None:
        """State should be updated with new type after creation."""
        mock_client = AsyncMock()
        mock_client.create_custom_asset_type = AsyncMock(return_value={
            "id": "new-type-uuid",
            "name": "Active Directory",
            "fields": [{"key": "field1", "name": "Field 1", "type": "text"}],
        })

        from itglue_migrate.state_fetcher import ExistingState
        state = ExistingState()
        # State starts empty
        assert state.custom_asset_type_by_name == {}

        executor = SyncExecutor(
            client=mock_client,
            org_id="org-uuid",
            dry_run=False,
            state=state,
        )

        plan = SyncPlan(
            custom_asset_types=EntityPlan(
                to_create=[{
                    "id": "itglue-type-123",
                    "name": "Active Directory",
                    "fields": [{"key": "field1", "name": "Field 1", "type": "text"}],
                }],
            )
        )

        await executor.execute(plan)

        # State should now have the new type
        assert "active directory" in state.custom_asset_type_by_name
        assert state.custom_asset_type_by_name["active directory"] == "new-type-uuid"
        assert "new-type-uuid" in state.custom_asset_types

    @pytest.mark.asyncio
    async def test_custom_asset_can_find_type_created_in_same_run(self) -> None:
        """Custom asset should find type created earlier in same sync run."""
        mock_client = AsyncMock()
        mock_client.create_custom_asset_type = AsyncMock(return_value={
            "id": "new-type-uuid",
            "name": "SSL Certificates",
            "fields": [{"key": "domain", "name": "Domain", "type": "text"}],
        })
        mock_client.create_custom_asset = AsyncMock(return_value={"id": "new-asset-uuid"})

        from itglue_migrate.state_fetcher import ExistingState
        state = ExistingState()

        executor = SyncExecutor(
            client=mock_client,
            org_id="org-uuid",
            dry_run=False,
            state=state,
        )

        plan = SyncPlan(
            custom_asset_types=EntityPlan(
                to_create=[{
                    "id": "type-itglue-id",
                    "name": "SSL Certificates",
                    "fields": [{"key": "domain", "name": "Domain", "type": "text"}],
                }],
            ),
            custom_assets=EntityPlan(
                to_create=[{
                    "id": "asset-itglue-id",
                    "asset_type": "ssl-certificates",
                    "fields": {"domain": "example.com"},
                }],
            ),
        )

        result = await executor.execute(plan)

        # Custom asset should have been created (not skipped)
        assert result.created.get("custom_asset_types", 0) == 1
        assert result.created.get("custom_assets", 0) == 1
        assert result.skipped.get("custom_assets", 0) == 0
```

**Step 2: Run test to verify it fails**

Run: `cd tools/itglue-migrate && pytest tests/unit/test_sync_executor.py::TestCustomAssetTypeStateUpdate -v`
Expected: FAIL - custom_assets will be 0 created, 1 skipped (type not found)

**Step 3: Fix _execute_custom_asset_types in sync_executor.py**

Modify `_execute_custom_asset_types` method (around line 912). Add state update after successful creation:

```python
async def _execute_custom_asset_types(
    self, plan: SyncPlan, result: SyncResult
) -> None:
    """Execute custom asset type creation."""
    for entity in plan.custom_asset_types.to_create:
        try:
            if self.dry_run:
                result.created["custom_asset_types"] = (
                    result.created.get("custom_asset_types", 0) + 1
                )
                continue

            name = entity.get("name", "Unnamed")
            fields = entity.get("fields", [])

            response = await self.client.create_custom_asset_type(
                name=name,
                fields=fields,
                display_field_key=entity.get("display_field_key"),
            )

            itglue_id = str(entity.get("id", ""))
            new_type_id = response.get("id", "")

            if itglue_id and new_type_id:
                result.id_map[itglue_id] = new_type_id

            # UPDATE STATE for subsequent custom asset lookups
            if self.state and new_type_id:
                name_lower = name.lower()
                self.state.custom_asset_type_by_name[name_lower] = new_type_id
                self.state.custom_asset_types[new_type_id] = {
                    "id": new_type_id,
                    "name": name,
                    "fields": fields,
                }

            result.created["custom_asset_types"] = (
                result.created.get("custom_asset_types", 0) + 1
            )

        except Exception as e:
            result.failed["custom_asset_types"] = (
                result.failed.get("custom_asset_types", 0) + 1
            )
            result.errors.append(f"Custom asset type '{entity.get('name')}': {e}")
            logger.warning(f"Failed to create custom asset type: {e}")
```

**Step 4: Run test to verify it passes**

Run: `cd tools/itglue-migrate && pytest tests/unit/test_sync_executor.py::TestCustomAssetTypeStateUpdate -v`
Expected: All 2 tests PASS

**Step 5: Run all sync_executor tests**

Run: `cd tools/itglue-migrate && pytest tests/unit/test_sync_executor.py -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
cd tools/itglue-migrate
git add src/itglue_migrate/sync_executor.py tests/unit/test_sync_executor.py
git commit -m "fix(sync): update state after creating custom asset types

After creating a custom asset type, immediately update state with the
new type ID and field definitions. This allows custom assets created
later in the same sync run to find their type."
```

---

## Task 5: Add Organization Name Uniqueness (Database Migration)

**Files:**
- Create: `api/alembic/versions/20260128_XXXXXX_add_unique_organization_name.py`

**Step 1: Check for duplicate organization names**

Run: `cd api && python -c "from sqlalchemy import create_engine, text; import os; e=create_engine(os.environ['DATABASE_URL']); print(e.execute(text('SELECT name, COUNT(*) as c FROM organizations GROUP BY name HAVING COUNT(*) > 1')).fetchall())"`

Expected: Empty list `[]` (no duplicates). If duplicates exist, resolve them first.

**Step 2: Create the migration file**

Run: `cd api && alembic revision -m "add_unique_organization_name"`

This creates a new migration file. Edit it:

```python
"""add_unique_organization_name

Revision ID: <auto-generated>
Revises: <previous-revision>
Create Date: <auto-generated>
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "<auto-generated>"
down_revision = "<previous-revision>"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the existing non-unique index
    op.drop_index("ix_organizations_name", table_name="organizations")

    # Create unique index to prevent duplicate organization names
    op.create_index(
        "ix_organizations_name",
        "organizations",
        ["name"],
        unique=True,
    )


def downgrade() -> None:
    # Drop unique index
    op.drop_index("ix_organizations_name", table_name="organizations")

    # Recreate non-unique index
    op.create_index(
        "ix_organizations_name",
        "organizations",
        ["name"],
        unique=False,
    )
```

**Step 3: Run the migration**

Run: `cd api && alembic upgrade head`
Expected: Migration applies successfully

**Step 4: Verify the constraint exists**

Run: `cd api && python -c "from sqlalchemy import create_engine, inspect, text; import os; e=create_engine(os.environ['DATABASE_URL']); i=inspect(e); print([idx for idx in i.get_indexes('organizations') if idx['name']=='ix_organizations_name'])"`

Expected: Shows index with `unique: True`

**Step 5: Commit**

```bash
cd api
git add alembic/versions/*add_unique_organization_name*
git commit -m "feat(db): add unique constraint on organization name

Prevents duplicate organization names at the database level.
The existing ix_organizations_name index is replaced with a unique index."
```

---

## Task 6: Add Organization Name Duplicate Check in API

**Files:**
- Modify: `api/src/routers/organizations.py`
- Create/Modify: `api/tests/routers/test_organizations.py`

**Step 1: Write the failing test**

```python
# In api/tests/routers/test_organizations.py

import pytest
from httpx import AsyncClient
from fastapi import status


class TestCreateOrganizationDuplicateName:
    """Tests for duplicate organization name handling."""

    @pytest.mark.asyncio
    async def test_create_duplicate_name_returns_409(
        self, client: AsyncClient, admin_token: str
    ) -> None:
        """Creating org with existing name should return 409 Conflict."""
        # Create first org
        response = await client.post(
            "/api/organizations",
            json={"name": "Unique Test Org"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == status.HTTP_201_CREATED

        # Try to create duplicate
        response = await client.post(
            "/api/organizations",
            json={"name": "Unique Test Org"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == status.HTTP_409_CONFLICT
        assert "already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_duplicate_name_case_insensitive(
        self, client: AsyncClient, admin_token: str
    ) -> None:
        """Duplicate check should be case-insensitive."""
        # Create first org
        response = await client.post(
            "/api/organizations",
            json={"name": "Case Test Org"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == status.HTTP_201_CREATED

        # Try with different case
        response = await client.post(
            "/api/organizations",
            json={"name": "CASE TEST ORG"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        # Note: This test documents expected behavior - may need adjustment
        # based on whether case-insensitive uniqueness is desired
        assert response.status_code in (status.HTTP_201_CREATED, status.HTTP_409_CONFLICT)
```

**Step 2: Run test to verify behavior**

Run: `cd api && pytest tests/routers/test_organizations.py::TestCreateOrganizationDuplicateName -v`
Expected: First test might pass due to DB constraint, but error message won't be user-friendly

**Step 3: Add duplicate check to create_organization**

Modify `api/src/routers/organizations.py`, in the `create_organization` function:

```python
@router.post("", response_model=OrganizationPublic, status_code=status.HTTP_201_CREATED)
async def create_organization(
    org_data: OrganizationCreate,
    current_user: RequireAdmin,
    db: DbSession,
) -> OrganizationPublic:
    """Create a new organization.

    Requires admin role.
    """
    org_repo = OrganizationRepository(db)

    # Check for duplicate name
    existing = await org_repo.get_by_name(org_data.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Organization with name '{org_data.name}' already exists",
        )

    org = Organization(
        name=org_data.name,
        metadata_=org_data.metadata,
        is_enabled=org_data.is_enabled if org_data.is_enabled is not None else True,
    )

    org = await org_repo.create(org)

    # ... rest of function (audit logging, etc.)
```

**Step 4: Run test to verify it passes**

Run: `cd api && pytest tests/routers/test_organizations.py::TestCreateOrganizationDuplicateName -v`
Expected: Test passes with proper 409 response

**Step 5: Commit**

```bash
cd api
git add src/routers/organizations.py tests/routers/test_organizations.py
git commit -m "feat(api): add duplicate name check for organizations

Returns 409 Conflict with user-friendly message when attempting to
create an organization with a name that already exists."
```

---

## Task 7: Add --skip-attachments Flag to Sync Command

**Files:**
- Modify: `tools/itglue-migrate/src/itglue_migrate/cli.py`
- Modify: `tools/itglue-migrate/src/itglue_migrate/sync_executor.py`

**Step 1: Add flag to sync command**

In `cli.py`, find the `sync` command (around line 2816) and add the parameter:

```python
@app.command()
def sync(
    export_path: Annotated[
        Path,
        typer.Option(
            "--export-path",
            "-e",
            help="Path to IT Glue export directory",
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            resolve_path=True,
        ),
    ],
    # ... other existing params ...
    skip_attachments: Annotated[
        bool,
        typer.Option(
            "--skip-attachments",
            help="Skip attachment uploads for faster testing",
        ),
    ] = False,
) -> None:
```

**Step 2: Pass flag to _run_sync and SyncExecutor**

Update the call to `_run_sync()` to pass `skip_attachments`:

```python
exit_code = asyncio.run(
    _run_sync(
        export_path=export_path,
        api_url=effective_api_url,
        token=token,
        target_org=org,
        _all_orgs=all_orgs,
        dry_run=dry_run,
        update_existing=update_existing,
        skip_attachments=skip_attachments,  # Add this
    )
)
```

Update `_run_sync` signature and pass to executor:

```python
async def _run_sync(
    export_path: Path,
    api_url: str,
    token: str,
    target_org: str | None,
    _all_orgs: bool,
    dry_run: bool,
    update_existing: bool,
    skip_attachments: bool = False,  # Add this
) -> int:
```

Then when creating the executor, pass the flag:

```python
executor = SyncExecutor(
    client,
    org_id=org_uuid,
    dry_run=False,
    state=state,
    update_existing=update_existing,
    reporter=reporter,
    doc_processor=doc_processor if not skip_attachments else None,  # Skip doc processor if skipping attachments
    export_path=export_path if not skip_attachments else None,  # Skip export path too
    skip_attachments=skip_attachments,  # Add this
)
```

**Step 3: Add skip_attachments to SyncExecutor**

In `sync_executor.py`, add the parameter to `__init__`:

```python
def __init__(
    self,
    client: BifrostDocsClient,
    org_id: str,
    dry_run: bool = False,
    state: ExistingState | None = None,
    update_existing: bool = False,
    reporter: ProgressReporter | None = None,
    doc_processor: DocumentProcessor | None = None,
    export_path: Path | None = None,
    skip_attachments: bool = False,  # Add this
) -> None:
    # ... existing init code ...
    self.skip_attachments = skip_attachments
```

Then modify `_upload_entity_attachments` to check the flag:

```python
async def _upload_entity_attachments(
    self, entity_type: str, itglue_id: str, bifrost_id: str
) -> int:
    """Upload attachments for an entity."""
    if self.skip_attachments:
        return 0
    # ... rest of method
```

**Step 4: Test the flag**

Run: `cd tools/itglue-migrate && itglue sync --help`
Expected: Shows `--skip-attachments` option in help

**Step 5: Commit**

```bash
cd tools/itglue-migrate
git add src/itglue_migrate/cli.py src/itglue_migrate/sync_executor.py
git commit -m "feat(sync): add --skip-attachments flag for faster testing

Allows skipping attachment uploads during sync for faster iteration
when testing. Attachments can be synced in a subsequent run."
```

---

## Task 8: Run Full Test Suite and Integration Test

**Step 1: Run all itglue-migrate tests**

Run: `cd tools/itglue-migrate && pytest tests/ -v`
Expected: All tests PASS

**Step 2: Run API tests**

Run: `cd api && pytest tests/ -v`
Expected: All tests PASS

**Step 3: Run type checking**

Run: `cd tools/itglue-migrate && pyright`
Expected: No errors

Run: `cd api && pyright`
Expected: No errors

**Step 4: Run linting**

Run: `cd tools/itglue-migrate && ruff check`
Expected: No errors

Run: `cd api && ruff check`
Expected: No errors

**Step 5: Run end-to-end migration test**

Run:
```bash
cd tools/itglue-migrate
itglue sync --export-path /path/to/test-export --org "Covi, Inc." --dry-run
```

Expected output should show:
- Documents: ~500+ to create (not 562 skipped)
- Custom Asset Types: 17 to create
- Custom Assets: 198 to create (not skipped)

**Step 6: Run actual migration**

Run:
```bash
itglue sync --export-path /path/to/test-export --org "Covi, Inc."
```

Expected results:
- Documents: ~500+ created (some legitimately empty)
- Custom Asset Types: 17 created
- Custom Assets: 198 created
- Relationships: Most resolved

**Step 7: Final commit**

```bash
git add -A
git commit -m "chore: ensure all tests pass after sync fixes"
```

---

## Summary

This plan fixes the three critical issues blocking IT Glue migration:

1. **Documents** - Now loads HTML from filesystem before empty check, preserves folder hierarchy
2. **Custom Assets** - State updated after type creation so assets can find their types
3. **Organization Uniqueness** - Database constraint + API check prevents duplicates

Plus the nice-to-have `--skip-attachments` flag for faster testing.

---

Plan complete and saved to `docs/plans/2026-01-28-itglue-sync-feature-parity.md`. Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Which approach?
