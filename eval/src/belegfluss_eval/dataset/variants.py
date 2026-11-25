"""Photo and scan variants of one-page documents (ADR-0018).

- Phone photo (JPEG): the sheet on a desk, seen slightly from the side and rotated, uneven light, a
  warm colour cast, blur and sensor noise.
- Scan (PDF): grey, slightly skewed, light noise, 200 dpi, an image only (no text layer, so the
  presence check has nothing to compare and is skipped, as for real scans).
Every random choice comes from the document's seed, so a rebuild makes the same kind of image.
"""

import io
import random

import pypdfium2 as pdfium
from PIL import Image, ImageChops, ImageFilter

DESK_COLOURS = [(92, 74, 58), (140, 140, 138), (200, 190, 170), (60, 62, 66)]


def _page(pdf: bytes, scale: float) -> Image.Image:
    document = pdfium.PdfDocument(pdf)
    try:
        image: Image.Image = document[0].render(scale=scale).to_pil().convert("RGB")
    finally:
        document.close()
    return image


def photo(pdf: bytes, seed: int) -> bytes:
    rng = random.Random(seed)  # noqa: S311 (test data, not security)
    sheet = _page(pdf, scale=2.2)
    width, height = sheet.size
    desk = rng.choice(DESK_COLOURS)

    def jitter() -> float:
        return rng.uniform(0.0, 0.04)

    # Corners of the source area: upper-left, lower-left, lower-right, upper-right.
    quad = (
        -width * jitter(), -height * jitter(),
        -width * jitter(), height * (1 + jitter()),
        width * (1 + jitter()), height * (1 + jitter()),
        width * (1 + jitter()), -height * jitter(),
    )  # fmt: skip
    image = sheet.transform(
        (width, height), Image.Transform.QUAD, quad, Image.Resampling.BICUBIC, fillcolor=desk
    )
    image = image.rotate(rng.uniform(-4, 4), Image.Resampling.BICUBIC, expand=True, fillcolor=desk)
    strength = rng.uniform(0.15, 0.35)
    # Light from one side: a linear gradient turned to one of four directions.
    direction = rng.choice([None, Image.Transpose.ROTATE_90, Image.Transpose.ROTATE_180,
                            Image.Transpose.ROTATE_270])  # fmt: skip
    gradient = Image.linear_gradient("L")
    if direction is not None:
        gradient = gradient.transpose(direction)
    gradient = gradient.resize(image.size)
    shade = gradient.point(lambda v: 255 - int(v * strength))
    image = ImageChops.multiply(image, Image.merge("RGB", (shade, shade, shade)))
    image = Image.blend(image, Image.new("RGB", image.size, (255, 236, 200)), 0.06)
    image = image.filter(ImageFilter.GaussianBlur(rng.uniform(0.6, 1.3)))
    noise = Image.effect_noise(image.size, rng.uniform(8, 18)).convert("RGB")
    image = Image.blend(image, noise, rng.uniform(0.04, 0.09))
    image.thumbnail((2200, 2200))
    out = io.BytesIO()
    image.save(out, format="JPEG", quality=rng.randrange(65, 86))
    return out.getvalue()


def scan(pdf: bytes, seed: int) -> bytes:
    rng = random.Random(seed)  # noqa: S311 (test data, not security)
    image = _page(pdf, scale=200 / 72).convert("L")
    image = image.rotate(rng.uniform(-1.2, 1.2), Image.Resampling.BICUBIC, fillcolor=255)
    image = image.filter(ImageFilter.GaussianBlur(0.4))
    image = Image.blend(image, Image.effect_noise(image.size, 10), 0.03)
    out = io.BytesIO()
    image.save(out, format="PDF", resolution=200.0)
    return out.getvalue()
