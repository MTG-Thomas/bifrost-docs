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
    client.list_configuration_types = AsyncMock(return_value=[])
    client.list_configuration_statuses = AsyncMock(return_value=[])
    client.list_custom_asset_types = AsyncMock(return_value=[])
    client.list_locations = AsyncMock(return_value={"items": [], "total": 0})
    client.list_documents = AsyncMock(return_value={"items": [], "total": 0})
    client.list_passwords = AsyncMock(return_value={"items": [], "total": 0})
    return client


@pytest.mark.asyncio
async def test_fetch_organizations_builds_lookup(mock_client):
    """StateFetcher builds lookup by itglue_id and name."""
    fetcher = StateFetcher(mock_client)
    state = await fetcher.fetch_for_org("uuid-1")

    assert state.org_by_itglue_id.get("123") == "uuid-1"
    assert state.org_by_name.get("acme corp") == "uuid-1"


@pytest.mark.asyncio
async def test_fetch_configurations_paginates(mock_client):
    """StateFetcher paginates through all configurations."""
    fetcher = StateFetcher(mock_client)
    state = await fetcher.fetch_for_org("uuid-1")

    assert state.config_by_itglue_id.get("456") == "cfg-1"


class TestExistingStateDataclass:
    """Tests for ExistingState dataclass."""

    def test_existing_state_default_values(self):
        """ExistingState initializes with empty collections."""
        state = ExistingState()

        assert state.org_by_itglue_id == {}
        assert state.org_by_name == {}
        assert state.config_by_itglue_id == {}
        assert state.config_type_by_name == {}
        assert state.config_status_by_name == {}
        assert state.location_by_itglue_id == {}
        assert state.document_by_itglue_id == {}
        assert state.password_by_itglue_id == {}
        assert state.custom_asset_type_by_name == {}
        assert state.custom_asset_by_itglue_id == {}
        assert state.configs == {}
        assert state.locations == {}
        assert state.documents == {}
        assert state.passwords == {}
        assert state.custom_assets == {}
        assert state.relationships == set()


class TestStateFetcherOrganizations:
    """Tests for organization fetching."""

    @pytest.mark.asyncio
    async def test_fetch_all_orgs_builds_both_lookups(self, mock_client):
        """fetch_all_orgs builds both itglue_id and name lookups."""
        fetcher = StateFetcher(mock_client)
        state = await fetcher.fetch_all_orgs()

        # Check itglue_id lookup
        assert state.org_by_itglue_id.get("123") == "uuid-1"
        # Org without itglue_id should not be in itglue_id lookup
        assert "uuid-2" not in state.org_by_itglue_id.values() or any(
            v == "uuid-2" for k, v in state.org_by_itglue_id.items()
        ) is False

        # Check name lookup (lowercase)
        assert state.org_by_name.get("acme corp") == "uuid-1"
        assert state.org_by_name.get("beta inc") == "uuid-2"

    @pytest.mark.asyncio
    async def test_fetch_all_orgs_handles_missing_metadata(self, mock_client):
        """fetch_all_orgs handles orgs without metadata gracefully."""
        mock_client.list_organizations = AsyncMock(return_value=[
            {"id": "uuid-1", "name": "No Metadata Org"},  # No metadata key
        ])

        fetcher = StateFetcher(mock_client)
        state = await fetcher.fetch_all_orgs()

        assert state.org_by_name.get("no metadata org") == "uuid-1"
        # No itglue_id lookup since no metadata
        assert len(state.org_by_itglue_id) == 0


class TestStateFetcherConfigTypes:
    """Tests for configuration type fetching."""

    @pytest.mark.asyncio
    async def test_fetch_config_types(self, mock_client):
        """fetch_for_org fetches configuration types."""
        mock_client.list_configuration_types = AsyncMock(return_value=[
            {"id": "type-1", "name": "Server"},
            {"id": "type-2", "name": "Workstation"},
        ])

        fetcher = StateFetcher(mock_client)
        state = await fetcher.fetch_for_org("uuid-1")

        assert state.config_type_by_name.get("server") == "type-1"
        assert state.config_type_by_name.get("workstation") == "type-2"


