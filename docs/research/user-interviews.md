# User interview guide — validate the problem before building

> **Goal:** find out whether freelancers and small businesses in Germany have a real, painful problem with incoming
> invoices (e-invoices mixed with PDFs and photos) and with handing them to their accountant. Do this **before** we
> build beyond M1.
> **Format:** 5 conversations of ~25 minutes, in person or video, in German or English.
> **Rule:** ask about **past behaviour**, not opinions about a future product. Do not pitch Belegfluss until the
> last 2 minutes.

## 1. What we want to learn

| # | Hypothesis | Evidence that supports it | Evidence against it (kill / pivot signal) |
|---|---|---|---|
| H1 | They already receive e-invoices (XML or ZUGFeRD) and find them hard to open, read or check | Can name a recent XML/e-invoice and what they did with it | "Never seen one", or the tool opens it fine |
| H2 | Collecting invoices for the accountant is tedious and manual | Describes a monthly ritual (email search, folders, uploads); can say how long it takes | Fully automated already (e.g. bank + DATEV Unternehmen online) |
| H3 | They can't tell whether an invoice is correct, and errors cause follow-up questions from the accountant | Recalls an accountant query about a wrong/missing invoice | Never had a problem |
| H4 | Accountants receive messy input and would value a clean, checked handoff | Accountant names concrete time lost per client | Accountant says clients' input is fine, or their own tool does everything |
| H5 | English-speaking freelancers have extra pain (German rules, German-only tools) | Mentions translation tools, asking friends, fear of mistakes | No difference to German speakers |
| H6 | Existing tools (DATEV Unternehmen online, lexoffice/Lexware Office, sevDesk, ELSTER viewer) do **not** cover it | Uses one but still does manual work around it | Their tool solves it end to end → **pivot or narrow the niche** |

**Decision after 5 interviews:**
- **Go:** ≥ 3 of 5 describe H1/H2 pain unprompted, ≥ 2 want to try a free pilot, and the accountant confirms a
  handoff format.
- **Narrow / pivot:** pain exists only for one group (e.g. only English speakers, only accountants). Re-scope the
  product to that group.
- **Stop and rethink:** most already use a tool that covers it. → Write an ADR and re-plan.

## 2. Who to ask (3–5 people)

| # | Profile | Why | Where to find them |
|---|---|---|---|
| P1 | Freelancer, German-speaking (e.g. designer, developer, coach), ideally **regular VAT** (not Kleinunternehmer) | Core user; receives B2B invoices (software, co-working, subcontractors) | Own network, local university alumni, local co-working spaces |
| P2 | Freelancer, **English-speaking**, living in Germany | Tests the bilingual hypothesis (H5) | Expat/freelancer meetups, LinkedIn, international colleagues |
| P3 | **Small business / Handwerk** (electrician, carpenter, small shop) | Many supplier invoices from wholesalers, who will send e-invoices early | Local businesses, family/friends' network |
| P4 | (optional) **Verein treasurer** (Kassenwart) | Associations with business activities must receive e-invoices too | Sports clubs, cultural associations |
| P5 | **Steuerberater / accountant** or bookkeeper in a firm | Second side of the handoff; decides what format is useful; possible channel to many users | Ask P1–P3 for their accountant; local firms |

Mix: at least one Kleinunternehmer and one regular-VAT business among P1–P4. They have different duties (F13 in
[einvoicing.md](einvoicing.md)).

## 3. Recruiting message

**Deutsch**

> Hallo [Name], ich baue gerade ein kleines Werkzeug, das Selbstständigen und kleinen Firmen bei eingehenden
> Rechnungen (E-Rechnung, PDF, Fotos) helfen soll. Bevor ich etwas programmiere, möchte ich verstehen, wie du das
> heute machst. Hättest du 25 Minuten für ein kurzes Gespräch (persönlich oder per Video)? Ich verkaufe nichts, und
> ich brauche keine echten Rechnungen von dir. Danke!

**English**

> Hi [name], I'm building a small tool to help freelancers and small businesses with incoming invoices (e-invoices,
> PDFs, photos). Before I write any code, I want to understand how you handle this today. Would you have 25 minutes
> for a short chat (in person or video)? I'm not selling anything, and I don't need any of your real invoices.
> Thank you!

