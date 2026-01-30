"""IT Glue API client for fetching flexible asset type definitions.

This module provides a client to fetch field definitions from the IT Glue API,
which is needed to accurately map StructuredData::Cell passwords to their
corresponding asset types and field names.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class ITGlueAPIError(Exception):
    """Exception raised for IT Glue API errors."""

    def __init__(self, status_code: int, message: str, response_body: Any = None):
        self.status_code = status_code
        self.message = message
        self.response_body = response_body
        super().__init__(f"IT Glue API Error {status_code}: {message}")


class ITGlueClient:
    """Client for IT Glue API.

    Used to fetch flexible asset type and field definitions, which are needed
    to map StructuredData::Cell password resource_ids to (asset_type, field_name).
    """

    DEFAULT_BASE_URL = "https://api.itglue.com"

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
    ):
        """Initialize the IT Glue API client.

        Args:
            api_key: IT Glue API key.
            base_url: Base URL of the IT Glue API.
            timeout: Request timeout in seconds.
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> ITGlueClient:
        """Enter async context manager."""
        await self._ensure_client()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit async context manager."""
        _ = exc_type, exc_val, exc_tb  # Unused but required by protocol
        await self.close()

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Ensure HTTP client is initialized."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "x-api-key": self.api_key,
                    "Content-Type": "application/vnd.api+json",
                },
                timeout=httpx.Timeout(self.timeout),
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Make an HTTP request to the IT Glue API.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API endpoint path.
            params: Query parameters.

        Returns:
            Response data (dict).

        Raises:
            ITGlueAPIError: If the request fails.
        """
        client = await self._ensure_client()

        try:
            response = await client.request(
                method=method,
                url=path,
                params=params,
            )
        except httpx.TimeoutException as e:
            raise ITGlueAPIError(0, f"Request timed out: {e}") from e
        except httpx.RequestError as e:
            raise ITGlueAPIError(0, f"Request failed: {e}") from e

        if response.status_code >= 400:
            try:
                error_body = response.json()
            except Exception:
                error_body = response.text
            raise ITGlueAPIError(response.status_code, str(error_body), error_body)

        if response.status_code == 204:
            return {}

        return response.json()

    async def _paginate(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Paginate through all results from an endpoint.

        IT Glue uses page[number] and page[size] for pagination.

        Args:
            path: API endpoint path.
            params: Base query parameters.

        Returns:
            List of all data items across all pages.
        """
        all_data: list[dict[str, Any]] = []
        page = 1
        page_size = 50  # IT Glue default max

        base_params = params.copy() if params else {}

        while True:
            base_params["page[number]"] = page
            base_params["page[size]"] = page_size

            response = await self._request("GET", path, params=base_params)
            data = response.get("data", [])

            if not data:
                break

            all_data.extend(data)

            # Check if there are more pages
            meta = response.get("meta", {})
            total_pages = meta.get("total-pages", 1)
            if page >= total_pages:
                break

            page += 1

        return all_data

    async def list_flexible_asset_types(self) -> list[dict[str, Any]]:
        """Get all flexible asset types.

        Returns:
            List of flexible asset type objects from IT Glue.
            Each object has 'id', 'type', and 'attributes' keys.
        """
        return await self._paginate("/flexible_asset_types")

    async def get_flexible_asset_fields(self, type_id: str) -> list[dict[str, Any]]:
        """Get fields for a flexible asset type.

        Args:
            type_id: The ID of the flexible asset type.

        Returns:
            List of field definition objects.
            Each object has 'id', 'type', and 'attributes' keys.
        """
        path = f"/flexible_asset_types/{type_id}/relationships/flexible_asset_fields"
        return await self._paginate(path)

    async def build_asset_type_map(self) -> dict[str, str]:
        """Build a mapping from flexible asset type ID to type name.

        For StructuredData::Cell passwords, the resource_id is the flexible
        asset TYPE id. This map allows looking up the type name.

        Returns:
            Dict mapping type_id (str) to type_name (str).
            Example: {"1016376066": "Azure App Registration"}
        """
        type_map: dict[str, str] = {}

        asset_types = await self.list_flexible_asset_types()
        logger.debug("Found %d flexible asset types", len(asset_types))

        for asset_type in asset_types:
            type_id = str(asset_type.get("id", ""))
            type_name = asset_type.get("attributes", {}).get("name", "")

            if type_id and type_name:
                type_map[type_id] = type_name
                logger.debug("Mapped type %s -> %s", type_id, type_name)

        logger.info("Built asset type map with %d entries", len(type_map))
        return type_map

