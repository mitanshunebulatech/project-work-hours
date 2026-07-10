"""
tests/conftest.py
"""

import os

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://workhours:workhours@localhost:5432/workhours_db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only")
os.environ.setdefault("FIELD_ENCRYPTION_KEY", "Ge2NZJCRn54UbRFcliOegTdclflnEa8ckXllzaqP25c=")