## 4. Consent and privacy (read out at the start)

**Deutsch:** "Ich mache mir Notizen, aber ohne deinen Namen. Ich nehme nichts auf, außer du stimmst ausdrücklich zu.
Bitte zeig mir keine echten Rechnungen und nenne keine Kundennamen. Du kannst jederzeit abbrechen. Ist das okay?"

**English:** "I'll take notes, but without your name. I won't record anything unless you explicitly agree. Please
don't show me real invoices or name your clients. You can stop at any time. Is that okay?"

Rules for us:
- Notes use participant codes (P1…P5). **Raw notes and contact details never go into this repository.** Keep them
  in a private place and delete them when no longer needed.
- Only an **anonymous summary** goes into `docs/research/interview-findings.md`.
- If someone offers a real invoice: politely decline. We only use official test data until the pilot has proper
  consent and a privacy policy (see PLAN.md, M5).

## 5. Interview script — freelancers and small businesses (≈25 min)

| Time | Deutsch | English |
|---|---|---|
| **0–2 Intro** | Danke! Es geht um deine Erfahrungen, es gibt keine falschen Antworten. | Thanks! This is about your experience, there are no wrong answers. |
| **2–7 Context** | 1. Was machst du beruflich, und seit wann selbstständig? | 1. What do you do, and how long have you been self-employed? |
| | 2. Bist du Kleinunternehmer oder weist du Umsatzsteuer aus? | 2. Are you a Kleinunternehmer, or do you charge VAT? |
| | 3. Wie viele Rechnungen *bekommst* du ungefähr im Monat? Von wem (Software, Material, Subunternehmer, Ausland)? | 3. Roughly how many invoices do you *receive* per month? From whom (software, materials, subcontractors, abroad)? |
| **7–15 Current process** | 4. Erzähl mir von der letzten Rechnung, die du bekommen hast. Was ist von Ankunft bis „erledigt" passiert? | 4. Tell me about the last invoice you received. What happened from arrival to "done"? |
| | 5. Wo landen Rechnungen (E-Mail, Papier, Portal-Download, Foto)? Wo bewahrst du sie auf? | 5. Where do invoices arrive (email, paper, portal download, photo)? Where do you keep them? |
| | 6. Wie bekommt dein Steuerberater die Belege? Wie oft? Wie lange dauert das? | 6. How does your accountant get your documents? How often? How long does it take? |
| | 7. Wann hat zuletzt etwas nicht gestimmt (falscher Betrag, fehlende Angabe, doppelte Rechnung)? Wie hast du es gemerkt? | 7. When was the last time something was wrong (wrong amount, missing info, duplicate)? How did you notice? |
| | 8. Welche Tools nutzt du dafür (DATEV Unternehmen online, lexoffice, sevDesk, Excel, Ordner)? Was nervt daran? | 8. Which tools do you use for this (DATEV Unternehmen online, lexoffice, sevDesk, Excel, folders)? What annoys you about them? |
| **15–20 E-invoices** | 9. Hast du schon eine E-Rechnung bekommen, also eine XML-Datei oder ein ZUGFeRD-PDF? Was hast du damit gemacht? | 9. Have you received an e-invoice yet, i.e. an XML file or a ZUGFeRD PDF? What did you do with it? |
| | 10. Was weißt du über die E-Rechnungspflicht? Woher? Was macht dir Sorgen? | 10. What do you know about the e-invoicing rules? From where? What worries you? |
| | 11. *(nur für Englischsprachige)* Wie gehst du mit deutschen Rechnungen und Regeln um? | 11. *(English speakers only)* How do you deal with German invoices and rules? |
| **20–23 Value** | 12. Wenn du einen Teil davon wegzaubern könntest, welchen? | 12. If you could make one part of this disappear, which one? |
| | 13. Hast du schon nach einer Lösung gesucht oder für eine bezahlt? Welche? | 13. Have you looked for, or paid for, a solution? Which one? |
| **23–25 Wrap-up** | 14. *(jetzt kurz die Idee zeigen)* Würdest du in einem kostenlosen Pilot mit Testdaten mitmachen? | 14. *(now briefly show the idea)* Would you join a free pilot with test data? |
| | 15. Kennst du jemanden, mit dem ich auch sprechen sollte, z. B. deinen Steuerberater? | 15. Do you know someone else I should talk to, e.g. your accountant? |

