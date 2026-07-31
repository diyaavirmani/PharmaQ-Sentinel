from __future__ import annotations

import hashlib
import re
from pathlib import Path
from uuid import uuid4

from app.core.exceptions import PharmaQSentinelError

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".eml"}
EXECUTABLE_EXTENSIONS = {".exe", ".bat", ".cmd", ".ps1", ".js", ".vbs", ".scr", ".msi", ".dll"}
MIME_BY_EXTENSION = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
    ".eml": "message/rfc822",
}
SAFE_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9._ -]+")


def sanitize_filename(filename: str) -> str:
    name = Path(filename).name
    cleaned = SAFE_FILENAME_PATTERN.sub("_", name).strip(" .")
    return cleaned or "uploaded-document"


def safe_stored_filename(original_filename: str) -> str:
    suffix = Path(sanitize_filename(original_filename)).suffix.lower()
    return f"{uuid4()}{suffix}"


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def validate_extension(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in EXECUTABLE_EXTENSIONS:
        raise PharmaQSentinelError("Executable uploads are not allowed", status_code=422)
    if suffix not in ALLOWED_EXTENSIONS:
        raise PharmaQSentinelError("Unsupported document format", status_code=422)
    return suffix


def detect_mime(content: bytes, filename: str) -> str:
    suffix = validate_extension(filename)
    if suffix == ".pdf":
        if not content.startswith(b"%PDF-"):
            raise PharmaQSentinelError("File extension does not match detected content type", status_code=422)
        return "application/pdf"
    if suffix == ".docx":
        if not content.startswith(b"PK\x03\x04"):
            raise PharmaQSentinelError("File extension does not match detected content type", status_code=422)
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if suffix == ".eml":
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise PharmaQSentinelError("Uploaded file could not be safely decoded", status_code=422) from exc
        if not (
            text[:64].lower().startswith("subject:")
            or "\nsubject:" in text[:4096].lower()
            or "\nfrom:" in text[:4096].lower()
        ):
            raise PharmaQSentinelError("File extension does not match detected content type", status_code=422)
        return "message/rfc822"

    try:
        content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PharmaQSentinelError("Uploaded file could not be safely decoded", status_code=422) from exc
    return "text/plain"


def ensure_safe_child_path(base_directory: Path, stored_filename: str) -> Path:
    base = base_directory.resolve()
    path = (base / stored_filename).resolve()
    if base != path.parent:
        raise PharmaQSentinelError("Unsafe upload storage path", status_code=422)
    return path
