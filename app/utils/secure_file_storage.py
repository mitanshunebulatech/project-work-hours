"""
app/utils/secure_file_storage.py

Encrypted-at-rest storage for identity documents (Aadhaar/PAN/Passport/Other
scans) — same posture as app/utils/file_storage.py (leave attachments), plus
Fernet encryption via app.core.encryption, since these files are higher-
sensitivity than a leave attachment.

Security notes (same reasoning as file_storage.py):
- The original filename is NEVER trusted for the on-disk name — only its
  extension is kept, validated against an allow-list, and the stored name
  is a fresh UUID.
- Files are saved outside anything served statically. The only way to read
  one back is through an authenticated endpoint that decrypts on the way
  out — a raw file on disk is ciphertext, useless without the app's
  FIELD_ENCRYPTION_KEY.
"""

import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings
from app.core.encryption import decrypt_bytes, encrypt_bytes
from app.core.exceptions import ValidationError

MAX_IDENTITY_DOC_BYTES = settings.MAX_IDENTITY_DOC_SIZE_MB * 1024 * 1024


def _upload_dir() -> Path:
    upload_dir = Path(settings.IDENTITY_DOCS_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def save_identity_document_file(file: UploadFile) -> str:
    """
    Validates extension + size, encrypts the contents, writes under a fresh
    UUID name, and returns the relative path to store on
    IdentityDocument.file_path. Raises ValidationError (422) on any rule
    violation — caller doesn't need to pre-check anything.
    """
    original_name = file.filename or ""
    extension = Path(original_name).suffix.lower()

    if extension not in settings.ALLOWED_IDENTITY_DOC_EXTENSIONS:
        allowed = ", ".join(settings.ALLOWED_IDENTITY_DOC_EXTENSIONS)
        raise ValidationError(f"Unsupported file type '{extension}'. Allowed types: {allowed}")

    contents = file.file.read()
    if len(contents) > MAX_IDENTITY_DOC_BYTES:
        raise ValidationError(
            f"File exceeds the maximum allowed size of {settings.MAX_IDENTITY_DOC_SIZE_MB}MB"
        )
    if len(contents) == 0:
        raise ValidationError("Uploaded file is empty")

    encrypted = encrypt_bytes(contents)

    stored_name = f"{uuid.uuid4().hex}{extension}"
    destination = _upload_dir() / stored_name
    destination.write_bytes(encrypted)

    return f"{Path(settings.IDENTITY_DOCS_DIR).name}/{stored_name}"


def read_identity_document_file(file_path: str) -> bytes:
    """
    Resolves a stored relative path, reads the encrypted bytes, and decrypts
    before returning — mirrors resolve_attachment_path's traversal defense.
    """
    candidate = _resolve_path(file_path)
    encrypted = candidate.read_bytes()
    return decrypt_bytes(encrypted)


def delete_identity_document_file(file_path: str) -> None:
    """Removes the file from disk. Silently no-ops if it's already gone —
    callers (IdentityDocumentRepository delete flows) shouldn't have to
    special-case a file that was manually cleaned up already."""
    candidate = _resolve_path(file_path)
    candidate.unlink(missing_ok=True)


def _resolve_path(file_path: str) -> Path:
    base_dir = Path(settings.IDENTITY_DOCS_DIR).resolve()
    stored_name = Path(file_path).name  # strip any directory component
    candidate = (base_dir / stored_name).resolve()

    if base_dir not in candidate.parents and candidate != base_dir:
        raise ValidationError("Invalid file path")

    return candidate
