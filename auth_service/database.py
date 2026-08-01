"""Database construction kept separate from the analysis service database."""

from __future__ import annotations

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def build_engine(database_url: str) -> Engine:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args, pool_pre_ping=True)


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def initialize_database(engine: Engine) -> None:
    from auth_service import models  # noqa: F401

    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    user_columns = {column["name"] for column in inspector.get_columns("auth_users")}
    user_column_migrations = {
        "username": "ALTER TABLE auth_users ADD COLUMN username VARCHAR(80) NULL",
        "access_role": "ALTER TABLE auth_users ADD COLUMN access_role VARCHAR(20) NULL",
    }
    for column_name, statement in user_column_migrations.items():
        if column_name in user_columns:
            continue
        with engine.begin() as connection:
            connection.execute(text(statement))

    event_columns = {
        column["name"] for column in inspector.get_columns("auth_approval_events")
    }
    event_column_migrations = {
        "previous_role": (
            "ALTER TABLE auth_approval_events ADD COLUMN previous_role VARCHAR(20) NULL"
        ),
        "new_role": "ALTER TABLE auth_approval_events ADD COLUMN new_role VARCHAR(20) NULL",
    }
    for column_name, statement in event_column_migrations.items():
        if column_name in event_columns:
            continue
        with engine.begin() as connection:
            connection.execute(text(statement))

    inspector = inspect(engine)
    user_indexes = {index["name"] for index in inspector.get_indexes("auth_users")}
    if "ix_auth_users_username" not in user_indexes:
        with engine.begin() as connection:
            connection.execute(
                text("CREATE UNIQUE INDEX ix_auth_users_username ON auth_users (username)")
            )
    if "ix_auth_users_access_role" not in user_indexes:
        with engine.begin() as connection:
            connection.execute(
                text("CREATE INDEX ix_auth_users_access_role ON auth_users (access_role)")
            )

    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE auth_users SET access_role = 'ADMIN' "
                "WHERE is_admin = 1 AND access_role IS NULL"
            )
        )
        connection.execute(
            text(
                "UPDATE auth_users SET access_role = 'VIEWER' "
                "WHERE is_admin = 0 AND status = 'APPROVED' AND access_role IS NULL"
            )
        )
