"""Regression tests for organization-scoped object access."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.core.auth import UserPrincipal
from src.models.enums import UserRole
from src.routers import (
    attachments,
    configurations,
    custom_assets,
    documents,
    locations,
    passwords,
    relationships,
    search,
)


@pytest.fixture
def reader_user() -> UserPrincipal:
    return UserPrincipal(
        user_id=uuid4(),
        email="zap-reader@example.com",
        name="ZAP Reader",
        role=UserRole.READER,
        is_active=True,
        is_verified=True,
    )


@pytest.mark.asyncio
async def test_wrong_org_document_lookup_returns_404(reader_user: UserPrincipal):
    org_id = uuid4()
    doc_id = uuid4()
    repo = AsyncMock()
    repo.get_by_id_and_org.return_value = None

    with patch("src.routers.documents.DocumentRepository", return_value=repo):
        with pytest.raises(HTTPException) as exc:
            await documents.get_document(org_id, doc_id, reader_user, AsyncMock())

    assert exc.value.status_code == 404
    assert exc.value.detail == "Document not found"
    repo.get_by_id_and_org.assert_awaited_once_with(doc_id, org_id)


@pytest.mark.asyncio
async def test_wrong_org_password_lookup_returns_404(reader_user: UserPrincipal):
    org_id = uuid4()
    password_id = uuid4()
    repo = AsyncMock()
    repo.get_by_id_and_org.return_value = None

    with patch("src.routers.passwords.PasswordRepository", return_value=repo):
        with pytest.raises(HTTPException) as exc:
            await passwords.get_password(org_id, password_id, reader_user, AsyncMock())

    assert exc.value.status_code == 404
    assert exc.value.detail == "Password not found"
    repo.get_by_id_and_org.assert_awaited_once_with(password_id, org_id)


@pytest.mark.asyncio
async def test_wrong_org_configuration_lookup_returns_404(reader_user: UserPrincipal):
    org_id = uuid4()
    config_id = uuid4()
    repo = AsyncMock()
    repo.get_by_id_for_org.return_value = None

    with patch("src.routers.configurations.ConfigurationRepository", return_value=repo):
        with pytest.raises(HTTPException) as exc:
            await configurations.get_configuration(org_id, config_id, reader_user, AsyncMock())

    assert exc.value.status_code == 404
    assert exc.value.detail == "Configuration not found"
    repo.get_by_id_for_org.assert_awaited_once_with(config_id, org_id)


@pytest.mark.asyncio
async def test_wrong_org_location_lookup_returns_404(reader_user: UserPrincipal):
    org_id = uuid4()
    location_id = uuid4()
    repo = AsyncMock()
    repo.get_by_id_and_organization.return_value = None

    with patch("src.routers.locations.LocationRepository", return_value=repo):
        with pytest.raises(HTTPException) as exc:
            await locations.get_location(org_id, location_id, reader_user, AsyncMock())

    assert exc.value.status_code == 404
    assert exc.value.detail == "Location not found"
    repo.get_by_id_and_organization.assert_awaited_once_with(location_id, org_id)


@pytest.mark.asyncio
async def test_wrong_org_custom_asset_lookup_returns_404(reader_user: UserPrincipal):
    org_id = uuid4()
    type_id = uuid4()
    asset_id = uuid4()
    type_repo = AsyncMock()
    type_repo.get_by_id.return_value = SimpleNamespace(fields=[], display_field_key=None)
    asset_repo = AsyncMock()
    asset_repo.get_by_id_type_and_org.return_value = None

    with (
        patch("src.routers.custom_assets.CustomAssetTypeRepository", return_value=type_repo),
        patch("src.routers.custom_assets.CustomAssetRepository", return_value=asset_repo),
    ):
        with pytest.raises(HTTPException) as exc:
            await custom_assets.get_custom_asset(
                org_id, type_id, asset_id, reader_user, AsyncMock()
            )

    assert exc.value.status_code == 404
    assert exc.value.detail == "Custom asset not found"
    asset_repo.get_by_id_type_and_org.assert_awaited_once_with(asset_id, type_id, org_id)


@pytest.mark.asyncio
async def test_wrong_org_attachment_lookup_returns_404(reader_user: UserPrincipal):
    org_id = uuid4()
    attachment_id = uuid4()
    repo = AsyncMock()
    repo.get_by_id_and_org.return_value = None

    with patch("src.routers.attachments.AttachmentRepository", return_value=repo):
        with pytest.raises(HTTPException) as exc:
            await attachments.get_attachment(org_id, attachment_id, reader_user, AsyncMock())

    assert exc.value.status_code == 404
    assert exc.value.detail == "Attachment not found"
    repo.get_by_id_and_org.assert_awaited_once_with(attachment_id, org_id)


@pytest.mark.asyncio
async def test_relationship_lookup_is_scoped_to_requested_org(reader_user: UserPrincipal):
    org_id = uuid4()
    entity_id = uuid4()
    repo = AsyncMock()
    repo.get_for_entity.return_value = []

    with patch("src.routers.relationships.RelationshipRepository", return_value=repo):
        result = await relationships.list_relationships(
            org_id,
            reader_user,
            AsyncMock(),
            entity_type="document",
            entity_id=entity_id,
        )

    assert result == []
    repo.get_for_entity.assert_awaited_once_with(org_id, "document", entity_id)


@pytest.mark.asyncio
async def test_search_with_org_filter_only_queries_that_org(reader_user: UserPrincipal):
    org_id = uuid4()
    org_repo = AsyncMock()
    org_repo.get_by_id.return_value = SimpleNamespace(id=org_id, is_enabled=True)
    embeddings = AsyncMock()
    embeddings.check_openai_available.return_value = False
    embeddings.text_search.return_value = []

    with (
        patch("src.routers.search.OrganizationRepository", return_value=org_repo),
        patch("src.routers.search.get_embeddings_service", return_value=embeddings),
    ):
        result = await search.search(
            reader_user,
            AsyncMock(),
            q="router",
            org_id=org_id,
            limit=20,
            mode="text",
            show_disabled=False,
        )

    assert result.results == []
    org_repo.get_by_id.assert_awaited_once_with(org_id)
    embeddings.text_search.assert_awaited_once()
    assert embeddings.text_search.await_args.args[2] == [org_id]
