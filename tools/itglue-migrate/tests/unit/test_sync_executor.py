"""Tests for sync_executor module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from itglue_migrate.sync_differ import SyncPlan
from itglue_migrate.sync_executor import SyncExecutor, SyncResult


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock API client."""
    client = MagicMock()
    client.create_organization = AsyncMock(return_value={"id": "new-org-uuid"})
    client.create_configuration = AsyncMock(return_value={"id": "new-config-uuid"})
    client.create_location = AsyncMock(return_value={"id": "new-location-uuid"})
    client.create_configuration_type = AsyncMock(return_value={"id": "new-type-uuid"})
    client.create_configuration_status = AsyncMock(return_value={"id": "new-status-uuid"})
    client.create_custom_asset_type = AsyncMock(return_value={"id": "new-cat-uuid"})
    client.create_custom_asset = AsyncMock(return_value={"id": "new-asset-uuid"})
    client.create_document = AsyncMock(return_value={"id": "new-doc-uuid"})
    client.create_password = AsyncMock(return_value={"id": "new-pwd-uuid"})
    client.create_relationship = AsyncMock(return_value={"id": "new-rel-uuid"})
    return client


class TestSyncResult:
    """Tests for SyncResult dataclass."""

    def test_sync_result_defaults(self) -> None:
        """SyncResult should have sensible defaults."""
        result = SyncResult()

        assert result.created == {}
        assert result.updated == {}
        assert result.skipped == {}
        assert result.failed == {}
        assert result.errors == []
        assert result.id_map == {}

    def test_sync_result_with_values(self) -> None:
        """SyncResult should store provided values."""
        result = SyncResult(
            created={"configurations": 5},
            updated={"documents": 2},
            skipped={"passwords": 1},
            failed={"locations": 1},
            errors=["Error 1", "Error 2"],
            id_map={"123": "uuid-abc"},
        )

        assert result.created == {"configurations": 5}
        assert result.updated == {"documents": 2}
        assert result.skipped == {"passwords": 1}
        assert result.failed == {"locations": 1}
        assert result.errors == ["Error 1", "Error 2"]
        assert result.id_map == {"123": "uuid-abc"}


class TestSyncExecutorInit:
    """Tests for SyncExecutor initialization."""

    def test_init_stores_client_and_org_id(self, mock_client: MagicMock) -> None:
        """SyncExecutor should store client and org_id."""
        executor = SyncExecutor(mock_client, org_id="org-uuid", dry_run=False)

        assert executor.client is mock_client
        assert executor.org_id == "org-uuid"
        assert executor.dry_run is False

    def test_init_with_dry_run(self, mock_client: MagicMock) -> None:
        """SyncExecutor should store dry_run setting."""
        executor = SyncExecutor(mock_client, org_id="org-uuid", dry_run=True)

        assert executor.dry_run is True


class TestSyncExecutorExecuteConfigurations:
    """Tests for executing configuration sync."""

    @pytest.mark.asyncio
    async def test_execute_creates_missing_configurations(
        self, mock_client: MagicMock
    ) -> None:
        """SyncExecutor creates configurations marked for creation."""
        plan = SyncPlan()
        plan.configurations.to_create = [
            {"id": "123", "name": "New Server", "organization_id": "org-1"}
        ]

        executor = SyncExecutor(mock_client, org_id="org-uuid", dry_run=False)
        result = await executor.execute(plan)

        assert result.created.get("configurations", 0) == 1
        mock_client.create_configuration.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_multiple_configurations(
        self, mock_client: MagicMock
    ) -> None:
        """SyncExecutor creates multiple configurations."""
        plan = SyncPlan()
        plan.configurations.to_create = [
            {"id": "123", "name": "Server 1"},
            {"id": "456", "name": "Server 2"},
            {"id": "789", "name": "Server 3"},
        ]

        executor = SyncExecutor(mock_client, org_id="org-uuid", dry_run=False)
        result = await executor.execute(plan)

        assert result.created.get("configurations", 0) == 3
        assert mock_client.create_configuration.call_count == 3

    @pytest.mark.asyncio
    async def test_execute_maps_itglue_ids_to_new_uuids(
        self, mock_client: MagicMock
    ) -> None:
        """SyncExecutor should track ID mappings from ITGlue to new UUIDs."""
        mock_client.create_configuration = AsyncMock(return_value={"id": "new-uuid-abc"})
        plan = SyncPlan()
        plan.configurations.to_create = [
            {"id": "itglue-123", "name": "Server"}
        ]

        executor = SyncExecutor(mock_client, org_id="org-uuid", dry_run=False)
        result = await executor.execute(plan)

        assert "itglue-123" in result.id_map
        assert result.id_map["itglue-123"] == "new-uuid-abc"


