# Third-party components and data

Belegfluss uses official tools and openly licensed packages instead of re-implementing standards
([ADR-0008](decisions/0008-test-data-sourcing-and-licensing.md)). This file lists what is **vendored** (copied into
this repository), **run** as a container, or **downloaded** for tests. Ordinary package dependencies are listed in
`apps/api/pyproject.toml` and `apps/web/package.json` with their lockfiles.

## Vendored in this repository

| Component | Where | Version | Licence | Notes |
|---|---|---|---|---|
| KoSIT XRechnung visualisation, step-1 XSLT (UBL/CII → semantic model) | `apps/api/src/belegfluss/reading/xslt/` | release `v2026-10-13` | Apache-2.0 (`LICENSE` in that folder; the project has no NOTICE file) | Unchanged; source and checksum in `SOURCE.md` there ([ADR-0014](decisions/0014-read-xml-with-official-kosit-transform.md)) |

## Run as a container (downloaded at image build, pinned by SHA-256)

| Component | Where | Version | Licence |
|---|---|---|---|
| KoSIT validator | `services/validator/Dockerfile` | 1.6.3 | Apache-2.0 ([repository](https://github.com/itplr-kosit/validator)) |
| XRechnung validator configuration | `services/validator/Dockerfile` | 2026-08-31 (XRechnung 3.0.2) | Apache-2.0 ([repository](https://github.com/itplr-kosit/validator-configuration-xrechnung)) |

## Notable runtime libraries

| Package | Used for | Licence |
|---|---|---|
| [saxonche](https://pypi.org/project/saxonche/) (SaxonC-HE 13.1) | Running the KoSIT XSLT | MPL-2.0 ([Saxonica](https://www.saxonica.com/html/saxon-c/index.html)); used unmodified |
| [lxml](https://pypi.org/project/lxml/) | Parsing untrusted XML safely | BSD-3-Clause |
| [pypdf](https://pypi.org/project/pypdf/) | Extracting the XML embedded in ZUGFeRD PDFs | BSD-3-Clause |
| [pypdfium2](https://pypi.org/project/pypdfium2/) (PDFium) | Reading the text layer of PDFs; rendering pages for AI reading | Apache-2.0 / BSD-3-Clause (PDFium: BSD-3-Clause) |
| [azure-storage-queue](https://pypi.org/project/azure-storage-queue/), [azure-storage-blob](https://pypi.org/project/azure-storage-blob/) | Queue and originals | MIT |
| [openai](https://pypi.org/project/openai/) | Calling Azure OpenAI (v1 API, structured outputs) | Apache-2.0 |
| [azure-identity](https://pypi.org/project/azure-identity/) | Keyless sign-in to Azure OpenAI (Azure CLI locally, Managed Identity in M4) | MIT |
| [Pillow](https://pypi.org/project/pillow/) | Turning photos upright, shrinking them and dropping their metadata | MIT-CMU |

Development only: [factur-x](https://pypi.org/project/factur-x/) (BSD) generates our own ZUGFeRD/Factur-X test PDFs.

## Test data (downloaded, never committed)

| Data | How | Licence |
|---|---|---|
| KoSIT XRechnung test suite 2026-08-31 (86 files) | `python scripts/fetch_test_data.py` → `testdata/external/` (git-ignored), SHA-256 checked | Apache-2.0 ([repository](https://github.com/itplr-kosit/xrechnung-testsuite)) |

Our own fixtures in `apps/api/tests/fixtures/` are synthetic: fictional companies, written for Belegfluss.
