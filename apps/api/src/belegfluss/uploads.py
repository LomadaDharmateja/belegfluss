"""Upload checks: size limit, file type from the content (not the name), SHA-256.

M1 accepts PDF, XML (UTF-8), PNG and JPEG. Parsing and validation follow in M2.
"""

import hashlib
import re
from dataclasses import dataclass
from typing import BinaryIO

from belegfluss.errors import AppError

CHUNK_SIZE = 1024 * 1024
_UTF8_BOM = b"\xef\xbb\xbf"
# An XML declaration, a comment, or a (possibly prefixed) root element such as <ubl:Invoice ...>.
_XML_START = re.compile(rb"<(\?xml[\s?]|!--|[A-Za-z_][\w.\-]*(:[A-Za-z_][\w.\-]*)?[\s/>])")


@dataclass(frozen=True)
class CheckedUpload:
    media_type: str
    size_bytes: int
    sha256: str


def detect_media_type(head: bytes) -> str | None:
    """Recognise the supported formats by their first bytes."""
    if head.startswith(b"%PDF-"):
        return "application/pdf"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    text = head.removeprefix(_UTF8_BOM).lstrip()
    if _XML_START.match(text) and not text[:20].lower().startswith((b"<!doctype", b"<html")):
        return "application/xml"
    return None


def check_upload(stream: BinaryIO, max_bytes: int) -> CheckedUpload:
    """Read the stream once: enforce the size limit, detect the type, compute SHA-256.

    The stream is rewound afterwards so it can be stored.
    """
    digest = hashlib.sha256()
    size = 0
    head = b""
    while chunk := stream.read(CHUNK_SIZE):
        if not head:
            head = chunk[:1024]
        size += len(chunk)
        if size > max_bytes:
            raise AppError(413, "upload.too_large", f"File is larger than {max_bytes} bytes.")
        digest.update(chunk)
    stream.seek(0)

    if size == 0:
        raise AppError(400, "upload.empty", "The file is empty.")
    media_type = detect_media_type(head)
    if media_type is None:
        raise AppError(
            415, "upload.unsupported_type", "Only PDF, XML, PNG and JPEG files are supported."
        )
    return CheckedUpload(media_type=media_type, size_bytes=size, sha256=digest.hexdigest())


_UNSAFE_CHARS = re.compile(r"[\x00-\x1f\x7f/\\]")


def safe_filename(name: str | None) -> str:
    """Keep the user's file name for display, without path parts or control characters."""
    if not name:
        return "upload"
    base = name.replace("\\", "/").rsplit("/", 1)[-1]
    cleaned = _UNSAFE_CHARS.sub("_", base).strip() or "upload"
    return cleaned[:255]