class TestSyncExecutorDryRun:
    """Tests for dry run mode."""

    @pytest.mark.asyncio
    async def test_dry_run_does_not_call_api(self, mock_client: MagicMock) -> None:
        """SyncExecutor in dry_run mode doesn't make API calls."""
        plan = SyncPlan()
        plan.configurations.to_create = [
            {"id": "123", "name": "New Server", "organization_id": "org-1"}
        ]

        executor = SyncExecutor(mock_client, org_id="org-uuid", dry_run=True)
        result = await executor.execute(plan)

        assert result.created.get("configurations", 0) == 1  # Still counts
        mock_client.create_configuration.assert_not_called()

    @pytest.mark.asyncio
    async def test_dry_run_counts_all_entity_types(
        self, mock_client: MagicMock
    ) -> None:
        """Dry run should count all entity types without API calls."""
        plan = SyncPlan()
        plan.configurations.to_create = [{"id": "1", "name": "Config"}]
        plan.locations.to_create = [{"id": "2", "name": "Location"}]
        plan.documents.to_create = [{"id": "3", "name": "Document", "content": "Real content"}]
        plan.passwords.to_create = [{"id": "4", "name": "Password", "password": "secret123"}]

        executor = SyncExecutor(mock_client, org_id="org-uuid", dry_run=True)
        result = await executor.execute(plan)

        assert result.created.get("configurations", 0) == 1
        assert result.created.get("locations", 0) == 1
        assert result.created.get("documents", 0) == 1
        assert result.created.get("passwords", 0) == 1

        # No API calls in dry run
        mock_client.create_configuration.assert_not_called()
        mock_client.create_location.assert_not_called()
        mock_client.create_document.assert_not_called()
        mock_client.create_password.assert_not_called()


class TestSyncExecutorExecuteLocations:
    """Tests for executing location sync."""

    @pytest.mark.asyncio
    async def test_execute_creates_locations(self, mock_client: MagicMock) -> None:
        """SyncExecutor creates locations marked for creation."""
        plan = SyncPlan()
        plan.locations.to_create = [
            {"id": "loc-123", "name": "Main Office", "address_1": "123 Main St"}
        ]

        executor = SyncExecutor(mock_client, org_id="org-uuid", dry_run=False)
        result = await executor.execute(plan)

        assert result.created.get("locations", 0) == 1
        mock_client.create_location.assert_called_once()


class TestSyncExecutorExecuteDocuments:
    """Tests for executing document sync."""

    @pytest.mark.asyncio
    async def test_execute_creates_documents(self, mock_client: MagicMock) -> None:
        """SyncExecutor creates documents marked for creation."""
        plan = SyncPlan()
        plan.documents.to_create = [
            {"id": "doc-123", "name": "Runbook", "path": "/docs", "content": "# Test"}
        ]

        executor = SyncExecutor(mock_client, org_id="org-uuid", dry_run=False)
        result = await executor.execute(plan)

        assert result.created.get("documents", 0) == 1
        mock_client.create_document.assert_called_once()


class TestSyncExecutorExecutePasswords:
    """Tests for executing password sync."""

    @pytest.mark.asyncio
    async def test_execute_creates_passwords(self, mock_client: MagicMock) -> None:
        """SyncExecutor creates passwords marked for creation."""
        plan = SyncPlan()
        plan.passwords.to_create = [
            {"id": "pwd-123", "name": "Admin Password", "password": "secret123"}
        ]

        executor = SyncExecutor(mock_client, org_id="org-uuid", dry_run=False)
        result = await executor.execute(plan)

        assert result.created.get("passwords", 0) == 1
        mock_client.create_password.assert_called_once()


class TestSyncExecutorExecuteOrganizations:
    """Tests for executing organization sync."""

    @pytest.mark.asyncio
    async def test_execute_creates_organizations(self, mock_client: MagicMock) -> None:
        """SyncExecutor creates organizations marked for creation."""
        plan = SyncPlan()
        plan.organizations.to_create = [
            {"name": "New Org", "metadata": {"itglue_id": "org-123"}}
        ]

        executor = SyncExecutor(mock_client, org_id="", dry_run=False)
        result = await executor.execute(plan)

        assert result.created.get("organizations", 0) == 1
        mock_client.create_organization.assert_called_once_with(
            name="New Org",
            is_enabled=True,
            metadata={"itglue_id": "org-123"},
        )

    @pytest.mark.asyncio
    async def test_execute_maps_org_itglue_ids(self, mock_client: MagicMock) -> None:
        """SyncExecutor maps ITGlue org IDs to new UUIDs."""
        plan = SyncPlan()
        plan.organizations.to_create = [
            {"name": "New Org", "metadata": {"itglue_id": "org-123"}}
        ]

        executor = SyncExecutor(mock_client, org_id="", dry_run=False)
        result = await executor.execute(plan)

        assert result.id_map.get("org-123") == "new-org-uuid"

    @pytest.mark.asyncio
    async def test_execute_organizations_dry_run(self, mock_client: MagicMock) -> None:
        """SyncExecutor dry run counts organizations without API calls."""
        plan = SyncPlan()
        plan.organizations.to_create = [
            {"name": "Org 1", "metadata": {"itglue_id": "1"}},
            {"name": "Org 2", "metadata": {"itglue_id": "2"}},
        ]

        executor = SyncExecutor(mock_client, org_id="", dry_run=True)
        result = await executor.execute(plan)

        assert result.created.get("organizations", 0) == 2
        mock_client.create_organization.assert_not_called()


