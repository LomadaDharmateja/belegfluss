"""Download pinned official test data into testdata/external/ (git-ignored), checked by SHA-256.

Usage:  python scripts/fetch_test_data.py

Only official, openly licensed releases are listed here (ADR-0008). Each archive is unpacked into its own folder.
Running the script again skips anything that is already in place.
"""

import hashlib
import sys
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "testdata" / "external"


@dataclass(frozen=True)
class Asset:
    folder: str  # unpacked into testdata/external/<folder>
    url: str
    sha256: str
    licence: str


ASSETS = [
    Asset(
        folder="xrechnung-testsuite-2026-08-31",
        url=(
            "https://github.com/itplr-kosit/xrechnung-testsuite/releases/download/v2026-08-31/"
            "xrechnung-3.0.2-testsuite-2026-08-31.zip"
        ),
        sha256="1e81ef7563e0fa04c0e0b0631318a7e0843a3c0beb57d83ef95ac0c4a095e3d7",
        licence="Apache-2.0",
    ),
]


def fetch(asset: Asset) -> None:
    folder = TARGET / asset.folder
    marker = folder / ".sha256"
    if marker.exists() and marker.read_text(encoding="utf-8").strip() == asset.sha256:
        print(f"ok      {asset.folder} (already present)")
        return

    print(f"fetch   {asset.url}")
    with urllib.request.urlopen(asset.url, timeout=120) as response:  # noqa: S310 (pinned https URL)
        data = response.read()
    digest = hashlib.sha256(data).hexdigest()
    if digest != asset.sha256:
        sys.exit(f"checksum mismatch for {asset.url}: expected {asset.sha256}, got {digest}")

    archive = TARGET / f"{asset.folder}.zip"
    archive.write_bytes(data)
    with zipfile.ZipFile(archive) as zf:
        unsafe = [n for n in zf.namelist() if n.startswith(("/", "\\")) or ".." in Path(n).parts]
        if unsafe:
            sys.exit(f"refusing archive with unsafe paths: {unsafe[:3]}")
        zf.extractall(folder)
    archive.unlink()
    marker.write_text(asset.sha256, encoding="utf-8")
    print(f"ok      {asset.folder} ({len(data):,} bytes, {asset.licence})")


def main() -> None:
    TARGET.mkdir(parents=True, exist_ok=True)
    for asset in ASSETS:
        fetch(asset)


if __name__ == "__main__":
    main()
