# Evaluation report: dev-ablations

- Runs: `2026-11-25-azure-dev-p97843178`, `2026-11-25-azure-dev-medium-p9eef6db0`, `2026-11-25-azure-dev-image-only-p97843178`
- Extractor: azure, model `gpt-5.4-mini`, deployment `gpt-5.4-mini`, reasoning effort `low`
- Prompt fingerprint: `97843178febb`; dataset version `409a087cfd9b`; split `dev`; date 2026-11-25
- Scored with the production mapping and checks (`eval/src/belegfluss_eval/scoring.py`).

## Headline

| | |
|---|---|
| Documents | 79 |
| **Document accuracy** (all export fields right) | **77.2 %** (95 % CI 66.8 % to 85.1 %) |
| Catch rate (wrong documents flagged) | 27.8 % |
| False alarms (correct documents flagged) | 0.0 % |
| Cost per document | $0.0055 |
| Seconds per document, p50 / p95 | 3.1 / 5.1 |

## Accuracy per field

| Field | `2026-11-25-azure-dev-p97843178` | `2026-11-25-azure-dev-medium-p9eef6db0` | `2026-11-25-azure-dev-image-only-p97843178` |
|---|---:|---:|---:|
| number | 100.0 % | 97.5 % | 98.7 % |
| issue_date | 100.0 % | 100.0 % | 97.5 % |
| due_date | 96.2 % | 96.2 % | 96.2 % |
| currency | 98.7 % | 97.5 % | 98.7 % |
| seller_name | 98.7 % | 100.0 % | 98.7 % |
| seller_vat_id | 87.3 % | 86.1 % | 77.2 % |
| buyer_name | 100.0 % | 100.0 % | 100.0 % |
| iban | 88.6 % | 86.1 % | 81.0 % |
| net | 96.2 % | 97.5 % | 94.9 % |
| vat | 98.7 % | 97.5 % | 98.7 % |
| gross | 97.5 % | 98.7 % | 98.7 % |
| due | 97.5 % | 97.5 % | 97.5 % |
| vat_breakdown | 97.5 % | 97.5 % | 97.5 % |
| line_count | 82.3 % | 82.3 % | 82.3 % |
| **document** | **77.2 %** | **73.4 %** | **62.0 %** |
| cost / document | $0.0055 | $0.0090 | $0.0054 |
| seconds p50 | 3.1 | 5.8 | 3.1 |

## By source and variant (main run)

| Group | Documents | Document accuracy | 95 % CI | Catch rate | False alarms |
|---|---:|---:|---|---:|---:|
| official/original | 38 | 78.9 % | 63.7 % to 88.9 % | 37.5 % | 0.0 % |
| official/photo | 4 | 25.0 % | 4.6 % to 69.9 % | 0.0 % | 0.0 % |
| official/scan | 3 | 0.0 % | 0.0 % to 56.2 % | 33.3 % | n/a |
| synthetic/original | 28 | 89.3 % | 72.8 % to 96.3 % | 0.0 % | 0.0 % |
| synthetic/photo | 3 | 66.7 % | 20.8 % to 93.9 % | 100.0 % | 0.0 % |
| synthetic/scan | 3 | 100.0 % | 43.8 % to 100.0 % | n/a | 0.0 % |

Documents with at most 2 pages (what Document Intelligence F0 can read): 58, document accuracy 79.3 %.

## Wrong fields (main run, first 25 of 48)

| Document | Field | Expected | Read |
|---|---|---|---|
| official-001 | seller_vat_id | DE/12/345/67890 | - |
| official-001 | line_count | 2 | 7 |
| official-002 | iban | - | DE79000000001234567890 |
| official-002 | line_count | 1 | 3 |
| official-017 | seller_vat_id | DE123456789 | - |
| official-056 | net | 2311.94 | 1492.23 |
| official-056 | line_count | 23 | 5 |
| official-065 | iban | - | DE79000000001234567890 |
| official-065 | line_count | 9 | 6 |
| official-067 | iban | - | DE79000000001234567890 |
| official-070 | iban | DE79000000001234567890 | - |
| official-072 | line_count | 2 | 1 |
| official-085 | seller_vat_id | ATU123456789 | 987654321 |
| official-085 | line_count | 2 | 1 |
| synthetic-017 | due_date | 2026-06-25 | - |
| synthetic-065 | net | 3038.66 | - |
| synthetic-065 | gross | 3545.67 | - |
| synthetic-065 | due | 3545.67 | - |
| synthetic-079 | currency | EUR | - |
| synthetic-079 | seller_vat_id | DE967264283 | - |
| synthetic-079 | iban | DE46901907611039672366 | - |
| synthetic-079 | net | 108858.95 | - |
| synthetic-079 | vat | 20683.20 | 0.00 |
| synthetic-079 | gross | 129542.15 | - |
| synthetic-079 | due | 129542.15 | - |
