"""Unit tests for the SLAYIN data layer (Phase 1)."""

from datetime import datetime
import time

import pytest
from sqlalchemy import delete, func, inspect, select
from sqlalchemy.exc import IntegrityError, StatementError

from src.database import (
    Base,
    ChatMessage,
    ChatRole,
    Feedback,
    FeedbackType,
    Outfit,
    OutfitItem,
    OutfitSource,
    Preference,
    PreferenceDimension,
    PreferenceSource,
    User,
    WardrobeItem,
    WardrobeItemStatus,
)
from src.database.db_config import create_db_engine

EXPECTED_TABLES = {
    "users",
    "wardrobe_items",
    "outfits",
    "outfit_items",
    "preferences",
    "feedback",
    "chat_messages",
}


def _item(user: User, **kw) -> WardrobeItem:
    defaults = dict(user=user, image_path="data/raw/user_images/1/x.jpg")
    defaults.update(kw)
    return WardrobeItem(**defaults)


# 1. Database can be created ---------------------------------------------------
def test_database_file_can_be_created(tmp_path):
    db_file = tmp_path / "nested" / "slayin_test.db"
    engine = create_db_engine(f"sqlite:///{db_file.as_posix()}")
    Base.metadata.create_all(engine)
    engine.dispose()
    assert db_file.exists()


# 2. Tables can be created -----------------------------------------------------
def test_all_tables_created(db_engine):
    assert EXPECTED_TABLES <= set(inspect(db_engine).get_table_names())


def test_sqlite_foreign_keys_enabled(db_engine):
    with db_engine.connect() as conn:
        assert conn.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1


# 3. User insert ---------------------------------------------------------------
def test_insert_user(db_session, user):
    fetched = db_session.scalar(select(User).where(User.email == "test@slayin.dev"))
    assert fetched is not None
    assert fetched.id == user.id
    assert fetched.name == "Test User"


def test_user_email_unique(db_session, user):
    db_session.add(User(name="Dup", email="test@slayin.dev"))
    with pytest.raises(IntegrityError):
        db_session.commit()


# 4. WardrobeItem <-> User -----------------------------------------------------
def test_wardrobe_item_belongs_to_user(db_session, user):
    item = _item(user, name="White oversized shirt", category="long sleeve top", color="white")
    db_session.add(item)
    db_session.commit()

    assert item.user_id == user.id
    assert item.status is WardrobeItemStatus.ACTIVE  # default
    assert item.is_favorite is False
    db_session.refresh(user)
    assert user.wardrobe_items == [item]


def test_wardrobe_item_comfort_rating_range(db_session, user):
    db_session.add(_item(user, comfort_rating=9))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_invalid_enum_value_rejected(db_session, user):
    db_session.add(_item(user, status="lost_in_space"))
    with pytest.raises(StatementError):
        db_session.commit()


# 5. Outfit with multiple WardrobeItems ---------------------------------------
def test_outfit_contains_multiple_items(db_session, user):
    shirt = _item(user, category="long sleeve top")
    jeans = _item(user, category="trousers")
    jacket = _item(user, category="long sleeve outwear")
    outfit = Outfit(user=user, name="Casual Friday", occasion="office", source=OutfitSource.RECOMMENDED)
    outfit.items = [
        OutfitItem(wardrobe_item=shirt, slot="top", position=0),
        OutfitItem(wardrobe_item=jeans, slot="bottom", position=1),
        OutfitItem(wardrobe_item=jacket, slot="outerwear", position=2),
    ]
    db_session.add(outfit)
    db_session.commit()
    db_session.expire_all()

    loaded = db_session.get(Outfit, outfit.id)
    assert [link.slot for link in loaded.items] == ["top", "bottom", "outerwear"]
    assert {w.id for w in loaded.wardrobe_items} == {shirt.id, jeans.id, jacket.id}
    assert len(shirt.outfit_links) == 1


def test_outfit_cannot_contain_same_item_twice(db_session, user):
    shirt = _item(user)
    outfit = Outfit(user=user)
    outfit.items = [OutfitItem(wardrobe_item=shirt), OutfitItem(wardrobe_item=shirt)]
    db_session.add(outfit)
    with pytest.raises(IntegrityError):
        db_session.commit()


# 6. Preference / Feedback / ChatMessage <-> User -----------------------------
def test_preferences_associated_with_user(db_session, user):
    jeans = _item(user, category="trousers")
    db_session.add_all(
        [
            Preference(
                user=user,
                dimension=PreferenceDimension.STYLE,
                value="oversized shirt",
                weight=1.0,
                confidence=0.9,
                source=PreferenceSource.CHAT,
                source_text="I love oversized shirts.",
            ),
            Preference(
                user=user,
                dimension=PreferenceDimension.ITEM,
                value="avoid",
                wardrobe_item=jeans,
                weight=-1.0,
                source=PreferenceSource.CHAT,
                source_text="Avoid these jeans.",
            ),
        ]
    )
    db_session.commit()
    db_session.refresh(user)

    assert len(user.preferences) == 2
    avoid = next(p for p in user.preferences if p.dimension is PreferenceDimension.ITEM)
    assert avoid.wardrobe_item_id == jeans.id
    assert avoid.confidence == 1.0  # default
    assert jeans.preferences == [avoid]