class TestStateFetcherConfigStatuses:
    """Tests for configuration status fetching."""

    @pytest.mark.asyncio
    async def test_fetch_config_statuses(self, mock_client):
        """fetch_for_org fetches configuration statuses."""
        mock_client.list_configuration_statuses = AsyncMock(return_value=[
            {"id": "status-1", "name": "Active"},
            {"id": "status-2", "name": "Retired"},
        ])

        fetcher = StateFetcher(mock_client)
        state = await fetcher.fetch_for_org("uuid-1")

        assert state.config_status_by_name.get("active") == "status-1"
        assert state.config_status_by_name.get("retired") == "status-2"


class TestStateFetcherCustomAssetTypes:
    """Tests for custom asset type fetching."""

    @pytest.mark.asyncio
    async def test_fetch_custom_asset_types(self, mock_client):
        """fetch_for_org fetches custom asset types."""
        mock_client.list_custom_asset_types = AsyncMock(return_value=[
            {"id": "cat-1", "name": "SSL Certificates"},
            {"id": "cat-2", "name": "Licenses"},
        ])
        # Need to mock list_custom_assets for when it iterates over types
        mock_client.list_custom_assets = AsyncMock(return_value={"items": [], "total": 0})

        fetcher = StateFetcher(mock_client)
        state = await fetcher.fetch_for_org("uuid-1")

        assert state.custom_asset_type_by_name.get("ssl certificates") == "cat-1"
        assert state.custom_asset_type_by_name.get("licenses") == "cat-2"


class TestStateFetcherLocations:
    """Tests for location fetching."""

    @pytest.mark.asyncio
    async def test_fetch_locations_builds_lookup(self, mock_client):
        """fetch_for_org builds location lookup by itglue_id."""
        mock_client.list_locations = AsyncMock(return_value={
            "items": [
                {"id": "loc-1", "name": "HQ", "metadata": {"itglue_id": "loc-123"}},
            ],
            "total": 1,
        })

        fetcher = StateFetcher(mock_client)
        state = await fetcher.fetch_for_org("uuid-1")

        assert state.location_by_itglue_id.get("loc-123") == "loc-1"
        assert "loc-1" in state.locations

    @pytest.mark.asyncio
    async def test_fetch_locations_paginates(self, mock_client):
        """fetch_for_org paginates through all locations."""
        # First call returns 100 items (full page), second returns less
        page1_items = [
            {"id": f"loc-{i}", "name": f"Location {i}", "metadata": {"itglue_id": str(i)}}
            for i in range(100)
        ]
        page2_items = [
            {"id": f"loc-{i}", "name": f"Location {i}", "metadata": {"itglue_id": str(i)}}
            for i in range(100, 150)
        ]

        mock_client.list_locations = AsyncMock(side_effect=[
            {"items": page1_items, "total": 150},
            {"items": page2_items, "total": 150},
        ])

        fetcher = StateFetcher(mock_client)
        state = await fetcher.fetch_for_org("uuid-1")

        assert len(state.locations) == 150
        assert state.location_by_itglue_id.get("0") == "loc-0"
        assert state.location_by_itglue_id.get("149") == "loc-149"


class TestStateFetcherDocuments:
    """Tests for document fetching."""

    @pytest.mark.asyncio
    async def test_fetch_documents_builds_lookup(self, mock_client):
        """fetch_for_org builds document lookup by itglue_id."""
        mock_client.list_documents = AsyncMock(return_value={
            "items": [
                {"id": "doc-1", "name": "Network Docs", "metadata": {"itglue_id": "doc-123"}},
            ],
            "total": 1,
        })

        fetcher = StateFetcher(mock_client)
        state = await fetcher.fetch_for_org("uuid-1")

        assert state.document_by_itglue_id.get("doc-123") == "doc-1"
        assert "doc-1" in state.documents