class TestSyncExecutorExecuteConfigTypes:
    """Tests for executing configuration type sync."""

    @pytest.mark.asyncio
    async def test_execute_creates_config_types(self, mock_client: MagicMock) -> None:
        """SyncExecutor creates configuration types marked for creation."""
        plan = SyncPlan()
        plan.config_types.to_create = [
            {"id": "type-123", "name": "Server"}
        ]

        executor = SyncExecutor(mock_client, org_id="org-uuid", dry_run=False)
        result = await executor.execute(plan)

        assert result.created.get("config_types", 0) == 1
        mock_client.create_configuration_type.assert_called_once()


class TestSyncExecutorExecuteConfigStatuses:
    """Tests for executing configuration status sync."""

    @pytest.mark.asyncio
    async def test_execute_creates_config_statuses(
        self, mock_client: MagicMock
    ) -> None:
        """SyncExecutor creates configuration statuses marked for creation."""
        plan = SyncPlan()
        plan.config_statuses.to_create = [
            {"id": "status-123", "name": "Active"}
        ]

        executor = SyncExecutor(mock_client, org_id="org-uuid", dry_run=False)
        result = await executor.execute(plan)

        assert result.created.get("config_statuses", 0) == 1
        mock_client.create_configuration_status.assert_called_once()


class TestSyncExecutorExecuteCustomAssetTypes:
    """Tests for executing custom asset type sync."""

    @pytest.mark.asyncio
    async def test_execute_creates_custom_asset_types(
        self, mock_client: MagicMock
    ) -> None:
        """SyncExecutor creates custom asset types marked for creation."""
        plan = SyncPlan()
        plan.custom_asset_types.to_create = [
            {"id": "cat-123", "name": "License", "fields": []}
        ]

        executor = SyncExecutor(mock_client, org_id="org-uuid", dry_run=False)
        result = await executor.execute(plan)

        assert result.created.get("custom_asset_types", 0) == 1
        mock_client.create_custom_asset_type.assert_called_once()


class TestSyncExecutorExecuteCustomAssets:
    """Tests for executing custom asset sync."""

    @pytest.mark.asyncio
    async def test_execute_creates_custom_assets(self, mock_client: MagicMock) -> None:
        """SyncExecutor creates custom assets marked for creation."""
        plan = SyncPlan()
        plan.custom_assets.to_create = [
            {"id": "asset-123", "type_id": "cat-uuid", "values": {"name": "MS Office"}}
        ]

        executor = SyncExecutor(mock_client, org_id="org-uuid", dry_run=False)
        result = await executor.execute(plan)

        assert result.created.get("custom_assets", 0) == 1
        mock_client.create_custom_asset.assert_called_once()


class TestSyncExecutorExecuteRelationships:
    """Tests for executing relationship sync."""

    @pytest.mark.asyncio
    async def test_execute_creates_relationships(self, mock_client: MagicMock) -> None:
        """SyncExecutor creates relationships marked for creation."""
        plan = SyncPlan()
        plan.relationships.to_create = [
            {
                "source_type": "configuration",
                "source_id": "config-uuid",
                "target_type": "password",
                "target_id": "pwd-uuid",
            }
        ]

        executor = SyncExecutor(mock_client, org_id="org-uuid", dry_run=False)
        result = await executor.execute(plan)

        assert result.created.get("relationships", 0) == 1
        mock_client.create_relationship.assert_called_once()


class TestSyncExecutorErrorHandling:
    """Tests for error handling during sync execution."""

    @pytest.mark.asyncio
    async def test_execute_records_api_errors(self, mock_client: MagicMock) -> None:
        """SyncExecutor should record errors and continue."""
        mock_client.create_configuration = AsyncMock(
            side_effect=Exception("API Error: Server unavailable")
        )
        plan = SyncPlan()
        plan.configurations.to_create = [
            {"id": "123", "name": "Server"}
        ]

        executor = SyncExecutor(mock_client, org_id="org-uuid", dry_run=False)
        result = await executor.execute(plan)

        assert result.failed.get("configurations", 0) == 1
        assert len(result.errors) == 1
        assert "API Error" in result.errors[0]

    @pytest.mark.asyncio
    async def test_execute_continues_after_error(self, mock_client: MagicMock) -> None:
        """SyncExecutor should continue processing after an error."""
        # First call fails, second succeeds
        mock_client.create_configuration = AsyncMock(
            side_effect=[Exception("Error"), {"id": "new-uuid"}]
        )
        plan = SyncPlan()
        plan.configurations.to_create = [
            {"id": "1", "name": "Server 1"},
            {"id": "2", "name": "Server 2"},
        ]

        executor = SyncExecutor(mock_client, org_id="org-uuid", dry_run=False)
        result = await executor.execute(plan)

        assert result.created.get("configurations", 0) == 1
        assert result.failed.get("configurations", 0) == 1
        assert len(result.errors) == 1


