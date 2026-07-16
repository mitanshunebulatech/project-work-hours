"""
tests/unit/test_secure_file_storage.py
"""

import io
import shutil
from pathlib import Path

import pytest
from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import ValidationError
from app.utils.secure_file_storage import (
    delete_identity_document_file,
    read_identity_document_file,
    save_identity_document_file,
)


def _upload(filename: str, content: bytes) -> UploadFile:
    return UploadFile(file=io.BytesIO(content), filename=filename)


@pytest.fixture(autouse=True)
def _clean_upload_dir():
    """Identity docs write to disk under settings.IDENTITY_DOCS_DIR — use a
    throwaway test directory and clean it up after each test."""
    original_dir = settings.IDENTITY_DOCS_DIR
    settings.IDENTITY_DOCS_DIR = "uploads/test_identity_documents"
    yield
    shutil.rmtree(settings.IDENTITY_DOCS_DIR, ignore_errors=True)
    settings.IDENTITY_DOCS_DIR = original_dir


def test_save_and_read_round_trips() -> None:
    original = b"%PDF-1.4 fake aadhaar scan bytes"
    file_path = save_identity_document_file(_upload("aadhaar.pdf", original))

    recovered = read_identity_document_file(file_path)
    assert recovered == original


def test_file_is_encrypted_on_disk() -> None:
    """The raw bytes on disk must never equal the plaintext — that's the
    entire point of this module vs. the plain file_storage.py."""
    original = b"sensitive aadhaar number and scan content"
    file_path = save_identity_document_file(_upload("aadhaar.pdf", original))

    stored_name = Path(file_path).name
    raw_on_disk = (Path(settings.IDENTITY_DOCS_DIR) / stored_name).read_bytes()
    assert raw_on_disk != original


def test_rejects_disallowed_extension() -> None:
    with pytest.raises(ValidationError):
        save_identity_document_file(_upload("resume.exe", b"anything"))


def test_rejects_oversized_file() -> None:
    oversized = b"x" * (settings.MAX_IDENTITY_DOC_SIZE_MB * 1024 * 1024 + 1)
    with pytest.raises(ValidationError):
        save_identity_document_file(_upload("big.png", oversized))


def test_rejects_empty_file() -> None:
    with pytest.raises(ValidationError):
        save_identity_document_file(_upload("empty.png", b""))


def test_delete_removes_file_and_is_idempotent() -> None:
    file_path = save_identity_document_file(_upload("passport.jpg", b"scan bytes"))
    stored_name = Path(file_path).name
    on_disk = Path(settings.IDENTITY_DOCS_DIR) / stored_name
    assert on_disk.exists()

    delete_identity_document_file(file_path)
    assert not on_disk.exists()

    # Deleting again must not raise — callers shouldn't have to check existence first.
    delete_identity_document_file(file_path)


def test_path_traversal_is_neutralized() -> None:
    """
    Mirrors the same defense already used by resolve_attachment_path in
    app/utils/file_storage.py: only the filename component is ever used, so
    a path like "../../../etc/passwd" resolves to
    "<IDENTITY_DOCS_DIR>/passwd" — never actually escaping the sandboxed
    directory. It legitimately doesn't exist there, so this raises
    FileNotFoundError (not ValidationError) — proving the traversal attempt
    was neutralized rather than followed.
    """
    with pytest.raises(FileNotFoundError):
        read_identity_document_file("../../../etc/passwd")
