"""Password field mapper for detecting embedded passwords in custom asset fields.

This module identifies fields that should be password type based on
StructuredData::Cell passwords in the IT Glue export.

For Cell passwords, the password's `name` field indicates which custom asset
field contains the embedded password value.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PasswordFieldMap:
    """Map of custom asset fields that contain embedded passwords.

    Fields are identified by (asset_type_slug, field_name_lower) tuples.
    global_password_fields contains field names that should be treated
    as passwords across all asset types.
    """

    password_fields: set[tuple[str, str]] = field(default_factory=set)
    global_password_fields: set[str] = field(default_factory=set)

    def is_password_field(self, asset_type_slug: str, field_name: str) -> bool:
        """Check if a field should be a password type.

        Args:
            asset_type_slug: The custom asset type slug (e.g., "ssl-certificates").
            field_name: The field name to check.

        Returns:
            True if this field contains embedded passwords.
        """
        # Check type-specific first
        if (asset_type_slug, field_name.lower()) in self.password_fields:
            return True
        # Fall back to global password fields
        return field_name.lower() in self.global_password_fields

    def get_password_fields_for_type(self, asset_type_slug: str) -> set[str]:
        """Get all password field names for an asset type.

        Args:
            asset_type_slug: The custom asset type slug.

        Returns:
            Set of lowercase field names that should be password type.
        """
        type_specific = {
            field_name
            for type_slug, field_name in self.password_fields
            if type_slug == asset_type_slug
        }
        # Include global password fields as fallback
        return type_specific | self.global_password_fields


def build_password_field_map(
    passwords: list[dict[str, Any]],
    custom_assets: dict[str, list[dict[str, Any]]] | None = None,
) -> PasswordFieldMap:
    """Build map of fields that should be password type.

    For StructuredData::Cell passwords (embedded in custom asset fields),
    the password's `name` field indicates which field contains the password.
    We collect all such field names and treat them as password fields.

    Args:
        passwords: List of password dictionaries from passwords.csv.
            Expected fields: resource_type, name.
        custom_assets: Unused, kept for API compatibility.

    Returns:
        PasswordFieldMap with identified password fields.
    """
    _ = custom_assets  # Unused
    password_map = PasswordFieldMap()

    for pwd in passwords:
        resource_type = (pwd.get("resource_type") or "").lower()

        # Only process ::Cell passwords (embedded in custom asset fields)
        if "structureddata::cell" not in resource_type:
            continue

        field_name = pwd.get("name") or ""
        if not field_name:
            continue

        # Add to global password fields - applies to any asset type with this field
        password_map.global_password_fields.add(field_name.lower())
        logger.debug("Cell password field detected: '%s'", field_name)

    if password_map.global_password_fields:
        logger.info(
            "Detected %d password field names from Cell passwords: %s",
            len(password_map.global_password_fields),
            password_map.global_password_fields,
        )

    return password_map