class TestSyncExecutorEmptyPlan:
    """Tests for handling empty sync plans."""

    @pytest.mark.asyncio
    async def test_execute_empty_plan_returns_empty_result(
        self, mock_client: MagicMock
    ) -> None:
        """SyncExecutor with empty plan should return empty result."""
        plan = SyncPlan()

        executor = SyncExecutor(mock_client, org_id="org-uuid", dry_run=False)
        result = await executor.execute(plan)

        assert result.created == {}
        assert result.failed == {}
        assert result.errors == []

        # No API calls
        mock_client.create_configuration.assert_not_called()
        mock_client.create_location.assert_not_called()


class TestSyncExecutorCellWrites:
    """Tests for executing cell writes (embedded passwords in custom assets)."""

    @pytest.fixture
    def mock_state(self) -> MagicMock:
        """Create a mock ExistingState."""
        from itglue_migrate.state_fetcher import ExistingState

        state = ExistingState()
        state.custom_asset_by_itglue_id = {
            "asset-123": "asset-uuid-abc",
            "asset-456": "asset-uuid-def",
        }
        state.custom_assets = {
            "asset-uuid-abc": {
                "id": "asset-uuid-abc",
                "type_id": "type-uuid-1",
                "values": {"name": "Test Asset"},
            },
            "asset-uuid-def": {
                "id": "asset-uuid-def",
                "type_id": "type-uuid-2",
                "values": {"name": "Another Asset"},
            },
        }
        return state

    @pytest.mark.asyncio
    async def test_execute_cell_writes(
        self, mock_client: MagicMock, mock_state: MagicMock
    ) -> None:
        """SyncExecutor updates custom asset fields with password values."""
        mock_client.update_custom_asset = AsyncMock(return_value={"id": "asset-uuid-abc"})

        plan = SyncPlan()
        plan.passwords.cell_writes = [
            {
                "id": "pwd-1",
                "name": "api_key",
                "password": "secret-value-123",
                "resource_type": "FlexibleAsset::StructuredData::Cell",
                "resource_id": "asset-123",
            }
        ]

        executor = SyncExecutor(
            mock_client, org_id="org-uuid", dry_run=False, state=mock_state
        )
        result = await executor.execute(plan)

        assert result.created.get("cell_writes", 0) == 1
        mock_client.update_custom_asset.assert_called_once_with(
            org_id="org-uuid",
            type_id="type-uuid-1",
            asset_id="asset-uuid-abc",
            values={"api_key": "secret-value-123"},
        )

    @pytest.mark.asyncio
    async def test_execute_cell_writes_skipped_without_state(
        self, mock_client: MagicMock
    ) -> None:
        """SyncExecutor skips cell_writes when no state is provided."""
        plan = SyncPlan()
        plan.passwords.cell_writes = [
            {
                "id": "pwd-1",
                "name": "api_key",
                "password": "secret-value",
                "resource_type": "FlexibleAsset::StructuredData::Cell",
                "resource_id": "asset-123",
            }
        ]

        executor = SyncExecutor(
            mock_client, org_id="org-uuid", dry_run=False, state=None
        )
        result = await executor.execute(plan)

        assert result.skipped.get("cell_writes", 0) == 1
        assert result.created.get("cell_writes", 0) == 0

    @pytest.mark.asyncio
    async def test_execute_cell_writes_dry_run(
        self, mock_client: MagicMock, mock_state: MagicMock
    ) -> None:
        """SyncExecutor counts cell_writes in dry run mode without API calls."""
        mock_client.update_custom_asset = AsyncMock()

        plan = SyncPlan()
        plan.passwords.cell_writes = [
            {
                "id": "pwd-1",
                "name": "api_key",
                "password": "secret-value",
                "resource_type": "FlexibleAsset::StructuredData::Cell",
                "resource_id": "asset-123",
            }
        ]

        executor = SyncExecutor(
            mock_client, org_id="org-uuid", dry_run=True, state=mock_state
        )
        result = await executor.execute(plan)

        assert result.created.get("cell_writes", 0) == 1
        mock_client.update_custom_asset.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_cell_writes_missing_asset(
        self, mock_client: MagicMock, mock_state: MagicMock
    ) -> None:
        """SyncExecutor skips cell_writes when custom asset not found."""
        plan = SyncPlan()
        plan.passwords.cell_writes = [
            {
                "id": "pwd-1",
                "name": "api_key",
                "password": "secret-value",
                "resource_type": "FlexibleAsset::StructuredData::Cell",
                "resource_id": "nonexistent-asset",
            }
        ]

        executor = SyncExecutor(
            mock_client, org_id="org-uuid", dry_run=False, state=mock_state
        )
        result = await executor.execute(plan)

        assert result.skipped.get("cell_writes", 0) == 1
        assert result.created.get("cell_writes", 0) == 0


