"""Turn an untrusted PDF or photo into what the model sees: a few page images plus the text layer.

- PDF: the first `max_pages` pages rendered at ~150 dpi (long side at most 1,600 px), plus the text
  layer for the presence checks.
- Photo: EXIF orientation applied, downscaled, re-encoded as JPEG. Re-encoding drops all metadata
  (EXIF, GPS) before anything leaves the system.
- Pillow's decompression-bomb guard is kept (huge pixel counts are rejected).
"""

import io
from dataclasses import dataclass

import pypdfium2 as pdfium
from PIL import Image, ImageOps, UnidentifiedImageError

from belegfluss.reading.classify import ReadingError, pdf_text

PDF_SCALE = 150 / 72  # PDF points -> pixels at ~150 dpi
PDF_MAX_SIDE = 1600
PHOTO_MAX_SIDE = 2048
Image.MAX_IMAGE_PIXELS = 50_000_000  # Pillow refuses images with more than twice this


@dataclass(frozen=True)
class Prepared:
    images: list[tuple[str, bytes]]  # (media type, bytes)
    text: str  # text layer ('' for photos and scans)
    pages: int  # pages in the original document


def _fit(image: Image.Image, max_side: int) -> Image.Image:
    image = image.convert("RGB")
    image.thumbnail((max_side, max_side))
    return image


def _encode(image: Image.Image, media_type: str) -> bytes:
    out = io.BytesIO()
    if media_type == "image/png":
        image.save(out, format="PNG", optimize=True)
    else:
        image.save(out, format="JPEG", quality=85)
    return out.getvalue()


def prepare_pdf(pdf: bytes, max_pages: int) -> Prepared:
    try:
        document = pdfium.PdfDocument(pdf)
    except pdfium.PdfiumError as exc:
        raise ReadingError("BF-PDF-UNREADABLE") from exc
    try:
        images = []
        for index in range(min(len(document), max_pages)):
            page = document[index]
            bitmap = page.render(scale=PDF_SCALE)
            images.append(("image/png", _encode(_fit(bitmap.to_pil(), PDF_MAX_SIDE), "image/png")))
            page.close()
        pages = len(document)
    finally:
        document.close()
    return Prepared(images=images, text=pdf_text(pdf, max_pages), pages=pages)


def prepare_photo(data: bytes) -> Prepared:
    try:
        with Image.open(io.BytesIO(data)) as original:
            upright = ImageOps.exif_transpose(original)
            jpeg = _encode(_fit(upright, PHOTO_MAX_SIDE), "image/jpeg")
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as exc:
        raise ReadingError("BF-IMAGE-UNREADABLE") from exc
    return Prepared(images=[("image/jpeg", jpeg)], text="", pages=1)


def prepare(data: bytes, media_type: str, max_pages: int) -> Prepared:
    if media_type == "application/pdf":
        return prepare_pdf(data, max_pages)
    return prepare_photo(data)
