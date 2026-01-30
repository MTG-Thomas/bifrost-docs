"""Unit tests for password field mapper module."""

from itglue_migrate.password_field_mapper import (
    PasswordFieldMap,
    build_password_field_map,
)


class TestPasswordFieldMap:
    """Tests for PasswordFieldMap class."""

    def test_is_password_field_returns_true_for_known_field(self) -> None:
        """Returns True for fields in the password_fields set."""
        password_map = PasswordFieldMap(
            password_fields={("ssl-certificates", "api_key"), ("databases", "admin_password")}
        )

        assert password_map.is_password_field("ssl-certificates", "api_key") is True
        assert password_map.is_password_field("databases", "admin_password") is True

    def test_is_password_field_returns_false_for_unknown_field(self) -> None:
        """Returns False for fields not in the password_fields set."""
        password_map = PasswordFieldMap(
            password_fields={("ssl-certificates", "api_key")}
        )

        assert password_map.is_password_field("ssl-certificates", "common_name") is False
        assert password_map.is_password_field("databases", "api_key") is False

    def test_is_password_field_case_insensitive(self) -> None:
        """Field name matching is case-insensitive."""
        password_map = PasswordFieldMap(
            password_fields={("ssl-certificates", "api_key")}
        )

        assert password_map.is_password_field("ssl-certificates", "API_KEY") is True
        assert password_map.is_password_field("ssl-certificates", "Api_Key") is True
        assert password_map.is_password_field("ssl-certificates", "api_KEY") is True

    def test_is_password_field_checks_global_fields(self) -> None:
        """Checks global_password_fields when type-specific not found."""
        password_map = PasswordFieldMap(
            password_fields=set(),
            global_password_fields={"api_key", "secret"},
        )

        # Should match any asset type
        assert password_map.is_password_field("ssl-certificates", "api_key") is True
        assert password_map.is_password_field("databases", "secret") is True
        assert password_map.is_password_field("any-type", "api_key") is True
        assert password_map.is_password_field("ssl-certificates", "common_name") is False

    def test_type_specific_takes_precedence(self) -> None:
        """Type-specific fields are checked before global fields."""
        password_map = PasswordFieldMap(
            password_fields={("ssl-certificates", "api_key")},
            global_password_fields=set(),  # Empty global
        )

        # Type-specific match
        assert password_map.is_password_field("ssl-certificates", "api_key") is True
        # Not in global, not type-specific for databases
        assert password_map.is_password_field("databases", "api_key") is False

    def test_get_password_fields_for_type(self) -> None:
        """Returns all password field names for an asset type."""
        password_map = PasswordFieldMap(
            password_fields={
                ("ssl-certificates", "api_key"),
                ("ssl-certificates", "secret"),
                ("databases", "admin_password"),
            }
        )

        ssl_fields = password_map.get_password_fields_for_type("ssl-certificates")
        assert ssl_fields == {"api_key", "secret"}

        db_fields = password_map.get_password_fields_for_type("databases")
        assert db_fields == {"admin_password"}

    def test_get_password_fields_for_type_includes_global(self) -> None:
        """Includes global password fields in the result."""
        password_map = PasswordFieldMap(
            password_fields={("ssl-certificates", "api_key")},
            global_password_fields={"secret_value", "private_key"},
        )

        ssl_fields = password_map.get_password_fields_for_type("ssl-certificates")
        assert ssl_fields == {"api_key", "secret_value", "private_key"}

        # Type with no specific fields still gets global
        other_fields = password_map.get_password_fields_for_type("other-type")
        assert other_fields == {"secret_value", "private_key"}

    def test_get_password_fields_for_type_empty_when_no_matches(self) -> None:
        """Returns empty set when asset type has no password fields."""
        password_map = PasswordFieldMap(
            password_fields={("ssl-certificates", "api_key")}
        )

        result = password_map.get_password_fields_for_type("databases")
        assert result == set()


