"""
Integration tests for organizations router.

Tests organization management including:
- Creating organizations
- Duplicate name handling
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.core.auth import UserPrincipal, get_current_active_user
from src.main import app
from src.models.enums import UserRole
from src.models.orm.organization import Organization


def create_mock_admin_user(user_id=None):
    """Create a mock admin UserPrincipal for testing."""
    return UserPrincipal(
        user_id=user_id or uuid4(),
        email="admin@example.com",
        name="Admin User",
        role=UserRole.ADMINISTRATOR,
        is_active=True,
        is_verified=True,
    )


@pytest_asyncio.fixture
async def client():
    """Create an async HTTP client for testing."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.mark.integration
class TestCreateOrganizationDuplicateName:
    """Tests for duplicate organization name handling."""

    async def test_create_duplicate_name_returns_409(self):
        """Creating org with existing name should return 409 Conflict."""
        admin_user = create_mock_admin_user()

        # Set up dependency override for authentication
        app.dependency_overrides[get_current_active_user] = lambda: admin_user

        # Create a mock for the organization that will be "found" as existing
        existing_org = MagicMock(spec=Organization)
        existing_org.id = uuid4()
        existing_org.name = "Unique Test Org"

        mock_org_repo = AsyncMock()
        # First call: check for existing org - return existing
        mock_org_repo.get_by_name = AsyncMock(return_value=existing_org)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                with patch(
                    "src.routers.organizations.OrganizationRepository",
                    return_value=mock_org_repo,
                ):
                    # Try to create org with same name as existing
                    response = await client.post(
                        "/api/organizations",
                        json={"name": "Unique Test Org"},
                    )

            assert response.status_code == 409
            assert "already exists" in response.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_create_unique_name_succeeds(self):
        """Creating org with unique name should succeed."""
        admin_user = create_mock_admin_user()

        # Set up dependency override for authentication
        app.dependency_overrides[get_current_active_user] = lambda: admin_user

        created_org = MagicMock(spec=Organization)
        created_org.id = uuid4()
        created_org.name = "New Unique Org"
        created_org.metadata_ = {}
        created_org.is_enabled = True
        created_org.created_at = MagicMock()
        created_org.updated_at = MagicMock()
        created_org.updated_by_user_id = None
        created_org.updated_by_user = None

        mock_org_repo = AsyncMock()
        # No existing org with this name
        mock_org_repo.get_by_name = AsyncMock(return_value=None)
        mock_org_repo.create = AsyncMock(return_value=created_org)

        mock_audit_service = AsyncMock()
        mock_audit_service.log = AsyncMock()

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                with (
                    patch(
                        "src.routers.organizations.OrganizationRepository",
                        return_value=mock_org_repo,
                    ),
                    patch(
                        "src.routers.organizations.get_audit_service",
                        return_value=mock_audit_service,
                    ),
                ):
                    response = await client.post(
                        "/api/organizations",
                        json={"name": "New Unique Org"},
                    )

            assert response.status_code == 201
            assert response.json()["name"] == "New Unique Org"
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)