class TestSyncExecutorRowCreates:
    """Tests for executing row creates (passwords with relationships)."""

    @pytest.fixture
    def mock_state(self) -> MagicMock:
        """Create a mock ExistingState."""
        from itglue_migrate.state_fetcher import ExistingState

        state = ExistingState()
        state.custom_asset_by_itglue_id = {
            "asset-123": "asset-uuid-abc",
        }
        return state

    @pytest.mark.asyncio
    async def test_execute_row_creates_password_and_relationship(
        self, mock_client: MagicMock, mock_state: MagicMock
    ) -> None:
        """SyncExecutor creates password and relationship for row_creates."""
        mock_client.create_password = AsyncMock(return_value={"id": "new-pwd-uuid"})
        mock_client.create_relationship = AsyncMock(return_value={"id": "new-rel-uuid"})

        plan = SyncPlan()
        plan.passwords.row_creates = [
            {
                "id": "pwd-1",
                "name": "Row Password",
                "password": "secret-value",
                "username": "admin",
                "resource_type": "FlexibleAsset::StructuredData::Row",
                "resource_id": "asset-123",
            }
        ]

        executor = SyncExecutor(
            mock_client, org_id="org-uuid", dry_run=False, state=mock_state
        )
        result = await executor.execute(plan)

        assert result.created.get("passwords", 0) == 1
        assert result.created.get("relationships", 0) == 1
        mock_client.create_password.assert_called_once()
        mock_client.create_relationship.assert_called_once_with(
            org_id="org-uuid",
            source_type="password",
            source_id="new-pwd-uuid",
            target_type="custom_asset",
            target_id="asset-uuid-abc",
        )

    @pytest.mark.asyncio
    async def test_execute_row_creates_dry_run(
        self, mock_client: MagicMock, mock_state: MagicMock
    ) -> None:
        """SyncExecutor counts row_creates in dry run mode without API calls."""
        plan = SyncPlan()
        plan.passwords.row_creates = [
            {
                "id": "pwd-1",
                "name": "Row Password",
                "password": "secret-value",
                "resource_type": "FlexibleAsset::StructuredData::Row",
                "resource_id": "asset-123",
            }
        ]

        executor = SyncExecutor(
            mock_client, org_id="org-uuid", dry_run=True, state=mock_state
        )
        result = await executor.execute(plan)

        assert result.created.get("passwords", 0) == 1
        assert result.created.get("relationships", 0) == 1
        mock_client.create_password.assert_not_called()
        mock_client.create_relationship.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_row_creates_without_state(
        self, mock_client: MagicMock
    ) -> None:
        """SyncExecutor creates password but not relationship without state."""
        mock_client.create_password = AsyncMock(return_value={"id": "new-pwd-uuid"})

        plan = SyncPlan()
        plan.passwords.row_creates = [
            {
                "id": "pwd-1",
                "name": "Row Password",
                "password": "secret-value",
                "resource_type": "FlexibleAsset::StructuredData::Row",
                "resource_id": "asset-123",
            }
        ]

        executor = SyncExecutor(
            mock_client, org_id="org-uuid", dry_run=False, state=None
        )
        result = await executor.execute(plan)

        assert result.created.get("passwords", 0) == 1
        # No relationship created without state
        assert result.created.get("relationships", 0) == 0
        mock_client.create_password.assert_called_once()
        mock_client.create_relationship.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_row_creates_maps_id(
        self, mock_client: MagicMock, mock_state: MagicMock
    ) -> None:
        """SyncExecutor maps ITGlue ID to new UUID for row_creates."""
        mock_client.create_password = AsyncMock(return_value={"id": "new-pwd-uuid"})
        mock_client.create_relationship = AsyncMock(return_value={"id": "new-rel-uuid"})

        plan = SyncPlan()
        plan.passwords.row_creates = [
            {
                "id": "itglue-pwd-123",
                "name": "Row Password",
                "password": "secret-value",
                "resource_type": "FlexibleAsset::StructuredData::Row",
                "resource_id": "asset-123",
            }
        ]

        executor = SyncExecutor(
            mock_client, org_id="org-uuid", dry_run=False, state=mock_state
        )
        result = await executor.execute(plan)

        assert "itglue-pwd-123" in result.id_map
        assert result.id_map["itglue-pwd-123"] == "new-pwd-uuid"


