# Evaluation report: test-repeat

- Runs: `2026-11-25-azure-test-p97843178`, `2026-11-25-azure-test-p97843178-2`
- Extractor: azure, model `gpt-5.4-mini`, deployment `gpt-5.4-mini`, reasoning effort `low`
- Prompt fingerprint: `97843178febb`; dataset version `409a087cfd9b`; split `test`; date 2026-11-25
- Scored with the production mapping and checks (`eval/src/belegfluss_eval/scoring.py`).

## Headline

| | |
|---|---|
| Documents | 127 |
| **Document accuracy** (all export fields right) | **71.7 %** (95 % CI 63.3 % to 78.8 %) |
| Catch rate (wrong documents flagged) | 16.7 % |
| False alarms (correct documents flagged) | 1.1 % |
| Cost per document | $0.0054 |
| Seconds per document, p50 / p95 | 2.9 / 5.5 |

## Accuracy per field

| Field | `2026-11-25-azure-test-p97843178` | `2026-11-25-azure-test-p97843178-2` |
|---|---:|---:|
| number | 96.9 % | 99.2 % |
| issue_date | 99.2 % | 100.0 % |
| due_date | 93.7 % | 93.7 % |
| currency | 99.2 % | 99.2 % |
| seller_name | 98.4 % | 99.2 % |
| seller_vat_id | 83.5 % | 83.5 % |
| buyer_name | 99.2 % | 100.0 % |
| iban | 89.0 % | 89.0 % |
| net | 95.3 % | 96.1 % |
| vat | 96.1 % | 96.9 % |
| gross | 96.1 % | 96.9 % |
| due | 96.1 % | 96.9 % |
| vat_breakdown | 95.3 % | 96.1 % |
| line_count | 83.5 % | 82.7 % |
| **document** | **71.7 %** | **74.8 %** |
| cost / document | $0.0054 | $0.0054 |
| seconds p50 | 2.9 | 3.8 |

## By source and variant (main run)

| Group | Documents | Document accuracy | 95 % CI | Catch rate | False alarms |
|---|---:|---:|---|---:|---:|
| official/original | 48 | 68.8 % | 54.7 % to 80.1 % | 13.3 % | 3.0 % |
| official/photo | 6 | 0.0 % | 0.0 % to 39.0 % | 0.0 % | n/a |
| official/scan | 7 | 0.0 % | 0.0 % to 35.4 % | 14.3 % | n/a |
| synthetic/original | 52 | 92.3 % | 81.8 % to 97.0 % | 0.0 % | 0.0 % |
| synthetic/photo | 7 | 57.1 % | 25.0 % to 84.2 % | 66.7 % | 0.0 % |
| synthetic/scan | 7 | 85.7 % | 48.7 % to 97.4 % | 100.0 % | 0.0 % |

Documents with at most 2 pages (what Document Intelligence F0 can read): 98, document accuracy 75.5 %.

## Same documents, run by run (`2026-11-25-azure-test-p97843178` vs `2026-11-25-azure-test-p97843178-2`)

| | Documents |
|---|---:|
| right in both | 87 |
| wrong in both | 28 |
| right only in `2026-11-25-azure-test-p97843178` | 4 |
| right only in `2026-11-25-azure-test-p97843178-2` | 8 |

Changed result: official-015, official-026, official-031, official-039, official-060, official-071, official-074, official-080, synthetic-014, synthetic-027-photo, synthetic-069-scan, synthetic-075-scan.

## Wrong fields (main run, first 25 of 100)

| Document | Field | Expected | Read |
|---|---|---|---|
| official-003 | seller_vat_id | DE/12/345/67890 | - |
| official-003 | line_count | 1 | 32 |
| official-004 | due_date | - | 2021-08-13 |
| official-004 | seller_vat_id | DE814060619 | - |
| official-004 | line_count | 1 | 8 |
| official-023 | iban | DE79000000001234567890 | - |
| official-026 | number | RECHNUNGSNUMMER | - |
| official-031 | number | RECHNUNGSNUMMER | - |
| official-032 | seller_vat_id | DE123456789 | - |
| official-032 | line_count | 11 | 7 |
| official-046 | net | 233.00 | 208.00 |
| official-059 | seller_name | - | kundencenter |
| official-059 | buyer_name | - | buyername |
| official-059 | iban | - | DE79000000001234567890 |
| official-060 | iban | - | DE79000000001234567890 |
| official-060 | line_count | 14 | 5 |
| official-071 | seller_vat_id | ATU123456789 | - |
| official-073 | seller_vat_id | ATU123456789 | - |
| official-073 | line_count | 2 | 1 |
| official-074 | seller_vat_id | ATU123456789 | ATU123456789/1234567 |
| official-076 | line_count | 2 | 1 |
| official-077 | seller_vat_id | ATU123456789 | - |
| official-077 | line_count | 2 | 1 |
| official-079 | iban | - | DE79000000001234567890 |
| official-080 | seller_vat_id | ATU123456789 | - |