def test_preference_weight_range_enforced(db_session, user):
    db_session.add(
        Preference(user=user, dimension=PreferenceDimension.COLOR, value="neon", weight=5.0,
                   source=PreferenceSource.MANUAL)
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_feedback_on_item_and_outfit(db_session, user):
    shirt = _item(user)
    outfit = Outfit(user=user, items=[OutfitItem(wardrobe_item=shirt)])
    db_session.add_all(
        [
            Feedback(user=user, wardrobe_item=shirt, feedback_type=FeedbackType.UNCOMFORTABLE,
                     comment="Too tight at the shoulders"),
            Feedback(user=user, outfit=outfit, feedback_type=FeedbackType.LIKED),
            Feedback(user=user, wardrobe_item=shirt, feedback_type=FeedbackType.GIVEN_AWAY),
        ]
    )
    db_session.commit()
    db_session.refresh(user)

    assert {f.feedback_type for f in user.feedback} == {
        FeedbackType.UNCOMFORTABLE, FeedbackType.LIKED, FeedbackType.GIVEN_AWAY
    }
    assert len(shirt.feedback) == 2
    assert outfit.feedback[0].feedback_type is FeedbackType.LIKED


def test_feedback_requires_a_target(db_session, user):
    db_session.add(Feedback(user=user, feedback_type=FeedbackType.DISLIKED))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_chat_messages_associated_with_user(db_session, user):
    db_session.add_all(
        [
            ChatMessage(user=user, role=ChatRole.USER, message="What should I wear to a wedding?"),
            ChatMessage(user=user, role=ChatRole.ASSISTANT, message="Try your navy blazer with..."),
        ]
    )
    db_session.commit()
    db_session.refresh(user)

    assert [m.role for m in user.chat_messages] == [ChatRole.USER, ChatRole.ASSISTANT]


# 7. Foreign keys --------------------------------------------------------------
def test_foreign_key_rejects_unknown_user(db_session):
    db_session.add(WardrobeItem(user_id=9999, image_path="x.jpg"))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_deleting_user_cascades_at_db_level(db_session, user):
    shirt = _item(user)
    outfit = Outfit(user=user, items=[OutfitItem(wardrobe_item=shirt)])
    db_session.add_all(
        [
            outfit,
            Preference(user=user, dimension=PreferenceDimension.COLOR, value="black", weight=0.8,
                       source=PreferenceSource.MANUAL),
            Feedback(user=user, wardrobe_item=shirt, feedback_type=FeedbackType.LIKED),
            ChatMessage(user=user, role=ChatRole.USER, message="hi"),
        ]
    )
    db_session.commit()

    # Raw SQL delete (bypasses ORM cascades) to prove ON DELETE CASCADE works in SQLite.
    db_session.execute(delete(User).where(User.id == user.id))
    db_session.commit()

    for model in (WardrobeItem, Outfit, OutfitItem, Preference, Feedback, ChatMessage):
        assert db_session.scalar(select(func.count()).select_from(model)) == 0, model.__name__


def test_deleting_wardrobe_item_removes_outfit_links(db_session, user):
    shirt, jeans = _item(user), _item(user)
    outfit = Outfit(user=user, items=[OutfitItem(wardrobe_item=shirt), OutfitItem(wardrobe_item=jeans)])
    db_session.add(outfit)
    db_session.commit()

    db_session.delete(shirt)
    db_session.commit()
    db_session.expire_all()

    assert [link.wardrobe_item_id for link in db_session.get(Outfit, outfit.id).items] == [jeans.id]


# 8. Timestamps ----------------------------------------------------------------
def test_timestamps_populated(db_session, user):
    shirt = _item(user)
    outfit = Outfit(user=user)
    pref = Preference(user=user, dimension=PreferenceDimension.FIT, value="oversized", weight=1.0,
                      source=PreferenceSource.CHAT)
    fb = Feedback(user=user, wardrobe_item=shirt, feedback_type=FeedbackType.LIKED)
    msg = ChatMessage(user=user, role=ChatRole.USER, message="hello")
    db_session.add_all([shirt, outfit, pref, fb, msg])
    db_session.commit()

    for obj in (user, shirt, outfit, pref):
        assert isinstance(obj.created_at, datetime)
        assert isinstance(obj.updated_at, datetime)
    for obj in (fb, msg):
        assert isinstance(obj.created_at, datetime)


def test_updated_at_changes_on_update(db_session, user):
    shirt = _item(user)
    db_session.add(shirt)
    db_session.commit()
    created, first_updated = shirt.created_at, shirt.updated_at

    time.sleep(0.01)
    shirt.status = WardrobeItemStatus.DAMAGED
    db_session.commit()

    assert shirt.updated_at > first_updated
    assert shirt.created_at == created


def test_server_default_timestamps_on_raw_insert(db_session, user):
    """DB-level CURRENT_TIMESTAMP fallback works for rows inserted outside the ORM."""
    db_session.execute(
        WardrobeItem.__table__.insert().values(user_id=user.id, image_path="raw.jpg")
    )
    db_session.commit()
    row = db_session.scalar(select(WardrobeItem).where(WardrobeItem.image_path == "raw.jpg"))
    assert row.created_at is not None and row.updated_at is not None
    assert row.status is WardrobeItemStatus.ACTIVE
