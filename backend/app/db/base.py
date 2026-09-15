"""Declarative base + table creation helper.

No migration tool (e.g. Alembic) yet — acceptable while the schema is still
this small and fluid. Worth adding once the schema stabilizes and there's
data in a shared environment worth preserving across changes.
"""

from sqlalchemy.orm import DeclarativeBase

from app.db.session import engine


class Base(DeclarativeBase):
    pass


def create_all() -> None:
    # Import models here so they're registered on Base.metadata before
    # create_all runs, without forcing every caller of this module to know
    # which models exist.
    from app.models import analysis  # noqa: F401

    Base.metadata.create_all(bind=engine)
