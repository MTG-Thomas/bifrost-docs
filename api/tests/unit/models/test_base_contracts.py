"""Tests for base contract models."""

from datetime import UTC, datetime
from uuid import uuid4

from src.models.contracts.base import PublicEntityBase, PublicOrganizationBase


class TestPublicEntityBase:
    """Tests for PublicEntityBase class."""

    def test_uuid_serialization(self):
        """Test that UUID fields are serialized to strings."""

        class TestModel(PublicEntityBase):
            name: str

        test_id = uuid4()
        test_org_id = uuid4()
        now = datetime.now(UTC)

        model = TestModel(
            id=test_id,
            organization_id=test_org_id,
            name="Test",
            is_enabled=True,
            created_at=now,
            updated_at=now,
        )

        # Serialize to dict (simulating JSON response)
        data = model.model_dump()

        # UUIDs should be strings
        assert isinstance(data["id"], str)
        assert isinstance(data["organization_id"], str)
        assert data["id"] == str(test_id)
        assert data["organization_id"] == str(test_org_id)

    def test_metadata_alias(self):
        """Test that metadata_ ORM field maps to metadata JSON field."""

        class TestModel(PublicEntityBase):
            name: str

        test_id = uuid4()
        test_org_id = uuid4()
        now = datetime.now(UTC)

        # Simulate ORM object with metadata_ attribute
        class FakeORM:
            def __init__(self):
                self.id = test_id
                self.organization_id = test_org_id
                self.name = "Test"
                self.is_enabled = True
                self.created_at = now
                self.updated_at = now
                self.metadata_ = {"key": "value"}  # Note: underscore suffix

        orm_obj = FakeORM()
        model = TestModel.model_validate(orm_obj)

        assert model.metadata == {"key": "value"}

    def test_default_metadata(self):
        """Test that missing metadata defaults to empty dict."""

        class TestModel(PublicEntityBase):
            name: str

        test_id = uuid4()
        test_org_id = uuid4()
        now = datetime.now(UTC)

        model = TestModel(
            id=test_id,
            organization_id=test_org_id,
            name="Test",
            is_enabled=True,
            created_at=now,
            updated_at=now,
        )

        assert model.metadata == {}

    def test_default_is_enabled(self):
        """Test that is_enabled defaults to True."""

        class TestModel(PublicEntityBase):
            name: str

        test_id = uuid4()
        test_org_id = uuid4()
        now = datetime.now(UTC)

        model = TestModel(
            id=test_id,
            organization_id=test_org_id,
            name="Test",
            created_at=now,
            updated_at=now,
        )

        assert model.is_enabled is True

    def test_explicit_is_enabled_false(self):
        """Test that is_enabled can be explicitly set to False."""

        class TestModel(PublicEntityBase):
            name: str

        test_id = uuid4()
        test_org_id = uuid4()
        now = datetime.now(UTC)

        model = TestModel(
            id=test_id,
            organization_id=test_org_id,
            name="Test",
            is_enabled=False,  # Explicitly disabled
            created_at=now,
            updated_at=now,
        )

        assert model.is_enabled is False


class TestPublicOrganizationBase:
    """Tests for PublicOrganizationBase class."""

    def test_no_organization_id_field(self):
        """Test that organization base doesn't have org_id field."""

        class TestOrgModel(PublicOrganizationBase):
            industry: str | None = None

        test_id = uuid4()
        now = datetime.now(UTC)

        model = TestOrgModel(
            id=test_id,
            name="Test Org",
            industry="Technology",
            created_at=now,
            updated_at=now,
        )

        # Should not have organization_id
        assert not hasattr(model, "organization_id")

        # But should have other common fields
        assert hasattr(model, "id")
        assert hasattr(model, "name")
        assert hasattr(model, "is_enabled")
        assert hasattr(model, "created_at")
        assert hasattr(model, "updated_at")
        assert hasattr(model, "metadata")

    def test_uuid_serialization(self):
        """Test UUID serialization for organization base."""

        class TestOrgModel(PublicOrganizationBase):
            pass

        test_id = uuid4()
        now = datetime.now(UTC)

        model = TestOrgModel(
            id=test_id,
            name="Test Org",
            created_at=now,
            updated_at=now,
        )

        data = model.model_dump()
        assert isinstance(data["id"], str)
        assert data["id"] == str(test_id)

    def test_metadata_alias(self):
        """Test metadata alias for organization base."""

        class TestOrgModel(PublicOrganizationBase):
            pass

        test_id = uuid4()
        now = datetime.now(UTC)

        # Simulate ORM object
        class FakeORM:
            def __init__(self):
                self.id = test_id
                self.name = "Test Org"
                self.is_enabled = True
                self.created_at = now
                self.updated_at = now
                self.metadata_ = {"size": "50-100"}

        orm_obj = FakeORM()
        model = TestOrgModel.model_validate(orm_obj)

        assert model.metadata == {"size": "50-100"}
