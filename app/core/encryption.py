"""
app/core/encryption.py
Field-level encryption for sensitive columns (e.g. PAN on employee_profiles).
No business logic lives here — pure cryptographic primitives only, mirroring
the separation already established in app/core/security.py.
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import String
from sqlalchemy.types import TypeDecorator

from app.core.config import settings


def _get_fernet() -> Fernet:
    # Not module-level: settings.FIELD_ENCRYPTION_KEY must be read lazily so tests
    # that override the env var before import still take effect.
    return Fernet(settings.FIELD_ENCRYPTION_KEY.encode())


class EncryptedString(TypeDecorator):
    """
    Transparently encrypts on write / decrypts on read. Stored ciphertext is
    base64 text, so the underlying column is a plain String — no DB-side
    crypto extension required, portable across Postgres and SQLite alike.
    """

    impl = String
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect) -> str | None:
        if value is None:
            return None
        return _get_fernet().encrypt(value.encode()).decode()

    def process_result_value(self, value: str | None, dialect) -> str | None:
        if value is None:
            return None
        try:
            return _get_fernet().decrypt(value.encode()).decode()
        except InvalidToken as exc:
            # Surfaces a wrong/rotated key clearly rather than returning garbage bytes.
            raise ValueError("Unable to decrypt field — encryption key mismatch") from exc