class TestSyncExecutorUpdateExisting:
    """Tests for update_existing functionality."""

    @pytest.fixture
    def mock_client_with_updates(self) -> MagicMock:
        """Create a mock API client with update methods."""
        client = MagicMock()
        client.create_configuration = AsyncMock(return_value={"id": "new-config-uuid"})
        client.update_configuration = AsyncMock(return_value={"id": "updated-config-uuid"})
        client.create_location = AsyncMock(return_value={"id": "new-location-uuid"})
        client.update_location = AsyncMock(return_value={"id": "updated-location-uuid"})
        client.create_document = AsyncMock(return_value={"id": "new-doc-uuid"})
        client.update_document = AsyncMock(return_value={"id": "updated-doc-uuid"})
        client.create_password = AsyncMock(return_value={"id": "new-pwd-uuid"})
        client.update_password = AsyncMock(return_value={"id": "updated-pwd-uuid"})
        client.create_configuration_type = AsyncMock(return_value={"id": "new-type-uuid"})
        client.create_configuration_status = AsyncMock(return_value={"id": "new-status-uuid"})
        client.create_custom_asset_type = AsyncMock(return_value={"id": "new-cat-uuid"})
        client.create_custom_asset = AsyncMock(return_value={"id": "new-asset-uuid"})
        client.create_relationship = AsyncMock(return_value={"id": "new-rel-uuid"})
        return client

    @pytest.mark.asyncio
    async def test_updates_skipped_when_update_existing_false(
        self, mock_client_with_updates: MagicMock
    ) -> None:
        """SyncExecutor skips updates when update_existing=False."""
        plan = SyncPlan()
        plan.configurations.to_update = [
            {"itglue_id": "123", "uuid": "config-uuid", "changes": {"name": "New Name"}}
        ]

        executor = SyncExecutor(
            mock_client_with_updates,
            org_id="org-uuid",
            dry_run=False,
            update_existing=False,
        )
        result = await executor.execute(plan)

        assert result.updated.get("configurations", 0) == 0
        mock_client_with_updates.update_configuration.assert_not_called()

    @pytest.mark.asyncio
    async def test_updates_executed_when_update_existing_true(
        self, mock_client_with_updates: MagicMock
    ) -> None:
        """SyncExecutor executes updates when update_existing=True."""
        plan = SyncPlan()
        plan.configurations.to_update = [
            {"itglue_id": "123", "uuid": "config-uuid", "changes": {"name": "New Name"}}
        ]

        executor = SyncExecutor(
            mock_client_with_updates,
            org_id="org-uuid",
            dry_run=False,
            update_existing=True,
        )
        result = await executor.execute(plan)

        assert result.updated.get("configurations", 0) == 1
        mock_client_with_updates.update_configuration.assert_called_once_with(
            org_id="org-uuid",
            config_id="config-uuid",
            name="New Name",
        )

    @pytest.mark.asyncio
    async def test_update_configurations_with_multiple_changes(
        self, mock_client_with_updates: MagicMock
    ) -> None:
        """SyncExecutor passes all changed fields to update API."""
        plan = SyncPlan()
        plan.configurations.to_update = [
            {
                "itglue_id": "123",
                "uuid": "config-uuid",
                "changes": {
                    "name": "New Name",
                    "serial_number": "NEW-SN",
                    "notes": "Updated notes",
                },
            }
        ]

        executor = SyncExecutor(
            mock_client_with_updates,
            org_id="org-uuid",
            dry_run=False,
            update_existing=True,
        )
        result = await executor.execute(plan)

        assert result.updated.get("configurations", 0) == 1
        mock_client_with_updates.update_configuration.assert_called_once_with(
            org_id="org-uuid",
            config_id="config-uuid",
            name="New Name",
            serial_number="NEW-SN",
            notes="Updated notes",
        )

    @pytest.mark.asyncio
    async def test_update_locations(
        self, mock_client_with_updates: MagicMock
    ) -> None:
        """SyncExecutor updates locations."""
        plan = SyncPlan()
        plan.locations.to_update = [
            {
                "itglue_id": "456",
                "uuid": "loc-uuid",
                "changes": {"name": "New Location", "address_1": "New Address"},
            }
        ]

        executor = SyncExecutor(
            mock_client_with_updates,
            org_id="org-uuid",
            dry_run=False,
            update_existing=True,
        )
        result = await executor.execute(plan)

        assert result.updated.get("locations", 0) == 1
        mock_client_with_updates.update_location.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_documents(
        self, mock_client_with_updates: MagicMock
    ) -> None:
        """SyncExecutor updates documents."""
        plan = SyncPlan()
        plan.documents.to_update = [
            {
                "itglue_id": "789",
                "uuid": "doc-uuid",
                "changes": {"content": "New content"},
            }
        ]

        executor = SyncExecutor(
            mock_client_with_updates,
            org_id="org-uuid",
            dry_run=False,
            update_existing=True,
        )
        result = await executor.execute(plan)

        assert result.updated.get("documents", 0) == 1
        mock_client_with_updates.update_document.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_passwords(
        self, mock_client_with_updates: MagicMock
    ) -> None:
        """SyncExecutor updates passwords."""
        plan = SyncPlan()
        plan.passwords.to_update = [
            {
                "itglue_id": "pwd-1",
                "uuid": "pwd-uuid",
                "changes": {"name": "New Password Name", "password": "newpass123"},
            }
        ]

        executor = SyncExecutor(
            mock_client_with_updates,
            org_id="org-uuid",
            dry_run=False,
            update_existing=True,
        )
        result = await executor.execute(plan)

        assert result.updated.get("passwords", 0) == 1
        mock_client_with_updates.update_password.assert_called_once()

    @pytest.mark.asyncio
    async def test_dry_run_counts_updates_without_api_calls(
        self, mock_client_with_updates: MagicMock
    ) -> None:
        """Dry run mode counts updates but doesn't call API."""
        plan = SyncPlan()
        plan.configurations.to_update = [
            {"itglue_id": "1", "uuid": "uuid-1", "changes": {"name": "New 1"}},
            {"itglue_id": "2", "uuid": "uuid-2", "changes": {"name": "New 2"}},
        ]
        plan.locations.to_update = [
            {"itglue_id": "3", "uuid": "uuid-3", "changes": {"name": "Loc 1"}},
        ]

        executor = SyncExecutor(
            mock_client_with_updates,
            org_id="org-uuid",
            dry_run=True,
            update_existing=True,
        )
        result = await executor.execute(plan)

        assert result.updated.get("configurations", 0) == 2
        assert result.updated.get("locations", 0) == 1
        mock_client_with_updates.update_configuration.assert_not_called()
        mock_client_with_updates.update_location.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_error_handling(
        self, mock_client_with_updates: MagicMock
    ) -> None:
        """SyncExecutor records errors during updates and continues."""
        mock_client_with_updates.update_configuration = AsyncMock(
            side_effect=Exception("Update failed")
        )
        plan = SyncPlan()
        plan.configurations.to_update = [
            {"itglue_id": "123", "uuid": "config-uuid", "changes": {"name": "New Name"}}
        ]

        executor = SyncExecutor(
            mock_client_with_updates,
            org_id="org-uuid",
            dry_run=False,
            update_existing=True,
        )
        result = await executor.execute(plan)

        assert result.failed.get("configurations", 0) == 1
        assert len(result.errors) == 1
        assert "Update failed" in result.errors[0]

    @pytest.mark.asyncio
    async def test_mixed_creates_and_updates(
        self, mock_client_with_updates: MagicMock
    ) -> None:
        """SyncExecutor handles both creates and updates in same plan."""
        plan = SyncPlan()
        plan.configurations.to_create = [
            {"id": "new-1", "name": "New Config"}
        ]
        plan.configurations.to_update = [
            {"itglue_id": "123", "uuid": "config-uuid", "changes": {"name": "Updated"}}
        ]

        executor = SyncExecutor(
            mock_client_with_updates,
            org_id="org-uuid",
            dry_run=False,
            update_existing=True,
        )
        result = await executor.execute(plan)

        assert result.created.get("configurations", 0) == 1
        assert result.updated.get("configurations", 0) == 1
        mock_client_with_updates.create_configuration.assert_called_once()
        mock_client_with_updates.update_configuration.assert_called_once()


