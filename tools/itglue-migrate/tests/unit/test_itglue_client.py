"""Unit tests for IT Glue API client module."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from itglue_migrate.itglue_client import ITGlueAPIError, ITGlueClient


class TestITGlueClient:
    """Tests for ITGlueClient class."""

    def test_init_default_base_url(self) -> None:
        """Uses default IT Glue API base URL."""
        client = ITGlueClient(api_key="test-key")
        assert client.base_url == "https://api.itglue.com"

    def test_init_custom_base_url(self) -> None:
        """Accepts custom base URL."""
        client = ITGlueClient(api_key="test-key", base_url="https://api.eu.itglue.com")
        assert client.base_url == "https://api.eu.itglue.com"

    def test_init_strips_trailing_slash(self) -> None:
        """Strips trailing slash from base URL."""
        client = ITGlueClient(api_key="test-key", base_url="https://api.itglue.com/")
        assert client.base_url == "https://api.itglue.com"


class TestITGlueClientRequests:
    """Tests for IT Glue client HTTP requests."""

    @pytest.mark.asyncio
    async def test_request_uses_correct_headers(self) -> None:
        """Request includes correct IT Glue API headers."""
        client = ITGlueClient(api_key="test-api-key")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}

        with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            await client._ensure_client()

            # Verify the client was created with correct headers
            assert client._client is not None
            assert client._client.headers["x-api-key"] == "test-api-key"
            assert client._client.headers["Content-Type"] == "application/vnd.api+json"

        await client.close()

    @pytest.mark.asyncio
    async def test_request_handles_timeout(self) -> None:
        """Raises ITGlueAPIError on timeout."""
        client = ITGlueClient(api_key="test-key")

        with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = httpx.TimeoutException("timeout")

            with pytest.raises(ITGlueAPIError) as exc_info:
                await client._request("GET", "/test")

            assert exc_info.value.status_code == 0
            assert "timed out" in str(exc_info.value)

        await client.close()

    @pytest.mark.asyncio
    async def test_request_handles_request_error(self) -> None:
        """Raises ITGlueAPIError on request error."""
        client = ITGlueClient(api_key="test-key")

        with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = httpx.RequestError("connection failed")

            with pytest.raises(ITGlueAPIError) as exc_info:
                await client._request("GET", "/test")

            assert exc_info.value.status_code == 0
            assert "failed" in str(exc_info.value)

        await client.close()

    @pytest.mark.asyncio
    async def test_request_handles_api_error(self) -> None:
        """Raises ITGlueAPIError on API error response."""
        client = ITGlueClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "Unauthorized"}

        with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            with pytest.raises(ITGlueAPIError) as exc_info:
                await client._request("GET", "/test")

            assert exc_info.value.status_code == 401
            assert "Unauthorized" in str(exc_info.value)

        await client.close()


class TestListFlexibleAssetTypes:
    """Tests for list_flexible_asset_types method."""

    @pytest.mark.asyncio
    async def test_returns_asset_types(self) -> None:
        """Returns list of flexible asset types."""
        client = ITGlueClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"id": "123", "type": "flexible-asset-types", "attributes": {"name": "SSL Certificate"}},
                {"id": "456", "type": "flexible-asset-types", "attributes": {"name": "Azure App Registration"}},
            ],
            "meta": {"total-pages": 1},
        }

        with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.list_flexible_asset_types()

        assert len(result) == 2
        assert result[0]["id"] == "123"
        assert result[0]["attributes"]["name"] == "SSL Certificate"
        assert result[1]["id"] == "456"

        await client.close()

    @pytest.mark.asyncio
    async def test_handles_pagination(self) -> None:
        """Paginates through multiple pages of results."""
        client = ITGlueClient(api_key="test-key")

        page1_response = MagicMock()
        page1_response.status_code = 200
        page1_response.json.return_value = {
            "data": [{"id": "1", "attributes": {"name": "Type 1"}}],
            "meta": {"total-pages": 2},
        }

        page2_response = MagicMock()
        page2_response.status_code = 200
        page2_response.json.return_value = {
            "data": [{"id": "2", "attributes": {"name": "Type 2"}}],
            "meta": {"total-pages": 2},
        }

        with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = [page1_response, page2_response]
            result = await client.list_flexible_asset_types()

        assert len(result) == 2
        assert result[0]["id"] == "1"
        assert result[1]["id"] == "2"

        await client.close()


class TestGetFlexibleAssetFields:
    """Tests for get_flexible_asset_fields method."""

    @pytest.mark.asyncio
    async def test_returns_fields_for_type(self) -> None:
        """Returns list of fields for an asset type."""
        client = ITGlueClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"id": "1016376066", "type": "flexible-asset-fields", "attributes": {"name": "Secret Value"}},
                {"id": "1016376067", "type": "flexible-asset-fields", "attributes": {"name": "App Name"}},
            ],
            "meta": {"total-pages": 1},
        }

        with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.get_flexible_asset_fields("456")

        assert len(result) == 2
        assert result[0]["id"] == "1016376066"
        assert result[0]["attributes"]["name"] == "Secret Value"

        await client.close()


class TestBuildAssetTypeMap:
    """Tests for build_asset_type_map method."""

    @pytest.mark.asyncio
    async def test_builds_complete_map(self) -> None:
        """Builds mapping from asset type ID to type name."""
        client = ITGlueClient(api_key="test-key")

        asset_types_response = MagicMock()
        asset_types_response.status_code = 200
        asset_types_response.json.return_value = {
            "data": [
                {"id": "100", "type": "flexible-asset-types", "attributes": {"name": "Azure App Registration"}},
                {"id": "200", "type": "flexible-asset-types", "attributes": {"name": "SSL Certificate"}},
            ],
            "meta": {"total-pages": 1},
        }

        with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = asset_types_response
            result = await client.build_asset_type_map()

        assert result["100"] == "Azure App Registration"
        assert result["200"] == "SSL Certificate"

        await client.close()

    @pytest.mark.asyncio
    async def test_handles_empty_asset_types(self) -> None:
        """Returns empty map when no asset types exist."""
        client = ITGlueClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [], "meta": {"total-pages": 1}}

        with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.build_asset_type_map()

        assert result == {}

        await client.close()

    @pytest.mark.asyncio
    async def test_skips_entries_with_missing_data(self) -> None:
        """Skips entries with missing id or name."""
        client = ITGlueClient(api_key="test-key")

        asset_types_response = MagicMock()
        asset_types_response.status_code = 200
        asset_types_response.json.return_value = {
            "data": [
                {"id": "100", "attributes": {"name": "Type 1"}},
                {"id": "", "attributes": {"name": "Type 2"}},  # Missing ID
                {"id": "300", "attributes": {"name": ""}},  # Missing name
            ],
            "meta": {"total-pages": 1},
        }

        with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = asset_types_response
            result = await client.build_asset_type_map()

        # Only valid entry should be present
        assert len(result) == 1
        assert result["100"] == "Type 1"

        await client.close()


class TestContextManager:
    """Tests for async context manager functionality."""

    @pytest.mark.asyncio
    async def test_context_manager_opens_and_closes_client(self) -> None:
        """Context manager properly opens and closes HTTP client."""
        async with ITGlueClient(api_key="test-key") as client:
            assert client._client is not None

        # After exiting context, client should be closed
        assert client._client is None

    @pytest.mark.asyncio
    async def test_close_is_idempotent(self) -> None:
        """Calling close multiple times is safe."""
        client = ITGlueClient(api_key="test-key")
        await client._ensure_client()

        await client.close()
        await client.close()  # Should not raise

        assert client._client is None
