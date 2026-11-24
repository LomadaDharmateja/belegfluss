# E-invoicing in Germany — verified research (M0)

> **Read on:** 2026-11-23 · **Method:** official sources only (law texts, BMF, KoSIT, FeRD/FNFE-MPE, European
> Commission/CEN, DATEV, Microsoft), plus one hands-on run of the official validator.
> **This is engineering research, not legal or tax advice.**
> Every fact has an ID (F1, F2, …) that is used in the [verified facts table](#8-verified-facts) and in the ADRs.

## 1. Summary

1. Since **1 Jan 2025** every business in Germany must be able to **receive** e-invoices. An email inbox is
   enough. Receiving has no exceptions, and that includes Kleinunternehmer (F6, F7).
2. **Issuing** e-invoices (domestic B2B) phases in. Until 31 Dec 2026 anyone may still send paper, or PDF if the
   recipient agrees. In 2027 that only applies to issuers with prior-year turnover ≤ €800,000. From
   **1 Jan 2028** e-invoices are mandatory for everyone not exempt (F8–F10).
3. Exempt from *issuing* (they may always send a "sonstige Rechnung"): invoices ≤ €250 gross, travel tickets,
   Kleinunternehmer, and supplies to non-business legal entities (F11–F14).
4. An e-invoice is a **structured** format that allows electronic processing. In practice that means EN 16931.
   **XRechnung** and **ZUGFeRD ≥ 2.0.1** qualify, except the profiles **MINIMUM** and **BASIC-WL**. A plain PDF is
   *not* an e-invoice (F1–F4).
5. In hybrid invoices (ZUGFeRD), the **XML is the leading part**. If PDF and XML disagree, the XML counts (F15).
6. Validation is **not a legal prerequisite** for input-VAT deduction, but the BMF calls it sensible (F16).
7. E-invoices must be kept **8 years**, at least the structured part **unaltered in its original form** (F18, F19).
8. The official **KoSIT validator** (Apache-2.0, Java) validates XRechnung *and* plain EN 16931 invoices in UBL and
   CII. We **ran it**: CLI and HTTP daemon both work as documented (F30–F38, [evidence log](evidence/validator-smoke-2026-11-23.txt)).
9. Official XRechnung test data (KoSIT test suite, Apache-2.0) is free to use. **FeRD's ZUGFeRD sample invoices
   have no redistribution licence**, so they must not be committed (F40–F44).
10. **Competition:** a free official viewer exists (ELSTER), and DATEV Unternehmen online already receives and
    processes e-invoices. "Making XML readable" alone is not a product (F17, F49). See [§7](#7-implications-for-belegfluss).

## 2. The rules

### 2.1 What counts as an e-invoice

- **Definition (§ 14 Abs. 1 S. 3 UStG):** an invoice "issued, transmitted and received in a structured electronic
  format" that "enables electronic processing". Everything else (paper, plain PDF, image) is a
  **"sonstige Rechnung"** (S. 4) (F1).
- **Allowed formats (§ 14 Abs. 1 S. 6 UStG):** (1) the European standard on e-invoicing and its list of syntaxes
  under Directive 2014/55/EU (that is EN 16931), or (2) a format agreed between issuer and recipient, if the
  required data can be correctly extracted into an EN 16931-conformant or interoperable format (e.g. EDI) (F2).
- **BMF view:** XRechnung and ZUGFeRD from version 2.0.1 qualify, **except the profiles MINIMUM and BASIC-WL**
  (BMF FAQ Q7) (F3).
- **All mandatory invoice fields must be in the structured part.** A reference in the XML to an unstructured
  attachment that holds the mandatory data is not enough. Extra details (e.g. timesheets as an embedded PDF) are
  fine (BMF FAQ Q7a) (F4).
- **Mandatory fields (§ 14 Abs. 4 UStG):** names and addresses of both parties; tax number or VAT ID; issue date;
  unique sequential invoice number; quantity and description of goods/services; date of supply; net amount by tax
  rate; tax rate and tax amount (or exemption note); special notes in some cases ("Gutschrift", retention note) (F5).
  KoSIT and FeRD publish an official **mapping table "Pflichtangaben → BT fields"**, which the BMF recommends using
  (BMF FAQ Q16) (F29).

### 2.2 Who is affected

- **Domestic B2B only:** the obligation applies when **both supplier and recipient are established in Germany**
  (§ 14 Abs. 2 S. 2 Nr. 1 UStG) (F6). "Established" means registered office, management, or a permanent
  establishment involved in the supply, otherwise residence (BMF FAQ Q3).
- **Freelancers, landlords, doctors and Kleinunternehmer are "Unternehmer"** and must be able to receive
  (BMF FAQ Q3, Q12) (F7).
- **Not affected:** B2C, and many tax-exempt supplies under § 4 Nr. 8–29 UStG (finance, property letting),
  because no invoice obligation exists (BMF FAQ Q4).
- **Vereine (associations):** affected only for their business (unternehmerisch) activities (BMF FAQ Q5).
- **B2G (public sector)** is governed separately (E-Rechnungsverordnung, Leitweg-ID). No Leitweg-ID is needed for
  B2B. A placeholder such as "-" in BT-10 is enough for tax purposes (BMF FAQ Q4a, Q6).
- **Foreign suppliers** without a German establishment are outside the obligation. They may state this on the
  invoice (BMF FAQ Q3). → *Invoices from AWS, Google, Adobe etc. will keep arriving as PDFs.*

### 2.3 Receiving (since 1 Jan 2025)

- Every domestic business must be able to receive e-invoices. **No exceptions** (BMF FAQ Q12) (F7).
- **An email inbox is sufficient.** The law prescribes **no transmission channel**: email, API, portal download and
  USB stick are all possible, and the channel is a civil-law matter between the parties (BMF FAQ Q8) (F20).
- The recipient is **not obliged to actually process** the data electronically beyond what archiving requires
  (BMF FAQ Q9).

### 2.4 Issuing: transition periods

| Period | Who may still issue a "sonstige Rechnung" instead of an e-invoice | Source |
|---|---|---|
| 1 Jan 2025 – 31 Dec 2026 | Everyone. Paper always; other electronic formats (PDF) only with recipient's consent | § 27 Abs. 38 Nr. 1 UStG (F8) |
| 1 Jan 2027 – 31 Dec 2027 | Only issuers with **prior-year total turnover ≤ €800,000** | § 27 Abs. 38 Nr. 2 UStG (F9) |
| until 31 Dec 2027 | EDI procedures that are not EN 16931-interoperable, with consent | § 27 Abs. 38 Nr. 3 UStG |
| from 1 Jan 2028 | Nobody (unless exempt, §2.5) | BMF FAQ Q11 (F10) |

- Not issuing an e-invoice when required is **not an administrative offence** under the current § 26a UStG. The
  recipient has a civil-law claim to receive one (BMF FAQ Q12c).
- **Input VAT risk is on the recipient side.** If an e-invoice was required and a sonstige Rechnung was sent, it is
  not a proper invoice. Input VAT may still be possible via a later corrective e-invoice or the
  "Objektivnachweis". It is also not objected to if the recipient could reasonably assume the issuer used a
  transition rule (BMF FAQ Q12b).
  → **Product implication:** from 2027/2028 Belegfluss can flag "this supplier probably should have sent an
  e-invoice". This is an advisory hint only, never a tax verdict.

### 2.5 Exceptions from *issuing* (receiving still required)

| Case | Rule | Source |
|---|---|---|
| Small-amount invoices **≤ €250 gross** | May always be sent as sonstige Rechnung | § 33 S. 4 UStDV (F11) |
| Travel tickets (Fahrausweise) | May always be sent as sonstige Rechnung | § 34 Abs. 1 UStDV (F12) |
| **Kleinunternehmer** (§ 19 UStG: ≤ €25,000 prior year and ≤ €100,000 current year) | May always be sent as sonstige Rechnung. If they switch to regular taxation, they must issue e-invoices | § 34a UStDV, § 19 Abs. 1 UStG, BMF FAQ Q4 (F13) |
| Supplies to legal entities that are not businesses (many Vereine, public bodies) | Sonstige Rechnung allowed | BMF FAQ Q4/Q5 (F14) |
| Cash purchases | **No exception**: > €250 needs an e-invoice (after transition) | BMF FAQ Q10 |

### 2.6 Hybrid invoices: the XML is leading

Before 2025 the visual PDF part of a ZUGFeRD invoice took precedence. **Since the e-invoice mandate the structured
(XML) part is leading.** If the two differ, the XML data counts. The BMF therefore recommends visualising the XML
itself instead of trusting the PDF image (BMF FAQ Q12a) (F15). FeRD says the same: only the structured XML part
entitles to input-VAT deduction ([FeRD 2.4 news](https://www.ferd-net.de/aktuelles-veranstaltungen/aktuelles/news/neue-zugferd-version-24-veroeffentlicht-1)).
→ **Product implication:** Belegfluss must show the XML data, and should run a **PDF-vs-XML consistency check**
(a strong, unique feature: "the PDF says €1,190, the legally relevant XML says €1,109").

### 2.7 Validation and input VAT

- Validation against EN 16931 format rules and business rules is **not a direct prerequisite** for tax recognition
  (e.g. input VAT). The BMF calls it "sensible", recommends doing it when issuing, and **does not recommend any
  specific validator** (BMF FAQ Q7) (F16).
- → **Product implication:** validator findings must be worded as *"problems found / please check"*, never as
  *"this invoice is legally invalid"*. That matters for the plain-language explanations and for liability.

### 2.8 Visualisation

- XRechnung has no built-in human-readable view, so a viewer is needed. "Many free offers" exist (BMF FAQ Q12a).
- The **tax administration offers a free e-invoice viewer via ELSTER**: `www.e-rechnung.elster.de` (BMF FAQ Q12a) (F17).
- KoSIT publishes an open-source visualisation (XSLT → HTML/PDF), see §4.6.

### 2.9 Archiving

- Invoices must be kept **8 years** (§ 14b Abs. 1 UStG). Booking vouchers likewise 8 years (§ 147 Abs. 3 AO).
  The period starts at the end of the calendar year of issue (F18).
- For an e-invoice, **at least the structured part must be stored unaltered in its original form**. Storing it
  outside a GoBD-compliant system is, for VAT purposes, regularly not a breach of § 14b (BMF FAQ Q13) (F19).
- → **Product implication:** Belegfluss keeps the original bytes immutable (content hash). But Belegfluss is **not
  a GoBD archive**, and our deletion feature (GDPR) conflicts with the user's 8-year duty. So: tell users clearly
  that they must keep their originals; offer "export everything" before deletion. See ARCHITECTURE §Security.

### 2.10 Special cases with deadlines (from BMF FAQ Q7b, based on the letters of 2024–2026)

- **Gross-price invoices:** until 31 Dec 2027 it is tolerated if the XML has only totals per tax rate and the
  line items are in a human-readable attachment (rounding issue in EN 16931).
- **Final invoices after down payments:** until 30 Jun 2030 deductions may be given as a sum in BT-113 "Paid
  amount" with details in BT-22, or in an attachment.
- **Public-law fee notices** (Gebührenbescheide) issued until 30 Jun 2030 may be sonstige Rechnungen.
- **Corrections** must be e-invoices if the original had to be one. Which invoice type code (BT-3) to use for
  which correction is not yet technically settled.
- **Collective invoices** (calendar month as supply period) are allowed.

### 2.11 What's coming

- **Three BMF letters** form the administrative view: 15 Oct 2024, 15 Oct 2025 ("Anpassung des UStAE") and
  **15 Oct 2026 ("Ergänzende Regelungen")** (BMF FAQ intro; BMF letter pages) (F21). *We read the official FAQ
  (as of 29 Oct 2026) and the letter landing pages. The letter PDFs could not be read in this session, see Open
  Questions.*
- **Transaction reporting system (Meldesystem):** planned for later. Legislation will be proposed "in due course",
  and today's rules may be adjusted for it (BMF FAQ Q1) (F22).
- **EU ViDA:** Digital Reporting Requirements for **cross-border** B2B from **1 Jul 2030**. Member States may require
  domestic e-invoicing without an EU derogation ([European Commission ViDA page](https://taxation-customs.ec.europa.eu/taxation/vat/vat-digital-age-vida_en),
  [Directive (EU) 2025/516](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32025L0516)) (F23, *caveat:
  read via search summary, the EUR-Lex text did not load*).
- **EN 16931-1:2026** was published in May 2026. The 2017 version is formally withdrawn but stays compliant during
  migration (F24). **XRechnung 4.0** (based on it) was published as a pre-release on 15 Sep 2026, **not for
  productive use**, and is expected final in **spring 2027**. XRechnung 3.0 stays in force until at least
  31 Jul 2027 (F26, F27).
  → **Architecture implication:** support **multiple validator configurations side by side** (3.0 now, 4.0 later),
  selected by the document's CustomizationID.

## 3. Formats

### 3.1 EN 16931 (European standard)

- Defines the **semantic data model** (business terms "BT-n", groups "BG-n") and the list of allowed syntaxes.
- Parts 1 (semantic model) and 2 (syntax list, CEN/TS 16931-2) are **free of charge** through an agreement between
  the Commission and CEN. Parts 3-x (syntax bindings for UBL 2.1, UN/CEFACT CII D16B, EDIFACT), 4, 5 and 6 are
  sold by national standards bodies (F24, [EC: obtaining the standard](https://ec.europa.eu/digital-building-blocks/sites/spaces/DIGITAL/pages/467108971/Obtaining+a+copy+of+the+European+standard+on+eInvoicing)).
- The two mandatory syntaxes are **UBL 2.1** and **UN/CEFACT CII** ([xeinkauf.de](https://xeinkauf.de/xrechnung/)) (F25).

### 3.2 XRechnung

- Germany's **CIUS** (Core Invoice Usage Specification) of EN 16931, plus an **Extension**, developed by KoSIT. A
  CIUS restricts and tightens the standard (extra rules "BR-DE-*"). The Extension adds elements (F25).
- Syntaxes: **UBL 2.1 Invoice, UBL 2.1 CreditNote, UN/CEFACT CII D16B** ([validator config README](https://github.com/itplr-kosit/validator-configuration-xrechnung)).
- **Current version 3.0** (in force since 1 Feb 2024, at least until 31 Jul 2027). Latest technical bundle
  **3.0.2 "Summer 2026 Bugfix" (31 Aug 2026)**. Latest visualisation release 13 Oct 2026
  ([versions and bundles](https://xeinkauf.de/xrechnung/versionen-und-bundles/)) (F26).
- **4.0:** pre-release 15 Sep 2026, not for production, final expected spring 2027
  ([xeinkauf.de version 4](https://xeinkauf.de/xrechnung/version-4)) (F27). Which UBL/CII versions it uses is
  *unverified* (see Open Questions).
- Identifier seen in the official test files: `cbc:CustomizationID` =
  `urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0` (observed, test suite 2026-08-31).

### 3.3 ZUGFeRD / Factur-X

- A **hybrid** format: a PDF/A-3 document with embedded **CII** XML. Developed by FeRD (part of AWV e.V.) and
  technically identical to the French Factur-X (FNFE-MPE) (F28).
- **Current version: ZUGFeRD 2.5.2 = Factur-X 1.09.2**, published 4 Aug 2026, effective 1 Sep 2026, fully backward
  compatible. Based on **CII D22B**, backward compatible with D16B. FeRD expected the next release in autumn 2026
  ([FeRD 2.5.2](https://www.ferd-net.de/publikationen-produkte/publikationen/detailseite/zugferd-252-english)) (F28).
- **Profiles:** MINIMUM, BASIC WL, BASIC, EN 16931 (formerly "COMFORT"), EXTENDED, plus XRECHNUNG as a reference
  profile ([FNFE Factur-X](https://fnfe-mpe.org/factur-x/), [FeRD](https://www.ferd-net.de/standards/zugferd)).
- **Which profiles are e-invoices under German VAT law:** all except **MINIMUM and BASIC-WL** (F3). MINIMUM and
  BASIC-WL do not carry line items, so they cannot hold all mandatory data in the structured part (consistent with
  F4).
- → **Product implication:** a ZUGFeRD MINIMUM/BASIC-WL file *looks* like an e-invoice but legally is a sonstige
  Rechnung. This is a valuable, explainable finding ("Your supplier's file is not a valid e-invoice because…").

### 3.4 Recognising the format of an incoming file (design input for M2)

| Input | How to recognise | Structured data? |
|---|---|---|
| UBL Invoice / CreditNote XML | root `Invoice` / `CreditNote` in UBL namespace; `cbc:CustomizationID` | yes |
| CII XML | root `rsm:CrossIndustryInvoice`; `ram:GuidelineSpecifiedDocumentContextParameter/ram:ID` | yes |
| PDF with embedded XML (ZUGFeRD / Factur-X) | PDF/A-3 attachment (CII XML); profile from the guideline ID | yes (XML is leading) |
| Plain PDF, scan, photo | no embedded XML | no → LLM extraction |

The scenario selectors in the official KoSIT configuration confirm these identifiers: XRechnung UBL/CII and plain
EN 16931 (`urn:cen.eu:en16931:2017`) each have their own scenario
([scenarios.xml](https://github.com/itplr-kosit/validator-configuration-xrechnung/blob/master/scenarios.xml)).
*The exact ZUGFeRD profile IDs and the normative attachment file name (`factur-x.xml` vs. others) were not verified
in this session.* They come from the FeRD specification in M2.

## 4. Validation tooling

### 4.1 KoSIT validator — facts

| Item | Fact | Source |
|---|---|---|
| Project | `itplr-kosit/validator`, generic XML validator (XSD + Schematron) driven by "scenarios" | [GitHub](https://github.com/itplr-kosit/validator) |
| Licence | **Apache-2.0** | [LICENSE](https://github.com/itplr-kosit/validator/blob/main/LICENSE) (F30) |
| Latest release | **v1.6.3, 2026-08-20** (security fix GHSA-hg2c-p2m3-q29m) | [releases](https://github.com/itplr-kosit/validator/releases) (F31) |
| Runtime | Java ≥ 11. v1.6.0 notes: runs up to Java 25 | README, release notes (F32) |
| Modes | CLI, Java library, **daemon with HTTP interface** | [README](https://github.com/itplr-kosit/validator) (F33) |
| CLI | `java -jar validator-1.6.3-standalone.jar -s scenarios.xml -r <repo> [-o outdir] [-h] files…`; exit code 0 = all acceptable, n = number rejected, -1 args error, -2 config error | [cli.md](https://github.com/itplr-kosit/validator/blob/main/docs/cli.md), `--help` (F34) |
| Daemon | `-D -H <host> -P <port> [-T threads] [-G no GUI]`; POST raw XML (`application/xml`, **no multipart**) to any path; **200 = acceptable, 406 = not acceptable, 422 = processing error**, 400/405/500; health at `/server/health` | [daemon.md](https://github.com/itplr-kosit/validator/blob/main/docs/daemon.md) (F35) |
| Security | **No authentication**: "the user is responsible to secure access". The built-in GUI is for showcasing only. Based on the JDK HTTP server | daemon.md (F36) |
| Docker | No official image documented | (F37) |
| Report | XML `rep:report` (ns `http://www.xoev.de/de/validator/varl/1`) with `rep:scenarioMatched`, `rep:validationStepResult` (xml, xsd, schematron steps) containing `rep:message` (`code`, `level` = error/warning/information, `xpathLocation`, text), and `rep:assessment` → `rep:accept` or `rep:reject` with an embedded HTML "Prüfbericht" | observed in smoke test (F38) |

### 4.2 XRechnung validator configuration

- `itplr-kosit/validator-configuration-xrechnung`, **Apache-2.0**. The LICENSE file adds a note on the CEN/EU
  agreement for the standard ([LICENSE](https://github.com/itplr-kosit/validator-configuration-xrechnung/blob/master/LICENSE)) (F39).
- Latest release **2026-08-31** ("compatible with XRechnung 3.0", uses validator v1.6.3, CEN Schematron 1.3.16).
  Asset `xrechnung-3.0.2-validator-configuration-2026-08-31.zip`
  ([releases](https://github.com/itplr-kosit/validator-configuration-xrechnung/releases)) (F39).
- Scenarios: XRechnung UBL Invoice/CreditNote/CII, XRechnung Extension, CVD, **and plain EN 16931 for UBL Invoice,
  UBL CreditNote and CII**. Plain EN 16931 invoices get only the EN 16931 rules, not the German BR-DE rules
  (scenarios.xml; confirmed by the smoke test).
- Releases came roughly twice a year in 2024–2026, while KoSIT's operating concept moves to one main release per
  year ([versions page](https://xeinkauf.de/xrechnung/versionen-und-bundles/)).

### 4.3 Smoke test (run on 2026-11-23)

Downloaded the three official release assets (SHA-256 checked against GitHub's digests) and ran them in
`eclipse-temurin:21-jre`. Full commands and output: [`evidence/validator-smoke-2026-11-23.txt`](evidence/validator-smoke-2026-11-23.txt).

| Input | CLI result | Daemon HTTP |
|---|---|---|
| Official test case 01.01a, UBL | ACCEPTABLE (1 info: BR-DE-TMP-32) | 200 |
| Official test case 01.01a, CII | ACCEPTABLE (1 info: BR-DE-TMP-32) | 200 |
| 01.01a UBL, TaxInclusiveAmount changed 336.9 → 346.90 | **REJECT**: BR-CO-15, BR-CO-16 | **406** |
| 01.01a UBL, CustomizationID → plain `urn:cen.eu:en16931:2017` | ACCEPTABLE (EN 16931 scenario matched) | 200 |
| Non-XML body | — | **422** |
| `GET /` with `-G` | — | 405 |

CLI exit code was **1** (= one rejected file). The health endpoint returned `UP`, version 1.6.3.

What we learned beyond the docs:
- `-o <dir>` (output directory) and `-T <threads>` exist (shown by `--help`, not in the docs we read).
- "Schematron N" can still be **ACCEPTABLE**: messages of level `information`/`warning` do not reject. The UI must
  separate **errors** (blocking) from **warnings/hints**.
- The JVM picked a default max heap of ~1.9 GB. **In a container we must set `-Xmx`** (to be sized in M2).
- Single-machine timings (~0.05–0.4 s per document, first call slower) are indicative only, **not a benchmark**.

### 4.4 How Belegfluss can call the validator from Python

| Option | How | Pros | Cons |
|---|---|---|---|
| **A. Daemon as internal container** | Validator runs in its own container (`-D -G`). Python POSTs XML and maps 200/406/422 + parses `rep:message` | Official tool unchanged; JVM stays warm (fast); language-neutral HTTP; scales separately; same in Compose / Container Apps / AKS | Extra container; **no auth → must never be publicly reachable**; JDK HTTP server not tuned for heavy load (fine for our volume) |
| B. CLI subprocess per file | Python worker image also contains a JRE; `subprocess.run(java -jar …)` | Simplest code | JVM start-up for every file; Java inside the Python image (bigger image, mixed concerns) |
| C. Embed via JPype / Py4J | Load the Java library inside Python | Fast, one process | Complex, fragile, unusual. Fails "simple code" |
| D. Re-implement with Python Schematron (e.g. `saxonche`) | Run the official XSLT-compiled Schematron directly | No Java | We would re-implement scenario selection and report building. No longer "the official validator" |

**Recommendation: A** → [ADR-0005](../decisions/0005-validator-as-internal-daemon.md).

### 4.5 What the KoSIT validator does not cover (ZUGFeRD)

- It validates **XML only**. For ZUGFeRD we first extract the embedded XML from the PDF/A-3 (Python:
  [`factur-x`](https://github.com/akretion/factur-x), BSD licence, can extract/check/generate; or `pypdf`).
- ZUGFeRD **EN 16931 / EXTENDED** XML can be checked against EN 16931 rules with the KoSIT EN 16931 CII scenario.
  Profile-specific rules (MINIMUM, BASIC-WL, EXTENDED extras) need **FeRD's Schematron** (Apache-2.0 per FeRD's
  terms of use). Whether we can add it as an extra KoSIT scenario is an **M2 spike**.
- **PDF/A-3 conformance** (veraPDF) is not checked by KoSIT. **Mustang** (Apache-2.0, v2.26.0) can do it via CLI.
  Its REST server is a paid product ([mustangproject.org](https://www.mustangproject.org/)). PDF/A conformance
  matters less for a recipient, since the XML is leading (F15). We treat it as optional.

### 4.6 Visualisation component

- `itplr-kosit/xrechnung-visualization` (Apache-2.0, release 2026-10-13): XSLT that first converts **UBL or CII
  into one intermediate "semantic model" XML** (BT-numbered), then renders HTML or PDF. Visualisations are **not**
  valid XRechnung and not meant for archiving
  ([README](https://github.com/itplr-kosit/xrechnung-visualization)).
- The 2026-10-13 release **fixed a JavaScript-injection bug via attachment file names (BT-122/BT-125)**.
  → Any HTML we render from invoice data is **untrusted** and must be sandboxed (CSP, sandboxed iframe, no inline
  scripts).
- Idea for M2: the official step-1 transform gives us **one normalised model for both syntaxes**. That could replace
  writing two parsers. It needs XSLT 2.0+, i.e. Saxon (spike in M2).

## 5. Test data

| Source | Licence | Contents | Use in tests | Commit to our repo? |
|---|---|---|---|---|
| [KoSIT xrechnung-testsuite](https://github.com/itplr-kosit/xrechnung-testsuite) 2026-08-31 | Apache-2.0 | 86 XML files: 66 standard business cases (33 UBL + 33 CII), 6 extension (5 UBL + 1 CII), 12 CIUS + 2 CVD technical cases (counted in our download) | yes | Allowed with licence + attribution, but **we fetch it pinned by script** (cleaner) (F40) |
| [ConnectingEurope eInvoicing-EN16931](https://github.com/ConnectingEurope/eInvoicing-EN16931) v1.3.17 (2026-10-09) | **EUPL-1.2** | UBL and CII examples, CEN validation artefacts | yes | Fetch by script; avoid mixing EUPL files into our tree (F41) |
| [Mustang test resources](https://github.com/ZUGFeRD/mustangproject/tree/master/library/src/test/resources) | Apache-2.0 (repo) | ZUGFeRD/Factur-X PDFs and XMLs, some third-party files (veraPDF) | yes, file by file | Only after checking each file's origin (F42) |
| [akretion/factur-x](https://github.com/akretion/factur-x) | BSD | Python lib + fixtures; can **generate our own** Factur-X/ZUGFeRD PDFs | yes, as generator | Our generated files: yes (F43) |
| FeRD ZUGFeRD sample invoices ([download](https://www.ferd-net.de/faqs/zugferd-beispielrechnungen)) | **No licence found**; ZUGFeRD texts need AWV approval to reproduce; only schemas/Schematron are Apache-2.0 | ~5.5 MB zip of example PDFs/XMLs per profile | local only, after accepting FeRD terms | **No** (F44) |
| Our own synthetic invoices | ours | generated: varied layouts, German umlauts, multi-page, wrong VAT, duplicates, foreign currency | yes | yes |

**Labelled PDF set without real customer data (M3 idea):** render the official XRechnung XML test cases to PDF with
the official visualisation. The XML is then the **exact ground truth** for LLM extraction from that PDF. Caveat: all
those PDFs share one clean layout, so we still need synthetic layouts, photos/scans and (later, with consent) real
pilot invoices.

## 6. Accountant export

### 6.1 What exists (DATEV)

- **DATEV-Format** (official, publicly documented): a CSV file named `EXTF_…csv`. Line 1 is a header with metadata,
  line 2 column titles, then data rows. Semicolon-separated, CR/LF, quoted text, comma as decimal separator
  ([DATEV Developer Portal](https://developer.datev.de/de/file-formats/details/datev-format/getting-started)) (F45).
- The "Buchungsstapel" (booking batch) header contains the accountant's **Beraternummer and Mandantennummer**,
  fiscal-year start and account-number length. Every row needs **Konto and Gegenkonto** (accounts of the chart of
  accounts, e.g. SKR03/SKR04) (sample file on the same page) (F46).
  → A correct DATEV booking export is **bookkeeping** (choosing accounts), which is a non-goal, and it needs the
  accountant's numbers. It is only realistic as an option configured *with* the accountant.
- **DATEV interfaces can be implemented without a DATEV partnership**, but DATEV runs a technical review of
  interfaces in partner solutions ([DATEV Marktplatz](https://www.datev.de/web/de/berufsgruppenuebergreifend/ueber-datev/portfolio/oekosystem/partnering/datev-marktplatz)) (F47).
  Data services exist: Buchungsdatenservice, Belegbilderservice Rechnungswesen, Rechnungsdatenservice 1.0
  ([Schnittstellen-Anbieter](https://www.datev.de/web/de/marktplatz/datev-schnittstellen-anbieter)) (F48).
  Their terms and costs were not verified.
- **DATEV Unternehmen online** (the client-side cloud app of DATEV accountants) manages receipts **"inklusive
  E-Rechnung"** and receives, processes and archives e-invoices
  ([DATEV Unternehmen online](https://www.datev.de/web/de/unternehmen/loesungen/rechnungswesen/buchfuehrung/buchfuehrung-effizienter-gestalten/durchgaengig-digitale-kaufmaennische-prozesse)) (F49).
  Details such as "Upload Mail only accepts ZUGFeRD/PDF" come from search summaries and community posts and are
  **unverified**.

### 6.2 What is realistic for Belegfluss

| Option | Effort | Value | Recommendation |
|---|---|---|---|
| **ZIP of originals** (XML/PDF exactly as received) + **CSV summary** (one row per invoice: supplier, number, dates, net/VAT/gross per rate, status, problems) | low | Works for every accountant; the originals stay the legal documents | **Build first (M2/M6)** |
| Forward originals to the accountant's DATEV Unternehmen online (user's own channel) | low–medium | Fits existing DATEV workflows | Validate in accountant interviews |
| DATEV-Format EXTF Buchungsstapel | medium | Saves accountant typing, but needs accounts + Berater/Mandant numbers | Only if accountants ask for it, configured by them |
| DATEV API (Rechnungsdatenservice etc.) | high (review process, unknown cost) | Deep integration | Not before real demand |

→ [ADR-0009](../decisions/0009-accountant-export-zip-and-csv-first.md).

## 7. Implications for Belegfluss

1. **Viewing is commodity.** ELSTER's viewer is free and official (F17). DATEV Unternehmen online handles
   e-invoices for DATEV clients (F49). The BMF itself says many free viewers exist. Our value must be the
   **workflow**: one inbox for *mixed* documents → checks in plain language → a clean handoff to the accountant.
2. **The inbox stays mixed for years**, and many documents will never be e-invoices: ≤ €250 receipts (F11), tickets
   (F12), invoices from Kleinunternehmer suppliers (F13), foreign suppliers (§2.2), and sonstige Rechnungen during
   the transition (F8, F9). → The LLM extraction path is a long-term need, not just a bridge.
3. **Explainable findings with real value:**
   - "PDF and XML differ, and the XML is legally leading" (F15)
   - "ZUGFeRD MINIMUM/BASIC-WL is not an e-invoice" (F3)
   - "mandatory data only in the attachment" (F4)
   - VAT maths (BR-CO-15 etc.), duplicates
   - from 2027/2028: "this supplier probably should have sent an e-invoice" (F9, F10)
4. **Tone of findings:** validation is not a legal prerequisite (F16), so we say "please check", never "invalid".
   We do not give tax advice.
5. **Retention vs. deletion:** users must keep originals 8 years (F18, F19). We are not their archive (yet), so
   export before deletion and clear wording.
6. **Positioning ideas to test in interviews:** bilingual (English-speaking freelancers in Germany struggle with
   German invoices and rules), and accountants as a channel. → [user-interviews.md](user-interviews.md)

## 8. Verified facts

Status: ✅ confirmed in an official source (or by running the tool) · ⚠️ caveat · ❌ not verified (listed in §9).

| ID | Fact | Source | Status |
|---|---|---|---|
| F1 | E-invoice = structured electronic format enabling electronic processing; otherwise "sonstige Rechnung" | [§ 14 UStG](https://www.gesetze-im-internet.de/ustg_1980/__14.html) Abs. 1 S. 3–4 | ✅ |
| F2 | Format: EN norm + syntax list (Dir. 2014/55/EU), or agreed format if extractable/interoperable | § 14 Abs. 1 S. 6 UStG | ✅ |
| F3 | XRechnung and ZUGFeRD ≥ 2.0.1 qualify, except MINIMUM and BASIC-WL | [BMF FAQ](https://www.bundesfinanzministerium.de/Content/DE/FAQ/e-rechnung.html) Q7 (FAQ has no binding force) | ✅ |
| F4 | All mandatory data must be in the structured part | BMF FAQ Q7a | ✅ |
| F5 | Mandatory invoice fields | § 14 Abs. 4 UStG | ✅ |
| F6 | Obligation when supplier and recipient are established in Germany | § 14 Abs. 2 S. 2 Nr. 1 UStG; BMF FAQ Q3 | ✅ |
| F7 | All domestic businesses must be able to receive, no exceptions, incl. Kleinunternehmer | BMF FAQ Q12 | ✅ |
| F8 | Until 31 Dec 2026: sonstige Rechnung allowed (PDF only with consent) | [§ 27 Abs. 38 Nr. 1 UStG](https://www.gesetze-im-internet.de/ustg_1980/__27.html) | ✅ |
| F9 | 2027: only if issuer's prior-year turnover ≤ €800,000 | § 27 Abs. 38 Nr. 2 UStG | ✅ |
| F10 | From 1 Jan 2028 e-invoice mandatory (unless exempt) | BMF FAQ Q11 | ✅ |
| F11 | ≤ €250 gross may always be sonstige Rechnung | [§ 33 UStDV](https://www.gesetze-im-internet.de/ustdv_1980/__33.html) | ✅ |
| F12 | Travel tickets may always be sonstige Rechnung | [§ 34 UStDV](https://www.gesetze-im-internet.de/ustdv_1980/__34.html) | ✅ |
| F13 | Kleinunternehmer (≤ €25,000 / €100,000) may always issue sonstige Rechnung | [§ 34a UStDV](https://www.gesetze-im-internet.de/ustdv_1980/__34a.html), [§ 19 UStG](https://www.gesetze-im-internet.de/ustg_1980/__19.html) | ✅ |
| F14 | Supplies to non-business legal entities: sonstige Rechnung allowed | BMF FAQ Q4, Q5 | ✅ |
| F15 | Hybrid: structured XML part is leading | BMF FAQ Q12a; FeRD 2.4 news | ✅ |
| F16 | Validation not a prerequisite for tax recognition; BMF recommends none | BMF FAQ Q7 | ✅ |
| F17 | Free official viewer at e-rechnung.elster.de | BMF FAQ Q12a | ✅ |
| F18 | Retention 8 years | [§ 14b UStG](https://www.gesetze-im-internet.de/ustg_1980/__14b.html); [§ 147 AO](https://www.gesetze-im-internet.de/ao_1977/__147.html) | ✅ |
| F19 | Structured part stored unaltered in original form | BMF FAQ Q13 | ✅ |
| F20 | No transmission channel prescribed; email inbox suffices | BMF FAQ Q8 | ✅ |
| F21 | BMF letters of 15 Oct 2024, 15 Oct 2025, 15 Oct 2026 | BMF FAQ intro; [2025 letter page](https://www.bundesfinanzministerium.de/Content/DE/Downloads/BMF_Schreiben/Steuerarten/Umsatzsteuer/Umsatzsteuer-Anwendungserlass/2025-10-15-einfuehrung-obligatorische-e-rechnung.html); [2026 letter page](https://www.bundesfinanzministerium.de/Content/DE/Downloads/BMF_Schreiben/Steuerarten/Umsatzsteuer/Umsatzsteuer-Anwendungserlass/2026-10-15-obligatorische-elektronische-rechnung.html) | ⚠️ PDFs not read |
| F22 | Reporting system planned; rules may be adjusted | BMF FAQ Q1 | ✅ |
| F23 | ViDA: cross-border DRR from 1 Jul 2030 | [EC ViDA](https://taxation-customs.ec.europa.eu/taxation/vat/vat-digital-age-vida_en) | ⚠️ via search summary |
| F24 | EN 16931 parts 1–2 free; 2026 version published May 2026; 2017 withdrawn | [EC page](https://ec.europa.eu/digital-building-blocks/sites/spaces/DIGITAL/pages/467108971/Obtaining+a+copy+of+the+European+standard+on+eInvoicing) (page marked "under review") | ⚠️ |
| F25 | XRechnung = CIUS + Extension; syntaxes UBL 2.1 and UN/CEFACT CII | [xeinkauf.de](https://xeinkauf.de/xrechnung/) | ✅ |
| F26 | XRechnung 3.0 in force ≥ 31 Jul 2027; bundle 3.0.2 Summer 2026 Bugfix (31 Aug 2026) | [versions page](https://xeinkauf.de/xrechnung/versionen-und-bundles/) | ✅ |
| F27 | XRechnung 4.0 pre-release 15 Sep 2026, not productive, final spring 2027 | [version 4](https://xeinkauf.de/xrechnung/version-4) | ✅ |
| F28 | ZUGFeRD 2.5.2 = Factur-X 1.09.2 (4 Aug 2026, effective 1 Sep 2026), CII D22B | [FeRD 2.5.2](https://www.ferd-net.de/publikationen-produkte/publikationen/detailseite/zugferd-252-english), [FNFE](https://fnfe-mpe.org/factur-x/) | ✅ |
| F29 | KoSIT/FeRD mapping table Pflichtangaben → BT fields, recommended by BMF | BMF FAQ Q16; [KoSIT table](https://xeinkauf.de/aktuelles/xrechnung/pflichtangaben-nach-ustg-en16931/) | ✅ Table read 2026-11-24 ([HTML version](https://xeinkauf.de/xrechnung/ustg), July 2025). It calls itself an "Orientierungshilfe" (non-binding); used for the M2a checks |
| F30 | KoSIT validator is Apache-2.0 | [LICENSE](https://github.com/itplr-kosit/validator/blob/main/LICENSE) | ✅ |
| F31 | Latest validator v1.6.3 (2026-08-20) | [releases](https://github.com/itplr-kosit/validator/releases) | ✅ |
| F32 | Java ≥ 11 | README | ✅ (ran on Java 21) |
| F33 | CLI, library, daemon modes | README | ✅ |
| F34 | CLI syntax and exit codes | cli.md; smoke test exit code 1 for 1 rejected | ✅ ran |
| F35 | Daemon: POST raw XML; 200/406/422; `/server/health` | daemon.md; smoke test | ✅ ran |
| F36 | Daemon has no authentication | daemon.md | ✅ |
| F37 | No official Docker image | README, docs | ⚠️ absence of evidence |
| F38 | Report structure (`rep:message` code/level/xpath, `rep:assessment` accept/reject) | smoke test | ✅ ran |
| F39 | XRechnung config 2026-08-31, Apache-2.0, includes plain EN 16931 scenarios | [config releases](https://github.com/itplr-kosit/validator-configuration-xrechnung/releases); smoke test | ✅ ran |
| F40 | KoSIT test suite 2026-08-31, Apache-2.0 | [test suite](https://github.com/itplr-kosit/xrechnung-testsuite) | ✅ (file count from our download) |
| F41 | ConnectingEurope examples, EUPL-1.2 | [LICENSE.txt](https://github.com/ConnectingEurope/eInvoicing-EN16931/blob/master/LICENSE.txt) | ✅ |
| F42 | Mustang Apache-2.0, has ZUGFeRD test PDFs | [GitHub](https://github.com/ZUGFeRD/mustangproject) | ⚠️ per-file origin unchecked |
| F43 | akretion/factur-x is BSD, can generate/extract/check | [README](https://github.com/akretion/factur-x) | ✅ |
| F44 | FeRD samples: no redistribution licence found | [FeRD terms](https://www.ferd-net.de/en/ueber-uns/ressourcen-1/veroeffentlichungen/disclaimer-and-rights-of-use-zugferd) | ⚠️ absence of licence |
| F45 | DATEV-Format = EXTF CSV, header + titles + rows, semicolon | [DATEV Developer Portal](https://developer.datev.de/de/file-formats/details/datev-format/getting-started) | ✅ |
| F46 | Buchungsstapel needs Berater/Mandant numbers and Konto/Gegenkonto | same (sample file) | ✅ |
| F47 | DATEV interfaces possible without partnership; DATEV reviews them | [DATEV Marktplatz](https://www.datev.de/web/de/berufsgruppenuebergreifend/ueber-datev/portfolio/oekosystem/partnering/datev-marktplatz) | ✅ |
| F48 | DATEV data services (Buchungsdaten-, Belegbilder-, Rechnungsdatenservice) | [Schnittstellen-Anbieter](https://www.datev.de/web/de/marktplatz/datev-schnittstellen-anbieter) | ✅ (terms/costs ❌) |
| F49 | DATEV Unternehmen online receives/processes/archives e-invoices | [DATEV page](https://www.datev.de/web/de/unternehmen/loesungen/rechnungswesen/buchfuehrung/buchfuehrung-effizienter-gestalten/durchgaengig-digitale-kaufmaennische-prozesse) | ✅ (formats per channel ❌) |

## 9. Open questions

**Unverified in this session (to close in the milestone noted):**

1. **BMF letter PDFs** (15 Oct 2025 and 15 Oct 2026). Automated fetching returned HTTP 503, and Chrome's PDF viewer
   exposed no text. We rely on the official FAQ (as of 29 Oct 2026), which summarises them. → Read the PDFs
   manually before M5 (pilot), especially the 2026 "Ergänzende Regelungen".
2. **ZUGFeRD profile identifiers** and the normative name of the embedded XML file. → M2, from the FeRD 2.5.2
   specification.
3. **XRechnung 4.0 syntax versions** (UBL/CII) and the transition period. → Watch xeinkauf.de; final expected
   spring 2027.
4. **Can FeRD's Schematron run as an extra KoSIT scenario?** → M2 spike.
5. **DATEV Unternehmen online channels**: which formats Upload online / Upload Mail accept for e-invoices. → Ask the
   accountant in interviews; check DATEV Hilfe-Center.
6. **Costs and terms** of DATEV data services. → Only if pilots ask for it.
7. **ViDA** full text (EUR-Lex did not load). Not relevant before 2030.
8. **Azure facts for later milestones** are recorded in [ARCHITECTURE.md](../ARCHITECTURE.md#11-azure-facts-checked-in-m0)
   with their own open points (Entra External ID data location, Azure OpenAI EU model availability, prices).

**Need a human answer (interviews / you):**

9. Do freelancers actually receive e-invoices today, and how many (expected to grow sharply in 2027/2028)?
10. Does their accountant already provide a tool (DATEV Unternehmen online, lexoffice, sevDesk…)? If yes, what
    gap is left?
11. What exact handoff does an accountant want (ZIP, CSV, DATEV, forwarding)?
12. Would an English-speaking freelancer value a bilingual explanation layer enough to use a new tool?

## 10. All sources (read 2026-11-23)

- Law: [§ 14 UStG](https://www.gesetze-im-internet.de/ustg_1980/__14.html) · [§ 14b UStG](https://www.gesetze-im-internet.de/ustg_1980/__14b.html) · [§ 19 UStG](https://www.gesetze-im-internet.de/ustg_1980/__19.html) · [§ 27 UStG](https://www.gesetze-im-internet.de/ustg_1980/__27.html) · [§ 33 UStDV](https://www.gesetze-im-internet.de/ustdv_1980/__33.html) · [§ 34 UStDV](https://www.gesetze-im-internet.de/ustdv_1980/__34.html) · [§ 34a UStDV](https://www.gesetze-im-internet.de/ustdv_1980/__34a.html) · [§ 147 AO](https://www.gesetze-im-internet.de/ao_1977/__147.html) · [§ 5 DDG](https://www.gesetze-im-internet.de/ddg/__5.html)
- BMF: [FAQ E-Rechnung (29 Oct 2026)](https://www.bundesfinanzministerium.de/Content/DE/FAQ/e-rechnung.html) · [letter 15 Oct 2025](https://www.bundesfinanzministerium.de/Content/DE/Downloads/BMF_Schreiben/Steuerarten/Umsatzsteuer/Umsatzsteuer-Anwendungserlass/2025-10-15-einfuehrung-obligatorische-e-rechnung.html) · [letter 15 Oct 2026](https://www.bundesfinanzministerium.de/Content/DE/Downloads/BMF_Schreiben/Steuerarten/Umsatzsteuer/Umsatzsteuer-Anwendungserlass/2026-10-15-obligatorische-elektronische-rechnung.html)
- EU: [EN 16931 access](https://ec.europa.eu/digital-building-blocks/sites/spaces/DIGITAL/pages/467108971/Obtaining+a+copy+of+the+European+standard+on+eInvoicing) · [ViDA](https://taxation-customs.ec.europa.eu/taxation/vat/vat-digital-age-vida_en)
- KoSIT: [XRechnung](https://xeinkauf.de/xrechnung/) · [versions](https://xeinkauf.de/xrechnung/versionen-und-bundles/) · [version 4](https://xeinkauf.de/xrechnung/version-4) · [validator](https://github.com/itplr-kosit/validator) · [config](https://github.com/itplr-kosit/validator-configuration-xrechnung) · [test suite](https://github.com/itplr-kosit/xrechnung-testsuite) · [visualization](https://github.com/itplr-kosit/xrechnung-visualization)
- ZUGFeRD: [FeRD ZUGFeRD](https://www.ferd-net.de/standards/zugferd) · [FeRD 2.5.2](https://www.ferd-net.de/publikationen-produkte/publikationen/detailseite/zugferd-252-english) · [FeRD terms of use](https://www.ferd-net.de/en/ueber-uns/ressourcen-1/veroeffentlichungen/disclaimer-and-rights-of-use-zugferd) · [FNFE Factur-X](https://fnfe-mpe.org/factur-x/) · [Mustang](https://www.mustangproject.org/) · [factur-x (Python)](https://github.com/akretion/factur-x)
- Test data: [ConnectingEurope eInvoicing-EN16931](https://github.com/ConnectingEurope/eInvoicing-EN16931)
- DATEV: [DATEV-Format](https://developer.datev.de/de/file-formats/details/datev-format/getting-started) · [Marktplatz](https://www.datev.de/web/de/berufsgruppenuebergreifend/ueber-datev/portfolio/oekosystem/partnering/datev-marktplatz) · [Schnittstellen-Anbieter](https://www.datev.de/web/de/marktplatz/datev-schnittstellen-anbieter) · [Unternehmen online](https://www.datev.de/web/de/unternehmen/loesungen/rechnungswesen/buchfuehrung/buchfuehrung-effizienter-gestalten/durchgaengig-digitale-kaufmaennische-prozesse)
