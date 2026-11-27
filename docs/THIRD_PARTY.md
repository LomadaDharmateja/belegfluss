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

## Evaluation only (`eval/`, never in the app)

| Component | Used for | Licence |
|---|---|---|
| KoSIT XRechnung visualisation `xr-pdf.xsl` (v2026-10-13, fetched into `testdata/external/`, not vendored) | Rendering the official test files as the official PDF view | Apache-2.0 |
| [Apache FOP](https://xmlgraphics.apache.org/fop/) 2.12 (container `eval/fop/Dockerfile`, SHA-512 pinned) | XSL-FO → PDF for the official view | Apache-2.0 |
| [Playwright for Python](https://pypi.org/project/playwright/) (Chromium) | Printing the synthetic HTML invoices to PDF | Apache-2.0 |
| [Jinja2](https://pypi.org/project/Jinja2/) | Synthetic invoice templates | BSD-3-Clause |
| [Faker](https://pypi.org/project/Faker/) | Fictional names and addresses for synthetic invoices | MIT |
| [azure-ai-documentintelligence](https://pypi.org/project/azure-ai-documentintelligence/) | The Document Intelligence baseline | MIT |

The rendered evaluation set (`eval-dataset-v1.zip`) is a release asset of this repository (public since M4b). It
contains renders of the official KoSIT XRechnung test suite and visualisation (Apache-2.0, © KoSIT, attribution and
licence link in the release notes) and our own synthetic documents (fictional data, MIT like the rest).

## Notable runtime libraries

| Package | Used for | Licence |
|---|---|---|
| [saxonche](https://pypi.org/project/saxonche/) (SaxonC-HE 13.1) | Running the KoSIT XSLT | MPL-2.0 ([Saxonica](https://www.saxonica.com/html/saxon-c/index.html)); used unmodified |
| [lxml](https://pypi.org/project/lxml/) | Parsing untrusted XML safely | BSD-3-Clause |
| [pypdf](https://pypi.org/project/pypdf/) | Extracting the XML embedded in ZUGFeRD PDFs | BSD-3-Clause |
| [pypdfium2](https://pypi.org/project/pypdfium2/) (PDFium) | Reading the text layer of PDFs; rendering pages for AI reading | Apache-2.0 / BSD-3-Clause (PDFium: BSD-3-Clause) |
| [azure-storage-queue](https://pypi.org/project/azure-storage-queue/), [azure-storage-blob](https://pypi.org/project/azure-storage-blob/) | Queue and originals | MIT |
| [openai](https://pypi.org/project/openai/) | Calling Azure OpenAI (v1 API, structured outputs) | Apache-2.0 |
| [azure-identity](https://pypi.org/project/azure-identity/) | Keyless sign-in to Azure (Azure CLI locally, Managed Identity in Azure) | MIT |
| [Pillow](https://pypi.org/project/pillow/) | Turning photos upright, shrinking them and dropping their metadata | MIT-CMU |

Development only: [factur-x](https://pypi.org/project/factur-x/) (BSD) generates our own ZUGFeRD/Factur-X test PDFs.

## Build, infrastructure and CI tools (not part of the app)

| Tool | Used for | Licence |
|---|---|---|
| [Terraform](https://github.com/hashicorp/terraform) 1.17 | Creating the Azure resources (`infra/`) | BUSL-1.1 (use for our own infrastructure is permitted) |
| [Terraform provider azurerm](https://github.com/hashicorp/terraform-provider-azurerm) 5.15 | Azure resources in Terraform | MPL-2.0 |
| [tflint](https://github.com/terraform-linters/tflint) and its [azurerm ruleset](https://github.com/terraform-linters/tflint-ruleset-azurerm) | Linting the Terraform code (CI) | MPL-2.0 |
| [Trivy](https://github.com/aquasecurity/trivy) | Scanning images and Terraform configuration, SBOMs (CI) | Apache-2.0 |
| [gitleaks](https://github.com/gitleaks/gitleaks) | Secret scanning (CI) | MIT |
| Container base images: [python](https://hub.docker.com/_/python), [node](https://hub.docker.com/_/node), [eclipse-temurin](https://hub.docker.com/_/eclipse-temurin), [alpine](https://hub.docker.com/_/alpine) | Runtime images (pinned by digest) | their own licences (PSF and Debian packages; MIT; GPL-2.0 with Classpath Exception; MIT and Alpine packages) |

## Test data (downloaded, never committed)

| Data | How | Licence |
|---|---|---|
| KoSIT XRechnung test suite 2026-08-31 (86 files) | `python scripts/fetch_test_data.py` → `testdata/external/` (git-ignored), SHA-256 checked | Apache-2.0 ([repository](https://github.com/itplr-kosit/xrechnung-testsuite)) |

Our own fixtures in `apps/api/tests/fixtures/` are synthetic: fictional companies, written for Belegfluss.
