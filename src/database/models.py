"""SQLAlchemy ORM models for SLAYIN.

Models describe *data only*; business rules (learning, recommendations, etc.)
belong in `src/services/`.

Enums are stored as plain VARCHAR values (no native DB enum, no CHECK), so new
values can be added in Python without a schema migration.
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    DateTime,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.db_config import Base, TimestampMixin, utcnow


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class WardrobeItemStatus(str, enum.Enum):
    ACTIVE = "active"
    UNAVAILABLE = "unavailable"  # e.g. in laundry, lent out
    DAMAGED = "damaged"
    GIVEN_AWAY = "given_away"
    ARCHIVED = "archived"


class OutfitSource(str, enum.Enum):
    RECOMMENDED = "recommended"  # produced by the recommendation engine
    STYLIST_CHAT = "stylist_chat"  # suggested by the AI stylist
    USER_CREATED = "user_created"  # assembled manually by the user


class PreferenceDimension(str, enum.Enum):
    """What aspect of style a preference is about."""

    CATEGORY = "category"  # e.g. "shirt"
    COLOR = "color"  # e.g. "navy"
    PATTERN = "pattern"  # e.g. "striped"
    STYLE = "style"  # e.g. "streetwear", "oversized shirt"
    FIT = "fit"  # e.g. "oversized"
    OCCASION = "occasion"  # e.g. "office"
    ITEM = "item"  # a specific wardrobe item ("avoid these jeans")
    OTHER = "other"


class PreferenceSource(str, enum.Enum):
    CHAT = "chat"  # stated to the AI stylist
    FEEDBACK = "feedback"  # derived from explicit Feedback rows
    INFERRED = "inferred"  # learned from behaviour
    MANUAL = "manual"  # set directly in settings/onboarding


class FeedbackType(str, enum.Enum):
    LIKED = "liked"
    DISLIKED = "disliked"
    UNCOMFORTABLE = "uncomfortable"
    UNAVAILABLE = "unavailable"
    DAMAGED = "damaged"
    GIVEN_AWAY = "given_away"
    AVOID = "avoid"


class ChatRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


def _str_enum(enum_cls: type[enum.Enum]) -> SAEnum:
    return SAEnum(
        enum_cls,
        native_enum=False,
        create_constraint=False,
        length=32,
        values_callable=lambda e: [member.value for member in e],
        validate_strings=True,
    )


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    wardrobe_items: Mapped[list[WardrobeItem]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    outfits: Mapped[list[Outfit]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    preferences: Mapped[list[Preference]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    feedback: Mapped[list[Feedback]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    chat_messages: Mapped[list[ChatMessage]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ChatMessage.created_at",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"


class WardrobeItem(TimestampMixin, Base):
    """One individual clothing item uploaded by a user.

    `category`, `color`, `pattern` and `style` are nullable: they are filled by
    image analysis (Phase 4) and may be corrected by the user.
    """

    __tablename__ = "wardrobe_items"
    __table_args__ = (
        CheckConstraint(
            "comfort_rating IS NULL OR (comfort_rating BETWEEN 1 AND 5)",
            name="comfort_rating_range",
        ),
        Index("ix_wardrobe_items_user_status", "user_id", "status"),
        Index("ix_wardrobe_items_user_category", "user_id", "category"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str | None] = mapped_column(String(120))
    image_path: Mapped[str] = mapped_column(String(500), nullable=False)

    category: Mapped[str | None] = mapped_column(String(50))
    color: Mapped[str | None] = mapped_column(String(50))
    pattern: Mapped[str | None] = mapped_column(String(50))
    style: Mapped[str | None] = mapped_column(String(50))

    status: Mapped[WardrobeItemStatus] = mapped_column(
        _str_enum(WardrobeItemStatus),
        default=WardrobeItemStatus.ACTIVE,
        server_default=WardrobeItemStatus.ACTIVE.value,
        nullable=False,
    )
    comfort_rating: Mapped[int | None] = mapped_column(SmallInteger)  # 1-5, user-reported
    is_favorite: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0", nullable=False
    )

    user: Mapped[User] = relationship(back_populates="wardrobe_items")
    outfit_links: Mapped[list[OutfitItem]] = relationship(
        back_populates="wardrobe_item", cascade="all, delete-orphan", passive_deletes=True
    )
    feedback: Mapped[list[Feedback]] = relationship(
        back_populates="wardrobe_item", passive_deletes=True
    )
    preferences: Mapped[list[Preference]] = relationship(
        back_populates="wardrobe_item", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<WardrobeItem id={self.id} category={self.category!r} status={self.status.value}>"


class Outfit(TimestampMixin, Base):
    """A generated or saved combination of wardrobe items (also the outfit history)."""

    __tablename__ = "outfits"
    __table_args__ = (Index("ix_outfits_user_created", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str | None] = mapped_column(String(120))
    occasion: Mapped[str | None] = mapped_column(String(100))  # e.g. "office", "date night"
    source: Mapped[OutfitSource] = mapped_column(
        _str_enum(OutfitSource),
        default=OutfitSource.RECOMMENDED,
        server_default=OutfitSource.RECOMMENDED.value,
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="outfits")
    items: Mapped[list[OutfitItem]] = relationship(
        back_populates="outfit",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="OutfitItem.position",
    )
    wardrobe_items: Mapped[list[WardrobeItem]] = relationship(
        secondary="outfit_items", viewonly=True
    )
    feedback: Mapped[list[Feedback]] = relationship(
        back_populates="outfit", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<Outfit id={self.id} occasion={self.occasion!r}>"


class OutfitItem(Base):
    """Association between an Outfit and the WardrobeItems it contains."""

    __tablename__ = "outfit_items"
    __table_args__ = (
        UniqueConstraint("outfit_id", "wardrobe_item_id", name="uq_outfit_items_outfit_item"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    outfit_id: Mapped[int] = mapped_column(
        ForeignKey("outfits.id", ondelete="CASCADE"), nullable=False, index=True
    )
    wardrobe_item_id: Mapped[int] = mapped_column(
        ForeignKey("wardrobe_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    slot: Mapped[str | None] = mapped_column(String(30))  # e.g. "top", "bottom", "outerwear"
    position: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)

    outfit: Mapped[Outfit] = relationship(back_populates="items")
    wardrobe_item: Mapped[WardrobeItem] = relationship(back_populates="outfit_links")

    def __repr__(self) -> str:
        return f"<OutfitItem outfit={self.outfit_id} item={self.wardrobe_item_id} slot={self.slot!r}>"


class Preference(TimestampMixin, Base):
    """A learned or stated user preference.

    Examples:
      "I love oversized shirts" -> dimension=style, value="oversized shirt", weight=+1.0
      "I don't like this shirt" -> dimension=item, wardrobe_item_id=<id>, weight=-0.6
      "Avoid these jeans"       -> dimension=item, wardrobe_item_id=<id>, weight=-1.0

    `weight`: sentiment strength in [-1, 1] (negative = dislike/avoid).
    `confidence`: how sure the system is, in [0, 1] (explicit statements high,
    inferred ones lower).
    """

    __tablename__ = "preferences"
    __table_args__ = (
        CheckConstraint("weight BETWEEN -1.0 AND 1.0", name="weight_range"),
        CheckConstraint("confidence BETWEEN 0.0 AND 1.0", name="confidence_range"),
        Index("ix_preferences_user_dimension", "user_id", "dimension"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    dimension: Mapped[PreferenceDimension] = mapped_column(
        _str_enum(PreferenceDimension), nullable=False
    )
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    wardrobe_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("wardrobe_items.id", ondelete="CASCADE"), index=True
    )
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(
        Float, default=1.0, server_default="1.0", nullable=False
    )
    source: Mapped[PreferenceSource] = mapped_column(_str_enum(PreferenceSource), nullable=False)
    source_text: Mapped[str | None] = mapped_column(Text)  # original statement, for traceability

    user: Mapped[User] = relationship(back_populates="preferences")
    wardrobe_item: Mapped[WardrobeItem | None] = relationship(back_populates="preferences")

    def __repr__(self) -> str:
        return f"<Preference {self.dimension.value}={self.value!r} w={self.weight}>"


class Feedback(Base):
    """Explicit user feedback about a wardrobe item and/or an outfit."""

    __tablename__ = "feedback"
    __table_args__ = (
        CheckConstraint(
            "wardrobe_item_id IS NOT NULL OR outfit_id IS NOT NULL",
            name="has_target",
        ),
        Index("ix_feedback_user_created", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    wardrobe_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("wardrobe_items.id", ondelete="CASCADE"), index=True
    )
    outfit_id: Mapped[int | None] = mapped_column(
        ForeignKey("outfits.id", ondelete="CASCADE"), index=True
    )
    feedback_type: Mapped[FeedbackType] = mapped_column(_str_enum(FeedbackType), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="feedback")
    wardrobe_item: Mapped[WardrobeItem | None] = relationship(back_populates="feedback")
    outfit: Mapped[Outfit | None] = relationship(back_populates="feedback")

    def __repr__(self) -> str:
        return f"<Feedback {self.feedback_type.value} item={self.wardrobe_item_id} outfit={self.outfit_id}>"


class ChatMessage(Base):
    """One message in the AI stylist conversation history."""

    __tablename__ = "chat_messages"
    __table_args__ = (Index("ix_chat_messages_user_created", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[ChatRole] = mapped_column(_str_enum(ChatRole), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="chat_messages")

    def __repr__(self) -> str:
        return f"<ChatMessage {self.role.value}: {self.message[:30]!r}>"
