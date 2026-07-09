"""
app/utils/file_storage.py

Local-disk storage for leave-request attachments. Deliberately not S3/cloud —
there's no cloud SDK or credentials anywhere in this project yet, so that
would be a much larger, unrelated infrastructure change. This keeps the same
"local disk, swap later" posture the rest of the app uses (e.g. SQLite-free,
single Postgres instance).

Security notes:
- The original filename is NEVER trusted for the on-disk name (path traversal,
  collisions, weird characters) — only its extension is kept, validated
  against an allow-list, and the actual filename is a fresh UUID.
- Files are saved outside any directory FastAPI serves statically, so the
  only way to read one back is through the authenticated
  GET /leave-requests/{id}/attachment endpoint (see leave_service.py), which
  checks the requester is the request's own employee or an admin.
"""

import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import ValidationError

MAX_ATTACHMENT_BYTES = settings.MAX_ATTACHMENT_SIZE_MB * 1024 * 1024


def _upload_dir() -> Path:
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def save_attachment_file(file: UploadFile) -> str:
    """
    Validates extension + size, writes the file under a fresh UUID name, and
    returns the relative path to store on LeaveRequestCreate.attachment_path.
    Raises ValidationError (422) on any rule violation — caller doesn't need
    to pre-check anything.
    """
    original_name = file.filename or ""
    extension = Path(original_name).suffix.lower()

    if extension not in settings.ALLOWED_ATTACHMENT_EXTENSIONS:
        allowed = ", ".join(settings.ALLOWED_ATTACHMENT_EXTENSIONS)
        raise ValidationError(f"Unsupported file type '{extension}'. Allowed types: {allowed}")

    # UploadFile doesn't expose a reliable pre-read size, so we read once into
    # memory to check the limit before writing — fine at a 10MB ceiling, and
    # avoids partially writing an oversized file to disk first.
    contents = file.file.read()
    if len(contents) > MAX_ATTACHMENT_BYTES:
        raise ValidationError(
            f"File exceeds the maximum allowed size of {settings.MAX_ATTACHMENT_SIZE_MB}MB"
        )
    if len(contents) == 0:
        raise ValidationError("Uploaded file is empty")

    stored_name = f"{uuid.uuid4().hex}{extension}"
    destination = _upload_dir() / stored_name
    destination.write_bytes(contents)

    # Stored as "leave_attachments/<uuid>.ext" — relative, portable, and never
    # exposes the server's absolute filesystem layout.
    return f"{Path(settings.UPLOAD_DIR).name}/{stored_name}"


def resolve_attachment_path(attachment_path: str) -> Path:
    """
    Resolves a stored relative path back to an absolute Path, defending
    against path traversal (e.g. "../../etc/passwd") by rejecting anything
    that resolves outside the configured upload directory.
    """
    base_dir = Path(settings.UPLOAD_DIR).resolve()
    stored_name = Path(attachment_path).name  # strip any directory component
    candidate = (base_dir / stored_name).resolve()

    if base_dir not in candidate.parents and candidate != base_dir:
        raise ValidationError("Invalid attachment path")

    return candidate
