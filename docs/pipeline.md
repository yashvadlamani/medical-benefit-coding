# Prototype pipeline: steps 1 to 3

The `benefit_coding` package implements the first three pipeline stages from the [architecture](architecture.md): ingest, AI extraction, and code mapping. Validation (step 4) and the review screen (step 5) are not built yet.

## Running it

```bash
pip install -r requirements.txt
python ingest/download_public_docs.py        # fetch the public documents into ./data
python -m benefit_coding run                 # steps 1-3 for all 25 plans
python -m benefit_coding run --plan 38166WI0140004
python -m benefit_coding run --file path/to/any.pdf
python -m benefit_coding evaluate            # writes docs/accuracy-report.md
python -m pytest tests
```

Settings come from a git-ignored `.env` file; see [`.env.example`](../.env.example). The Azure resources it points to are listed under [Services used](#services-used).

Results are written to `./output` (git-ignored):

| Folder | Contents |
| --- | --- |
| `output/ingested/<plan>.json` | Page text, document type, sections |
| `output/extracted/<plan>.json` | One record per field: value, citation, confidence, review flag |
| `output/coded/<plan>.json` | One record per field: system codes, parameters, suggestions, review flag |

## Services used

Everything runs from a local Python process. It calls two Azure resources, both in resource group `medical-benefit-coding-rg`, and downloads source documents from public websites. No member data or client data is sent anywhere.

| Step | Service | Type | Resource / detail | Used for |
| --- | --- | --- | --- | --- |
| Data collection | CMS Exchange Public Use Files (`download.cms.gov`, `cms.gov`) | External, public | Plan year 2026 files, data dictionaries, sample SBC | Plan list, SBC links, published cost-sharing values (answer key) |
| Data collection | Insurer websites (`alabamablue.com`, `mountainhealth.coop`, `sbc.anthem.com`, `file.anthem.com`, `securityhealth.org`) | External, public | SBC and brochure PDFs | Source documents for the 25 plans |
| Data collection | Azure Blob Storage | Azure | Account `medbencodingf946de69`, container `prototype-docs`, Standard LRS, Central US, public access off | Stores the downloaded documents, answer key and manifest |
| 1. Ingest | PyMuPDF | Local library | | Reads the text layer of digital PDFs |
| 1. Ingest | Azure Document Intelligence | Azure | Resource `medbencoding-ai` (Azure AI Services, S0, East US 2), `prebuilt-read` model, API `2024-11-30` | OCR, only when a PDF has no usable text layer |
| 1. Ingest | None | Local code | | Document classification and section splitting are rule-based |
| 2. Extract | Azure OpenAI | Azure | Resource `medbencoding-ai`, deployment `extract`, model `gpt-5-mini` version `2025-08-07`, Global Standard, API `2024-10-21`, called through the `openai` Python SDK | Structured extraction of the 22 fields with quotes and confidence |
| 2. Extract | None | Local code | | Citation check and review flag |
| 3. Map | None | Local code | `benefit_coding/code_library.csv` | Lookup of system codes; no network calls |
| Scoring | None | Local code | Answer key in `data/golden/` | Accuracy report |

Supporting tools:

| Tool | Used for |
| --- | --- |
| Azure CLI (`az`) | Creating the resources; uploading documents to Blob Storage with `--upload` |
| `curl` | Downloading the public documents |
| GitHub | Source repository; documents and outputs are not stored there |
| `pytest` | Unit tests; they make no network calls |

Notes:

- **Authentication:** the pipeline uses the AI resource's key from the git-ignored `.env` file. Blob uploads use the logged-in Azure CLI account.
- **What leaves the machine:** step 2 sends the text of the SBC sections to Azure OpenAI; step 1 sends the whole PDF to Document Intelligence only when OCR is needed. Both are public documents.
- **Cost:** both AI services are pay-per-use with no idle charge. A full 25-plan run uses about 100k input and 160k output tokens. OCR is billed per page and was used for one 7-page test document.
- **Separate from HCM-Agent:** none of these resources are shared with the `clara-rg` resource group.

## Step 1: Ingest ([`ingest.py`](../benefit_coding/ingest.py), [`ocr.py`](../benefit_coding/ocr.py))

- **Read:** text is taken from the PDF's text layer. If the document averages under 80 characters a page it is treated as a scan and sent to Azure Document Intelligence for OCR.
- **Classify:** the first three pages are scored against marker phrases for each type: `sbc`, `plan_brochure`, `benefit_grid`, `rider`, otherwise `other`.
- **Split:** an SBC is cut at the headings of the federal template into `header`, `important_questions`, `common_medical_events`, `excluded_and_other_services`, `rights_and_notices` and `coverage_examples`. Other documents are split by page. Every passage keeps its page number.

## Step 2: Extract ([`extract.py`](../benefit_coding/extract.py))

The header, important-questions and common-medical-events sections go to the LLM in one call, with a JSON schema that forces one record for each of the 22 fields in [`fields.py`](../benefit_coding/fields.py):

| Kind | Fields | Value |
| --- | --- | --- |
| Amount | Deductible and out-of-pocket limit; individual and family; in and out of network (8) | Dollar amount, or not applicable |
| Cost share | PCP, specialist, preventive, ER, urgent care, hospital stay, outpatient surgery, imaging, drug tiers 1-4 (12) | Copay, coinsurance, whether the deductible applies; or no charge / not covered |
| Flag | Prior authorization for imaging and for a hospital stay (2) | Yes / no |

Every record carries a quote, a page number and a confidence score. After the model answers:

- **Citation check:** the quote must be found on a page of the document, compared word by word with numbers kept whole, so a quote with a changed figure fails. A field whose quote is not found has its confidence capped at 0.3.
- **Review flag:** any field under 0.8 confidence, or not found in the document, is marked for review.

## Step 3: Map ([`mapping.py`](../benefit_coding/mapping.py), [`code_library.csv`](../benefit_coding/code_library.csv))

The code library is a lookup table of `field, type, value, system_code`. It is a placeholder: 716 invented codes such as `PCP-CP0030` (PCP visit, $30 copay) that each client would replace with its own table.

- Deductibles and out-of-pocket limits map to an accumulator code with the dollar amount as a parameter.
- Cost shares map to one code per component, so "$250 copay then 20%" gives two codes.
- A value the table does not hold (for example a $120 copay) is left **unmapped** and sent to review with suggestions: the nearest values in the table, and codes that already-coded plans from the same insurer used for that field.

## Results

Final run on the 25 pinned plans, scored against the values CMS publishes for each plan. Full detail is in the [accuracy report](accuracy-report.md).

| Measure | Result | Approval target |
| --- | --- | --- |
| Field accuracy, simple plans | 99.7% | 90%+ |
| Field accuracy, moderate plans | 98.5% | 80%+ |
| Field accuracy, all plans | 99.2% (496 of 500) | |
| Extracted values with a verified citation | 503 of 503 | 100% |
| Wrong fields that were flagged for review | 3 of 4 | |
| Fields mapped to a code | 494 of 550 | |
| Fields left unmapped (value not in the code table) | 9 | |
| Fields not stated in the SBC | 47 | |
| Fields sent to review | 72 of 550, between 1 and 7 per plan | |

How to read these numbers:

- **The extraction rules were tuned on these same 25 plans.** The first run, before any tuning, scored 96.2% (98.7% simple, 92.5% moderate). The misses were systematic: six-tier drug formularies, split generic tiers, and multi-column provider tables.
- **Unseen plans:** ten other small-group plans that were never used for tuning scored 99.5% (199 of 200), with every citation verified. They come from the same four insurers, so this does not show how the pipeline handles a new insurer's layout.
- **Results vary slightly between runs.** The model is not deterministic; runs on the 25 plans ranged from 99.2% to 100%.
- **The answer key is the insurer's filed cost sharing, not claims-system codes.** Extraction is scored; code mapping is only checked by unit tests because the code table is invented.
- **The 47 "not stated" fields** are mostly the prior-authorization flags, which many SBCs do not mention, and are not scored.

## Not covered yet

- Only SBCs are extracted. Brochures are classified but not used.
- OCR was checked on one scan-like copy of an SBC through ingest only (text read, classified and split correctly); extraction accuracy on scans is not measured.
- Outputs stay in `./output`; they are not uploaded to blob storage.
- No SBC reconciliation, test claims, review screen or audit trail (steps 4 and 5).
