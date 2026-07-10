"""
tests/unit/test_encryption.py
"""

import pytest

from app.core.encryption import EncryptedString


def test_encrypt_then_decrypt_round_trips() -> None:
    field = EncryptedString(255)
    plaintext = "ABCDE1234F"

    ciphertext = field.process_bind_param(plaintext, dialect=None)
    assert ciphertext != plaintext  # never stored as plaintext
    assert isinstance(ciphertext, str)

    decrypted = field.process_result_value(ciphertext, dialect=None)
    assert decrypted == plaintext


def test_none_passes_through_unencrypted() -> None:
    field = EncryptedString(255)
    assert field.process_bind_param(None, dialect=None) is None
    assert field.process_result_value(None, dialect=None) is None


def test_tampered_ciphertext_raises_value_error() -> None:
    field = EncryptedString(255)
    ciphertext = field.process_bind_param("ABCDE1234F", dialect=None)
    tampered = ciphertext[:-1] + ("A" if ciphertext[-1] != "A" else "B")

    with pytest.raises(ValueError):
        field.process_result_value(tampered, dialect=None)


def test_same_plaintext_produces_different_ciphertext_each_time() -> None:
    """Fernet includes a random IV per encryption — two calls must not collide,
    so ciphertext alone can't be used to correlate records by PAN."""
    field = EncryptedString(255)
    a = field.process_bind_param("ABCDE1234F", dialect=None)
    b = field.process_bind_param("ABCDE1234F", dialect=None)
    assert a != b