class TestCoerceFieldValue:
    """Tests for _coerce_field_value method."""

    @pytest.fixture
    def executor(self, mock_client: MagicMock) -> SyncExecutor:
        """Create a SyncExecutor for testing."""
        return SyncExecutor(mock_client, org_id="org-uuid", dry_run=False)

    def test_coerce_number_from_string_int(self, executor: SyncExecutor) -> None:
        """Coerce string to integer."""
        assert executor._coerce_field_value("42", "number") == 42
        assert executor._coerce_field_value("0", "number") == 0
        assert executor._coerce_field_value("-5", "number") == -5

    def test_coerce_number_from_string_float(self, executor: SyncExecutor) -> None:
        """Coerce string to float."""
        assert executor._coerce_field_value("3.14", "number") == 3.14
        assert executor._coerce_field_value("0.0", "number") == 0.0

    def test_coerce_number_keeps_numeric_types(self, executor: SyncExecutor) -> None:
        """Already numeric types are kept as-is."""
        assert executor._coerce_field_value(42, "number") == 42
        assert executor._coerce_field_value(3.14, "number") == 3.14

    def test_coerce_number_returns_none_for_invalid(
        self, executor: SyncExecutor
    ) -> None:
        """Invalid number strings return None."""
        assert executor._coerce_field_value("abc", "number") is None
        assert executor._coerce_field_value("", "number") is None
        assert executor._coerce_field_value("  ", "number") is None

    def test_coerce_checkbox_from_string(self, executor: SyncExecutor) -> None:
        """Coerce string to boolean for checkbox fields."""
        # True values
        assert executor._coerce_field_value("true", "checkbox") is True
        assert executor._coerce_field_value("True", "checkbox") is True
        assert executor._coerce_field_value("yes", "checkbox") is True
        assert executor._coerce_field_value("YES", "checkbox") is True
        assert executor._coerce_field_value("1", "checkbox") is True
        assert executor._coerce_field_value("on", "checkbox") is True

        # False values
        assert executor._coerce_field_value("false", "checkbox") is False
        assert executor._coerce_field_value("False", "checkbox") is False
        assert executor._coerce_field_value("no", "checkbox") is False
        assert executor._coerce_field_value("NO", "checkbox") is False
        assert executor._coerce_field_value("0", "checkbox") is False
        assert executor._coerce_field_value("off", "checkbox") is False
        assert executor._coerce_field_value("", "checkbox") is False

    def test_coerce_checkbox_keeps_bool(self, executor: SyncExecutor) -> None:
        """Boolean values are kept as-is for checkbox fields."""
        assert executor._coerce_field_value(True, "checkbox") is True
        assert executor._coerce_field_value(False, "checkbox") is False

    def test_coerce_text_keeps_string(self, executor: SyncExecutor) -> None:
        """Text type keeps values as strings."""
        assert executor._coerce_field_value("Hello", "text") == "Hello"
        assert executor._coerce_field_value("42", "text") == "42"

    def test_coerce_textbox_keeps_string(self, executor: SyncExecutor) -> None:
        """Textbox type keeps values as strings."""
        assert executor._coerce_field_value("Long text", "textbox") == "Long text"

    def test_coerce_select_keeps_string(self, executor: SyncExecutor) -> None:
        """Select type keeps values as strings."""
        assert executor._coerce_field_value("Option A", "select") == "Option A"

    def test_coerce_date_keeps_string(self, executor: SyncExecutor) -> None:
        """Date type keeps values as strings."""
        assert executor._coerce_field_value("2024-01-15", "date") == "2024-01-15"

    def test_coerce_none_returns_none(self, executor: SyncExecutor) -> None:
        """None values return None for all types."""
        assert executor._coerce_field_value(None, "text") is None
        assert executor._coerce_field_value(None, "number") is None
        assert executor._coerce_field_value(None, "checkbox") is None