Follow-up prompts in both languages: *"Warum?" / "Why?"*, *"Kannst du ein Beispiel geben?" / "Can you give an
example?"*, *"Was ist dann passiert?" / "What happened next?"*.

## 6. Interview script — accountant / Steuerberater (≈25 min)

| Deutsch | English |
|---|---|
| 1. Wie viele Mandanten sind Selbstständige oder Kleinbetriebe? | 1. How many of your clients are freelancers or small businesses? |
| 2. Wie bekommen diese Mandanten ihre Belege zu Ihnen (DATEV Unternehmen online, Upload Mail, E-Mail, Papier)? | 2. How do these clients send you their documents (DATEV Unternehmen online, Upload Mail, email, paper)? |
| 3. Welche Formate kommen an, und wie viele E-Rechnungen (XRechnung, ZUGFeRD) sind es heute? | 3. Which formats arrive, and how many e-invoices (XRechnung, ZUGFeRD) are there today? |
| 4. Was geht am häufigsten schief (fehlende Belege, falsche Angaben, Duplikate, unlesbare Fotos)? Wie viel Zeit kostet das pro Mandant und Monat? | 4. What goes wrong most often (missing documents, wrong data, duplicates, unreadable photos)? How much time does that cost per client per month? |
| 5. Wie gehen Sie mit XML-Rechnungen um? Prüfen Sie sie (Validator, Viewer)? | 5. How do you handle XML invoices? Do you check them (validator, viewer)? |
| 6. Wenn ein Mandant Ihnen Belege „sauber" übergibt, was genau wäre ideal: ZIP mit Originalen, CSV-Liste, DATEV-Format (EXTF), direkt in DATEV Unternehmen online? | 6. If a client hands over documents "cleanly", what exactly would be ideal: ZIP of originals, CSV list, DATEV-Format (EXTF), straight into DATEV Unternehmen online? |
| 7. Würden Sie für einen Import Konten (SKR03/04) oder Ihre Berater-/Mandantennummer bereitstellen, oder ist das zu viel? | 7. Would you provide accounts (SKR03/04) or your Berater/Mandant numbers for an import, or is that too much? |
| 8. Was müsste ein Tool erfüllen, damit Sie es Mandanten empfehlen (Datenschutz, Serverstandort, Archivierung)? | 8. What would a tool need for you to recommend it to clients (data protection, server location, archiving)? |
| 9. Was halten Sie davon, wenn ein Tool Probleme in einfacher Sprache erklärt, z. B. „PDF und XML weichen ab"? | 9. What do you think of a tool explaining problems in plain language, e.g. "the PDF and the XML differ"? |
| 10. Dürfte ich Sie später noch einmal zu einem Prototyp fragen? | 10. May I ask you again later about a prototype? |

## 7. Note template (one per interview, kept outside git)

```text
Code: P_  | Date: ____ | Profile: freelancer / small business / Verein / accountant
Language: DE / EN | VAT status: Kleinunternehmer / regular | Invoices received per month: ___
Current process (arrival → storage → accountant): ...
Tools used: ...
Last problem (story, with what happened next): ...
E-invoice experience (yes/no, what they did): ...
Time spent per month on invoices: ___
Strongest pain (their words, translated if needed): "..."
H1 H2 H3 H4 H5 H6 → supported / against / unclear (one line each)
Pilot interest: yes / maybe / no   | Referral: ...
```

## 8. After the interviews

1. Write `docs/research/interview-findings.md`: an anonymous summary per hypothesis, quotes without names, decision
   (go / narrow / stop).
2. If the findings change scope or priorities: write an ADR that supersedes the affected decision, update `PLAN.md`,
   and log it in `docs/PROJECT_LOG.md` (change rule in [PLAN.md](../../PLAN.md#6-working-rules)).
3. Feed concrete examples (anonymised) into the synthetic test-data generator for M3.
