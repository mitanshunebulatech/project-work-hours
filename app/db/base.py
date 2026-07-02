"""
app/db/base.py
Single shared declarative base. All ORM models inherit from this so that
Alembic's autogenerate can discover every table via Base.metadata.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