class TestCustomAssetFieldFiltering:
    """Tests for custom asset field filtering and transformation."""

    @pytest.fixture
    def mock_state(self) -> MagicMock:
        """Create a mock state with custom asset type definitions."""
        state = MagicMock()
        state.custom_asset_type_by_name = {"test type": "type-uuid"}
        state.custom_asset_types = {
            "type-uuid": {
                "id": "type-uuid",
                "name": "Test Type",
                "fields": [
                    {"name": "Name", "key": "name", "type": "text"},
                    {"name": "Count", "key": "count", "type": "number"},
                    {"name": "Active", "key": "active", "type": "checkbox"},
                ],
            }
        }
        return state

    @pytest.mark.asyncio
    async def test_custom_asset_filters_unknown_fields(
        self, mock_client: MagicMock, mock_state: MagicMock
    ) -> None:
        """Unknown fields from CSV are filtered out."""
        plan = SyncPlan()
        plan.custom_assets.to_create = [
            {
                "id": "123",
                "asset_type": "test type",
                "fields": {
                    "Name": "Test Asset",
                    "Count": "5",
                    "Unknown Field": "should be ignored",
                    "Another Unknown": "also ignored",
                },
            }
        ]

        executor = SyncExecutor(
            mock_client, org_id="org-uuid", dry_run=False, state=mock_state
        )
        await executor.execute(plan)

        # Check the values passed to create_custom_asset
        call_kwargs = mock_client.create_custom_asset.call_args.kwargs
        values = call_kwargs.get("values", {})

        # Valid fields should be present
        assert "name" in values
        assert "count" in values

        # Unknown fields should be filtered out
        assert "unknown_field" not in values
        assert "another_unknown" not in values

    @pytest.mark.asyncio
    async def test_custom_asset_coerces_field_types(
        self, mock_client: MagicMock, mock_state: MagicMock
    ) -> None:
        """Field values are coerced to correct types."""
        plan = SyncPlan()
        plan.custom_assets.to_create = [
            {
                "id": "123",
                "asset_type": "test type",
                "fields": {
                    "Name": "Test Asset",
                    "Count": "42",  # String that should become int
                    "Active": "yes",  # String that should become bool
                },
            }
        ]

        executor = SyncExecutor(
            mock_client, org_id="org-uuid", dry_run=False, state=mock_state
        )
        await executor.execute(plan)

        call_kwargs = mock_client.create_custom_asset.call_args.kwargs
        values = call_kwargs.get("values", {})

        # Count should be coerced to int
        assert values["count"] == 42
        assert isinstance(values["count"], int)

        # Active should be coerced to bool
        assert values["active"] is True
        assert isinstance(values["active"], bool)


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

    @pytest.mark.asyncio
    async def test_creates_document_with_real_content(
        self, mock_client: MagicMock
    ) -> None:
        """Documents with real content after stripping HTML are created."""
        plan = SyncPlan()
        plan.documents.to_create = [
            {"id": "123", "name": "Real Doc", "content": "<p>Hello World</p>"},
        ]

        executor = SyncExecutor(mock_client, org_id="org-uuid", dry_run=False)
        result = await executor.execute(plan)

        assert result.created.get("documents", 0) == 1
        assert result.skipped.get("documents", 0) == 0
        mock_client.create_document.assert_called_once()

    @pytest.mark.asyncio
    async def test_creates_password_with_real_value(
        self, mock_client: MagicMock
    ) -> None:
        """Passwords with real password values are created."""
        plan = SyncPlan()
        plan.passwords.to_create = [
            {"id": "123", "name": "Real Password", "password": "secret123"},
        ]

        executor = SyncExecutor(mock_client, org_id="org-uuid", dry_run=False)
        result = await executor.execute(plan)

        assert result.created.get("passwords", 0) == 1
        assert result.skipped.get("passwords", 0) == 0
        mock_client.create_password.assert_called_once()
