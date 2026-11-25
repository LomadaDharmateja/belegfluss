"""The labelled set: one entry per document with its split, checksum and exact labels.

The manifest is committed; the rendered files are not (they are a release asset, ADR-0018). The
dataset version is the SHA-256 of the manifest file: any change to a label or a file changes it.
"""

import hashlib
from pathlib import Path
from typing import Literal

from belegfluss.reading import InvoiceModel
from pydantic import BaseModel

Split = Literal["dev", "test"]


class Document(BaseModel):
    id: str
    source: Literal["official", "synthetic"]
    origin: str  # suite file name or generator id
    layout: str  # official line layout or synthetic template
    variant: Literal["original", "photo", "scan"]
    split: Split
    media_type: str
    file: str  # path inside the dataset folder
    pages: int
    sha256: str
    labels: InvoiceModel


class Manifest(BaseModel):
    name: str
    generator: str  # generator version: bump when rendering or labelling changes
    documents: list[Document]

    def split(self, split: Split) -> list[Document]:
        return [d for d in self.documents if d.split == split]


def load(path: Path) -> Manifest:
    return Manifest.model_validate_json(path.read_bytes())


def save(manifest: Manifest, path: Path) -> None:
    path.write_text(manifest.model_dump_json(indent=1) + "\n", encoding="utf-8", newline="\n")


def version(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
