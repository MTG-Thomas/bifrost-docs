import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.core.database import get_db
from src.core.rate_limiting import limiter
from src.routers.auth import router
from src.services.passkey_service import PasskeyValidationError


class FakeDb:
    async def commit(self):
        pass


@pytest.mark.asyncio
async def test_setup_passkey_verify_malformed_credential_returns_400(monkeypatch):
    monkeypatch.setattr(limiter, "enabled", False)

    app = FastAPI()
    app.include_router(router)

    class FakePasskeyService:
        def __init__(self, db):
            self.db = db

        async def verify_setup_registration(
            self, registration_token, credential_json, device_name=None
        ):
            raise PasskeyValidationError("parser detail that should not leak")

    app.dependency_overrides[get_db] = lambda: FakeDb()
    monkeypatch.setattr("src.services.passkey_service.PasskeyService", FakePasskeyService)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/auth/setup/passkey/verify",
            json={"registration_token": "token", "credential": {"not": "webauthn"}},
        )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid passkey setup response"}


@pytest.mark.asyncio
async def test_setup_passkey_verify_invalid_token_returns_400_without_leaking_parser(
    monkeypatch,
):
    monkeypatch.setattr(limiter, "enabled", False)

    app = FastAPI()
    app.include_router(router)

    class FakePasskeyService:
        def __init__(self, db):
            self.db = db

        async def verify_setup_registration(
            self, registration_token, credential_json, device_name=None
        ):
            raise ValueError("Registration token not found or expired")

    app.dependency_overrides[get_db] = lambda: FakeDb()
    monkeypatch.setattr("src.services.passkey_service.PasskeyService", FakePasskeyService)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/auth/setup/passkey/verify",
            json={"registration_token": "expired", "credential": {"not": "webauthn"}},
        )

    assert response.status_code == 400
    assert response.json() == {"detail": "Registration token not found or expired"}
