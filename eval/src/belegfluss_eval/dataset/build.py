"""Build the labelled set once: render, make variants, split, write the manifest, package.

The result is frozen (ADR-0018): the ZIP becomes a release asset and the manifest records every
SHA-256. A rebuild gives the same labels and splits; file bytes may differ (PDF timestamps), so
every run uses the released files, not a rebuild.
"""

import hashlib
import random
import shutil
import subprocess
import zipfile
from dataclasses import dataclass
from pathlib import Path

import pypdfium2 as pdfium
from belegfluss.reading import InvoiceModel

from belegfluss_eval import manifest
from belegfluss_eval.dataset import official, synthetic, variants
from belegfluss_eval.paths import DATASET_FILES, DATASET_NAME, EXTERNAL, MANIFEST

GENERATOR = "eval-dataset-v1 (built 2026-11-25)"
SEED = 20261125
SYNTHETIC_COUNT = 80
VARIANTS_PER_SOURCE = 20  # per source (official, synthetic): half photos, half scans
DEV_SHARE = 0.4
ZIP_DATE = (2026, 11, 25, 0, 0, 0)


@dataclass(frozen=True)
class Original:
    doc_id: str
    source: str  # "official" | "synthetic"
    origin: str
    layout: str
    labels: InvoiceModel
    path: Path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pages(path: Path) -> int:
    if path.suffix == ".jpg":
        return 1
    document = pdfium.PdfDocument(path.read_bytes())
    try:
        return len(document)
    finally:
        document.close()


def _originals() -> list[Original]:
    work = EXTERNAL / "eval-build"
    items = official.prepare_all()
    pdfs = official.render(items, work / "official")
    result = []
    for item in items:
        target = DATASET_FILES / "official" / f"{item.doc_id}.pdf"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(pdfs[item.doc_id], target)
        result.append(
            Original(item.doc_id, "official", item.origin, item.layout, item.labels, target)
        )
    generated = synthetic.generate(SYNTHETIC_COUNT)
    rendered = synthetic.render(generated, DATASET_FILES / "synthetic")
    for doc in generated:
        result.append(
            Original(
                doc.doc_id,
                "synthetic",
                f"{doc.template}/{doc.case}",
                doc.template,
                doc.labels,
                rendered[doc.doc_id],
            )
        )
    return result


def build() -> manifest.Manifest:
    if DATASET_FILES.exists():
        shutil.rmtree(DATASET_FILES)
    originals = _originals()
    rng = random.Random(SEED)  # noqa: S311 (test data, not security)

    ids = [o.doc_id for o in originals]
    rng.shuffle(ids)
    dev = set(ids[: round(len(ids) * DEV_SHARE)])

    def entry(o: Original, path: Path, variant: str, media_type: str) -> manifest.Document:
        return manifest.Document(
            id=o.doc_id if variant == "original" else f"{o.doc_id}-{variant}",
            source="official" if o.source == "official" else "synthetic",
            origin=o.origin,
            layout=o.layout,
            variant="original"
            if variant == "original"
            else ("photo" if variant == "photo" else "scan"),
            split="dev" if o.doc_id in dev else "test",
            media_type=media_type,
            file=path.relative_to(DATASET_FILES).as_posix(),
            pages=_pages(path),
            sha256=_sha256(path),
            labels=o.labels,
        )

    documents = [entry(o, o.path, "original", "application/pdf") for o in originals]
    folder = DATASET_FILES / "variants"
    folder.mkdir(parents=True, exist_ok=True)
    for source in ("official", "synthetic"):
        # Only page 1 is photographed or scanned. The official view has every export field on page 1
        # (details follow); a synthetic invoice must fit on one page.
        candidates = [
            o for o in originals
            if o.source == source and (source == "official" or _pages(o.path) == 1)
        ]  # fmt: skip
        for index, o in enumerate(rng.sample(candidates, VARIANTS_PER_SOURCE)):
            seed = SEED + int(hashlib.sha256(o.doc_id.encode()).hexdigest()[:8], 16)
            pdf = o.path.read_bytes()
            if index % 2 == 0:
                path = folder / f"{o.doc_id}-photo.jpg"
                path.write_bytes(variants.photo(pdf, seed))
                documents.append(entry(o, path, "photo", "image/jpeg"))
            else:
                path = folder / f"{o.doc_id}-scan.pdf"
                path.write_bytes(variants.scan(pdf, seed))
                documents.append(entry(o, path, "scan", "application/pdf"))

    data = manifest.Manifest(name=DATASET_NAME, generator=GENERATOR, documents=documents)
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    manifest.save(data, MANIFEST)
    return data


def package() -> Path:
    """ZIP of the files in a fixed order with a fixed date, for the release asset."""
    target = EXTERNAL / f"{DATASET_NAME}.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(DATASET_FILES.rglob("*")):
            if path.is_file():
                info = zipfile.ZipInfo(path.relative_to(DATASET_FILES).as_posix(), ZIP_DATE)
                archive.writestr(info, path.read_bytes(), zipfile.ZIP_DEFLATED)
    return target


def verify(data: manifest.Manifest) -> list[str]:
    """Files that are missing or differ from the manifest."""
    problems = []
    for doc in data.documents:
        path = DATASET_FILES / doc.file
        if not path.exists():
            problems.append(f"missing {doc.file}")
        elif _sha256(path) != doc.sha256:
            problems.append(f"checksum differs: {doc.file}")
    return problems


def fetch() -> list[str]:
    """Download the release asset with the GitHub CLI, unpack it and check every file."""
    # The GitHub CLI from PATH, as a developer runs it; CI provides it too.
    command = ["gh", "release", "download", DATASET_NAME, "--pattern", f"{DATASET_NAME}.zip"]
    command += ["--dir", str(EXTERNAL), "--clobber"]
    subprocess.run(command, check=True)  # noqa: S603 (fixed command)
    if DATASET_FILES.exists():
        shutil.rmtree(DATASET_FILES)
    with zipfile.ZipFile(EXTERNAL / f"{DATASET_NAME}.zip") as archive:
        archive.extractall(DATASET_FILES)
    return verify(manifest.load(MANIFEST))
