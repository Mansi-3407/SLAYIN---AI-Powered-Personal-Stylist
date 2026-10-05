"""Alembic migration tests: run against a fresh temporary SQLite file."""

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import inspect

from config import BASE_DIR
from src.database import Base
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


def _alembic_config(db_url: str) -> Config:
    cfg = Config(str(BASE_DIR / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", db_url)
    cfg.attributes["configure_logger"] = False
    return cfg


def test_upgrade_head_matches_models_and_downgrades_cleanly(tmp_path):
    db_url = f"sqlite:///{(tmp_path / 'migration_test.db').as_posix()}"
    cfg = _alembic_config(db_url)
    engine = create_db_engine(db_url)

    try:
        command.upgrade(cfg, "head")
        assert EXPECTED_TABLES <= set(inspect(engine).get_table_names())

        # Migrations and ORM models must be in sync (no pending autogenerate diff).
        with engine.connect() as conn:
            diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
        assert diff == [], f"Models and migrations out of sync: {diff}"

        command.downgrade(cfg, "base")
        remaining = set(inspect(engine).get_table_names()) - {"alembic_version"}
        assert remaining == set()
    finally:
        engine.dispose()
