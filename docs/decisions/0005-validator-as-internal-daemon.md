# ADR-0005: Run the official KoSIT validator in daemon mode as an internal-only container

- **Status:** Accepted (2026-11-23)
- **Date:** 2026-11-23
- **Milestone:** M0 (implemented in M2)

## Context

We want official validation results for XRechnung and EN 16931 invoices, not our own re-implementation of the
rules. The official tool is the KoSIT validator (Java, Apache-2.0) with the official XRechnung configuration
(Apache-2.0). Our services are Python.

Verified in M0 (documentation + smoke test, see [einvoicing.md §4](../research/einvoicing.md#4-validation-tooling)
and the [evidence log](../research/evidence/validator-smoke-2026-11-23.txt)):
- v1.6.3 (2026-08-20), Java ≥ 11; ran on `eclipse-temurin:21-jre`.
- Daemon mode `-D -H -P [-T threads] [-G no GUI]`: POST raw XML → **200 acceptable, 406 not acceptable, 422
  processing error**; `/server/health` returns `UP`.
- **The daemon has no authentication.** Securing access is the operator's job.
- The official configuration (2026-08-31) also has **plain EN 16931 scenarios** (UBL and CII): a non-XRechnung
  EN 16931 invoice was accepted with EN rules only.
- The report contains `rep:message` elements with `code`, `level` (error/warning/information) and `xpathLocation`,
  and `rep:assessment` with `accept` or `reject`.
- The default JVM heap in a container was ~1.9 GB, so it must be capped.

## Options

- **A. Daemon in its own container, reached over an internal network:** official tool unchanged, warm JVM,
  language-neutral HTTP, scales separately. Needs an extra container and must never be public.
- **B. CLI subprocess per file from the Python worker:** simplest code, but a JVM start-up per file and Java inside
  the Python image.
- **C. Embed in Python (JPype/Py4J):** fast, but complex and fragile.
- **D. Run the Schematron from Python (e.g. Saxon for Python):** no Java, but we would rebuild scenario selection and
  reports, so it is no longer the official validator.

## Decision

**Option A.**
- `services/validator/` contains a Dockerfile (Temurin JRE + pinned validator jar + pinned official configuration,
  SHA-256 checked) and no own code.
- Start with `-D -G -H 0.0.0.0`, and set `-Xmx` (sized in M2 by measuring).
- **Network:** Compose — not published to the host in CI. Container Apps — internal ingress only. AKS — ClusterIP +
  NetworkPolicy allowing only the worker.
- **Python client** (`httpx`): POST bytes with `Content-Type: application/xml`. Map 200 → accepted, 406 →
  rejected, 422 → processing error (our bug or broken file), anything else → retry. Parse `rep:message` into our
  `Finding` model (code, severity, location).
- **Versions side by side:** the image tag includes the configuration version (e.g.
  `validator:1.6.3-xr3.0.2-2026-08-31`). When XRechnung 4.0 is final (expected spring 2027), we run it next to 3.0
  and route by the document's CustomizationID.
- Every stored validation result records the validator and configuration version.

## Consequences

- Validation results are as official as they can be, and we can say exactly which version produced them.
- One more container. It needs memory and a health check, and a cold start when scaled to zero (measure in M4).
- ZUGFeRD-specific checks (profile Schematron, PDF/A-3) are not covered. See the M2 spike in
  [einvoicing.md §4.5](../research/einvoicing.md#45-what-the-kosit-validator-does-not-cover-zugferd).
- The validator's findings are hints for the user, not a legal verdict (F16).

## Sources

- https://github.com/itplr-kosit/validator (README, docs/cli.md, docs/daemon.md, releases, LICENSE)
- https://github.com/itplr-kosit/validator-configuration-xrechnung (releases, scenarios.xml, LICENSE)
