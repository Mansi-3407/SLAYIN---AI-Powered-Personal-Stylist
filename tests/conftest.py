"""Shared pytest fixtures.

Database tests use an isolated in-memory SQLite engine, never the production DB.
"""

import pytest
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.database import Base, User
from src.database.db_config import create_db_engine


@pytest.fixture()
def db_engine():
    engine = create_db_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # one shared connection so the in-memory DB persists
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def db_session(db_engine) -> Session:
    session = sessionmaker(bind=db_engine, autoflush=False, expire_on_commit=False)()
    yield session
    session.rollback()
    session.close()


@pytest.fixture()
def user(db_session) -> User:
    u = User(name="Test User", email="test@slayin.dev")
    db_session.add(u)
    db_session.commit()
    return u
