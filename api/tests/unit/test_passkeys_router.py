from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.core.auth import UserPrincipal, get_current_active_user
from src.core.database import get_db
from src.core.rate_limiting import limiter
from src.models.enums import UserRole
from src.routers.passkeys import router


@pytest.mark.asyncio
async def test_registration_options_route_accepts_rate_limited_request(monkeypatch):
    monkeypatch.setattr(limiter, "enabled", False)

    app = FastAPI()
    app.include_router(router)

    user = UserPrincipal(
        user_id=uuid4(),
        email="test@example.com",
        name="Test User",
        role=UserRole.OWNER,
        is_active=True,
        is_verified=True,
    )

    class FakePasskeyService:
        def __init__(self, db):
            self.db = db

        async def generate_registration_options(self, user_id):
            assert user_id == user.user_id
            return {"challenge": "abc123", "rp": {"name": "Bifrost Docs"}}

    app.dependency_overrides[get_current_active_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: object()
    monkeypatch.setattr("src.routers.passkeys.PasskeyService", FakePasskeyService)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/auth/passkeys/register/options", json={})

    assert response.status_code == 200
    assert response.json() == {"options": {"challenge": "abc123", "rp": {"name": "Bifrost Docs"}}}
