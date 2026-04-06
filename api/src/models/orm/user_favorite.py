"""
User Favorite ORM model.

Stores personal bookmarks for quick access to frequently used entities.
Each user can favorite items across different organizations and entity types.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.orm.base import Base

if TYPE_CHECKING:
    from src.models.orm.user import User
    from src.models.orm.organization import Organization


class UserFavorite(Base):
    """User favorites database table for quick access bookmarks."""

    __tablename__ = "user_favorites"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Entity type: "password", "configuration", "document", "location", "custom_asset"
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # Entity ID (UUID of the favorited item)
    entity_id: Mapped[UUID] = mapped_column(nullable=False)
    # Display order for sorting (lower = first)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Optional custom label (if None, use entity name)
    custom_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=text("NOW()"),
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="favorites")
    organization: Mapped["Organization"] = relationship()

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "organization_id",
            "entity_type",
            "entity_id",
            name="uq_user_favorites_user_org_entity",
        ),
    )