class TestBuildPasswordFieldMap:
    """Tests for build_password_field_map function.

    The function collects field names from StructuredData::Cell passwords
    and adds them to global_password_fields.
    """

    def test_collects_cell_password_field_names(self) -> None:
        """Collects field names from StructuredData::Cell passwords."""
        passwords = [
            {
                "id": "pwd-1",
                "name": "Secret Value",
                "resource_type": "StructuredData::Cell",
                "resource_id": "some-id",
            },
            {
                "id": "pwd-2",
                "name": "API Key",
                "resource_type": "StructuredData::Cell",
                "resource_id": "another-id",
            },
        ]

        password_map = build_password_field_map(passwords)

        # Both field names should be in global_password_fields
        assert "secret value" in password_map.global_password_fields
        assert "api key" in password_map.global_password_fields

    def test_matches_any_asset_type_via_global(self) -> None:
        """Password fields match any asset type via global_password_fields."""
        passwords = [
            {
                "id": "pwd-1",
                "name": "Secret Value",
                "resource_type": "StructuredData::Cell",
                "resource_id": "some-id",
            },
        ]

        password_map = build_password_field_map(passwords)

        # Should match any asset type
        assert password_map.is_password_field("azure-app-registration", "Secret Value") is True
        assert password_map.is_password_field("ssl-certificates", "Secret Value") is True
        assert password_map.is_password_field("any-type", "Secret Value") is True

    def test_empty_when_no_cell_passwords(self) -> None:
        """Returns empty map when no StructuredData::Cell passwords exist."""
        passwords = [
            {
                "id": "pwd-1",
                "name": "Server Password",
                "resource_type": "Configuration",
                "resource_id": "config-123",
            },
            {
                "id": "pwd-2",
                "name": "Location Password",
                "resource_type": "Location",
                "resource_id": "loc-456",
            },
        ]

        password_map = build_password_field_map(passwords)

        assert password_map.password_fields == set()
        assert password_map.global_password_fields == set()

    def test_ignores_row_passwords(self) -> None:
        """Ignores StructuredData::Row passwords (different mechanism)."""
        passwords = [
            {
                "id": "pwd-1",
                "name": "Row Password",
                "resource_type": "StructuredData::Row",
                "resource_id": "asset-123",
            },
        ]

        password_map = build_password_field_map(passwords)

        assert password_map.password_fields == set()
        assert password_map.global_password_fields == set()

    def test_handles_missing_name(self) -> None:
        """Gracefully handles passwords with missing name."""
        passwords = [
            {
                "id": "pwd-1",
                "name": None,
                "resource_type": "StructuredData::Cell",
                "resource_id": "asset-123",
            },
            {
                "id": "pwd-2",
                "name": "",
                "resource_type": "StructuredData::Cell",
                "resource_id": "asset-123",
            },
        ]

        # Should not raise
        password_map = build_password_field_map(passwords)

        assert password_map.password_fields == set()
        assert password_map.global_password_fields == set()

    def test_case_insensitive_resource_type(self) -> None:
        """Resource type matching is case-insensitive."""
        passwords = [
            {
                "id": "pwd-1",
                "name": "API Key",
                "resource_type": "structureddata::cell",  # lowercase
                "resource_id": "asset-123",
            },
            {
                "id": "pwd-2",
                "name": "Secret",
                "resource_type": "STRUCTUREDDATA::CELL",  # uppercase
                "resource_id": "asset-123",
            },
        ]

        password_map = build_password_field_map(passwords)

        assert "api key" in password_map.global_password_fields
        assert "secret" in password_map.global_password_fields

    def test_deduplicates_field_names(self) -> None:
        """Multiple passwords for the same field are deduplicated."""
        passwords = [
            {
                "id": "pwd-1",
                "name": "API Key",
                "resource_type": "StructuredData::Cell",
                "resource_id": "asset-123",
            },
            {
                "id": "pwd-2",
                "name": "API Key",
                "resource_type": "StructuredData::Cell",
                "resource_id": "asset-456",
            },
            {
                "id": "pwd-3",
                "name": "api key",  # Same name, different case
                "resource_type": "StructuredData::Cell",
                "resource_id": "asset-789",
            },
        ]

        password_map = build_password_field_map(passwords)

        # Should have exactly one entry (lowercased)
        assert password_map.global_password_fields == {"api key"}

    def test_empty_inputs(self) -> None:
        """Handles empty inputs gracefully."""
        password_map = build_password_field_map([])
        assert password_map.password_fields == set()
        assert password_map.global_password_fields == set()

    def test_custom_assets_parameter_ignored(self) -> None:
        """The custom_assets parameter is ignored (kept for API compatibility)."""
        passwords = [
            {
                "id": "pwd-1",
                "name": "Secret",
                "resource_type": "StructuredData::Cell",
                "resource_id": "asset-123",
            },
        ]
        custom_assets = {
            "ssl-certificates": [
                {"id": "asset-123", "fields": {"Secret": "val"}},
            ],
        }

        # custom_assets should be ignored - only field names matter
        password_map = build_password_field_map(passwords, custom_assets)

        assert "secret" in password_map.global_password_fields
