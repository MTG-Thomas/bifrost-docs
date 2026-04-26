import json
from types import MethodType, SimpleNamespace
from uuid import uuid4

import pytest

from src.services.passkey_service import PasskeyService, PasskeyValidationError


class FakeRedis:
    def __init__(self, value):
        self.value = value
        self.deleted = []

    async def get(self, key):
        return self.value

    async def delete(self, key):
        self.deleted.append(key)


def _redis_factory(redis: FakeRedis):
    async def get_fake_redis():
        return redis

    return get_fake_redis


@pytest.mark.asyncio
async def test_verify_registration_wraps_malformed_credential(monkeypatch):
    redis = FakeRedis("YWJj")
    monkeypatch.setattr("src.services.passkey_service.get_redis", _redis_factory(redis))

    service = PasskeyService(db=object())
    user_id = uuid4()

    async def get_user_by_id(self, requested_user_id):
        assert requested_user_id == user_id
        return SimpleNamespace(id=user_id)

    service._get_user_by_id = MethodType(get_user_by_id, service)

    with pytest.raises(PasskeyValidationError, match="Invalid passkey registration response"):
        await service.verify_registration(
            user_id=user_id,
            credential_json=json.dumps({"not": "webauthn"}),
        )


@pytest.mark.asyncio
async def test_verify_authentication_wraps_malformed_credential(monkeypatch):
    redis = FakeRedis("YWJj")
    monkeypatch.setattr("src.services.passkey_service.get_redis", _redis_factory(redis))

    service = PasskeyService(db=object())

    with pytest.raises(PasskeyValidationError, match="Invalid passkey authentication response"):
        await service.verify_authentication(
            challenge_id="challenge",
            credential_json=json.dumps({"not": "webauthn"}),
        )


@pytest.mark.asyncio
async def test_verify_setup_registration_wraps_malformed_credential(monkeypatch):
    redis = FakeRedis(
        json.dumps(
            {
                "email": "owner@example.com",
                "name": "Owner",
                "challenge": "YWJj",
                "webauthn_user_id": "YWJj",
            }
        )
    )
    monkeypatch.setattr("src.services.passkey_service.get_redis", _redis_factory(redis))

    service = PasskeyService(db=object())

    with pytest.raises(PasskeyValidationError, match="Invalid passkey setup response"):
        await service.verify_setup_registration(
            registration_token="token",
            credential_json=json.dumps({"not": "webauthn"}),
        )
