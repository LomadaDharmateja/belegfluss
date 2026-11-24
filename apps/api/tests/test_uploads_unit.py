"""Unit tests for type detection and file-name cleaning (no containers needed)."""

import io

import pytest

from belegfluss.errors import AppError
from belegfluss.uploads import check_upload, detect_media_type, safe_filename


@pytest.mark.parametrize(
    ("head", "expected"),
    [
        (b"%PDF-1.4\n", "application/pdf"),
        (b"\x89PNG\r\n\x1a\n....", "image/png"),
        (b"\xff\xd8\xff\xdb", "image/jpeg"),
        (b'<?xml version="1.0"?><a/>', "application/xml"),
        (b"\xef\xbb\xbf<?xml version='1.0'?>", "application/xml"),
        (b"  \n<rsm:CrossIndustryInvoice xmlns:rsm='x'>", "application/xml"),
        (b"<Invoice>", "application/xml"),
        (b"<!-- comment --><Invoice/>", "application/xml"),
        (b"<!DOCTYPE html>", None),
        (b"<html lang='de'>", None),
        (b"plain text", None),
        (b"", None),
    ],
)
def test_detect_media_type(head: bytes, expected: str | None) -> None:
    assert detect_media_type(head) == expected


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Rechnung.pdf", "Rechnung.pdf"),
        ("../../etc/passwd", "passwd"),
        ("C:\\Users\\x\\Beleg Mai.pdf", "Beleg Mai.pdf"),
        ("bad\x00name\n.xml", "bad_name_.xml"),
        ("Größe ÄÖÜ ß.xml", "Größe ÄÖÜ ß.xml"),
        ("", "upload"),
        (None, "upload"),
        ("a" * 300 + ".pdf", "a" * 255),
    ],
)
def test_safe_filename(name: str | None, expected: str) -> None:
    assert safe_filename(name) == expected


def test_check_upload_counts_bytes_and_rewinds() -> None:
    stream = io.BytesIO(b"%PDF-1.7\n" + b"x" * 5000)
    checked = check_upload(stream, max_bytes=10_000)
    assert checked.size_bytes == 5009
    assert stream.tell() == 0


def test_check_upload_stops_at_limit() -> None:
    with pytest.raises(AppError) as excinfo:
        check_upload(io.BytesIO(b"%PDF-" + b"x" * 100), max_bytes=50)
    assert excinfo.value.code == "upload.too_large"