class TestStateFetcherPasswords:
    """Tests for password fetching."""

    @pytest.mark.asyncio
    async def test_fetch_passwords_builds_lookup(self, mock_client):
        """fetch_for_org builds password lookup by itglue_id."""
        mock_client.list_passwords = AsyncMock(return_value={
            "items": [
                {"id": "pwd-1", "name": "Admin Password", "metadata": {"itglue_id": "pwd-123"}},
            ],
            "total": 1,
        })

        fetcher = StateFetcher(mock_client)
        state = await fetcher.fetch_for_org("uuid-1")

        assert state.password_by_itglue_id.get("pwd-123") == "pwd-1"
        assert "pwd-1" in state.passwords


class TestStateFetcherCustomAssets:
    """Tests for custom asset fetching."""

    @pytest.mark.asyncio
    async def test_fetch_custom_assets_per_type(self, mock_client):
        """fetch_for_org fetches custom assets for each type."""
        mock_client.list_custom_asset_types = AsyncMock(return_value=[
            {"id": "cat-1", "name": "SSL Certificates"},
        ])
        mock_client.list_custom_assets = AsyncMock(return_value={
            "items": [
                {"id": "asset-1", "name": "Cert 1", "metadata": {"itglue_id": "ca-123"}},
            ],
            "total": 1,
        })

        fetcher = StateFetcher(mock_client)
        state = await fetcher.fetch_for_org("uuid-1")

        assert state.custom_asset_by_itglue_id.get("ca-123") == "asset-1"
        assert "asset-1" in state.custom_assets


class TestStateFetcherRelationships:
    """Tests for relationship fetching."""

    @pytest.mark.asyncio
    async def test_fetch_relationships_for_passwords(self, mock_client):
        """fetch_for_org fetches relationships for each password."""
        mock_client.list_passwords = AsyncMock(return_value={
            "items": [
                {"id": "pwd-1", "name": "Admin Password", "metadata": {"itglue_id": "pwd-123"}},
            ],
            "total": 1,
        })
        mock_client.list_relationships = AsyncMock(return_value=[
            {
                "source_type": "password",
                "source_id": "pwd-1",
                "target_type": "configuration",
                "target_id": "cfg-1",
            },
        ])

        fetcher = StateFetcher(mock_client)
        state = await fetcher.fetch_for_org("uuid-1")

        expected_key = "password:pwd-1:configuration:cfg-1"
        assert expected_key in state.relationships

    @pytest.mark.asyncio
    async def test_fetch_relationships_normalizes_reversed_direction(self, mock_client):
        """fetch_for_org normalizes relationships where password is target."""
        mock_client.list_passwords = AsyncMock(return_value={
            "items": [
                {"id": "pwd-1", "name": "Admin Password", "metadata": {"itglue_id": "pwd-123"}},
            ],
            "total": 1,
        })
        # Relationship stored as config -> password (password is target)
        mock_client.list_relationships = AsyncMock(return_value=[
            {
                "source_type": "configuration",
                "source_id": "cfg-1",
                "target_type": "password",
                "target_id": "pwd-1",
            },
        ])

        fetcher = StateFetcher(mock_client)
        state = await fetcher.fetch_for_org("uuid-1")

        # Should be normalized to password:X:type:Y format
        expected_key = "password:pwd-1:configuration:cfg-1"
        assert expected_key in state.relationships

    @pytest.mark.asyncio
    async def test_fetch_relationships_handles_errors(self, mock_client):
        """fetch_for_org continues if relationship fetch fails."""
        mock_client.list_passwords = AsyncMock(return_value={
            "items": [
                {"id": "pwd-1", "name": "Admin Password", "metadata": {"itglue_id": "pwd-123"}},
            ],
            "total": 1,
        })
        mock_client.list_relationships = AsyncMock(side_effect=Exception("API Error"))

        fetcher = StateFetcher(mock_client)
        # Should not raise
        state = await fetcher.fetch_for_org("uuid-1")

        # Should have empty relationships but still have password
        assert len(state.relationships) == 0
        assert "pwd-1" in state.passwords
