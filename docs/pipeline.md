# Prototype pipeline: steps 1 to 5

The `benefit_coding` package implements pipeline stages 1 to 4 from the [architecture](architecture.md): ingest, AI extraction, code mapping and automated validation. Stage 5, the review screen, is the Flask app in [`app.py`](../app.py), running at <https://medbencoding-review-f946de69.azurewebsites.net>. This is a rough first draft.

## Running it

```bash
pip install -r requirements.txt
python ingest/download_public_docs.py        # fetch the public documents into ./data
python -m benefit_coding seed-codes          # once: load the code library into Azure Table Storage
python -m benefit_coding run                 # steps 1-3 for all 25 plans
python -m benefit_coding run --plan 38166WI0140004
python -m benefit_coding run --file path/to/any.pdf
python -m benefit_coding evaluate            # writes docs/accuracy-report.md
python -m benefit_coding seed-mismatch       # adds a demo plan with one deliberately wrong value
python -m benefit_coding validate            # step 4 for every coded plan; writes docs/validation-report.md
flask run                                    # step 5 locally; the hosted copy is on Azure App Service
python -m pytest tests
```

Settings come from a git-ignored `.env` file; see [`.env.example`](../.env.example). The Azure resources it points to are listed under [Services used](#services-used).

Results are written to Azure Blob Storage, in the `prototype-docs` container, so the pipeline and the hosted review app share them:

| Blob | Contents |
| --- | --- |
| `output/ingested/<plan>.json` | Page text, document type, sections |
| `output/extracted/<plan>.json` | One record per field: value, citation, confidence, review flag |
| `output/coded/<plan>.json` | One record per field: system codes, parameters, suggestions, review flag |
| `output/validated/<plan>.json` | Checks, judge verdicts, test claims, and which fields need a reviewer |
| `output/index.json` | One summary row per plan, for the review app's plan list |

## Services used

The pipeline is orchestrated by a local Python process. Document reading, extraction and the code library all run on Azure resources in resource group `medical-benefit-coding-rg`; source documents are downloaded from public websites. No member data or client data is sent anywhere.

| Step | Service | Type | Resource / detail | Used for |
| --- | --- | --- | --- | --- |
| Data collection | CMS Exchange Public Use Files (`download.cms.gov`, `cms.gov`) | External, public | Plan year 2026 files, data dictionaries, sample SBC | Plan list, SBC links, published cost-sharing values (answer key) |
| Data collection | Insurer websites (`alabamablue.com`, `mountainhealth.coop`, `sbc.anthem.com`, `file.anthem.com`, `securityhealth.org`) | External, public | SBC and brochure PDFs | Source documents for the 25 plans |
| Data collection | Azure Blob Storage | Azure | Account `medbencodingf946de69`, container `prototype-docs`, Standard LRS, Central US, public access off | Stores the downloaded documents, answer key and manifest |
| 1. Ingest | Azure Document Intelligence | Azure | Resource `medbencoding-ai` (Azure AI Services, S0, East US 2), `prebuilt-read` model, API `2024-11-30` | Reads the text of every document, digital or scanned |
| 1. Ingest | None | Local code | | Document classification and section splitting are rule-based |
| 2. Extract | Azure OpenAI | Azure | Resource `medbencoding-ai`, deployment `extract`, model `gpt-5-mini` version `2025-08-07`, Global Standard, API `2024-10-21`, called through the `openai` Python SDK | Structured extraction of the 22 fields with quotes and confidence |
| 2. Extract | None | Local code | | Citation check and review flag |
| 3. Map | Azure Table Storage | Azure | Account `medbencodingf946de69`, table `codelibrary` (716 codes) | Code library lookup |
| 3. Map | Azure Table Storage | Azure | Account `medbencodingf946de69`, table `codedplans` (one row per plan and field) | Stores the codes assigned to each plan; queried for same-insurer suggestions |
| 3. Map | None | Local code | | The mapping rules themselves |
| 4. Validate | Azure OpenAI | Azure | Resource `medbencoding-ai`, deployment `extract` (`gpt-5-mini`); same model as extraction | LLM judge: audits every extracted value against the document |
| 4. Validate | None | Local code | | SBC reconciliation, consistency rules, test-claim calculator |
| 5. Review | Azure App Service | Azure | Web app `medbencoding-review-f946de69`, plan `medbencoding-plan` (Linux, B1, Central US), Python 3.12, gunicorn | Hosts the Flask review screen |
| 5. Review | Azure Table Storage | Azure | Account `medbencodingf946de69`, tables `reviewdecisions` and `audittrail` | Reviewer decisions and the audit trail |
| 5. Review | Azure Blob Storage | Azure | Container `prototype-docs`, `output/` prefix | The review screen reads pipeline outputs from here |
| Scoring | None | Local code | Answer key in `data/golden/` | Accuracy report |

Supporting tools:

| Tool | Used for |
| --- | --- |
| Azure CLI (`az`) | Creating the resources; uploading documents to Blob Storage with `--upload` |
| `curl` | Downloading the public documents |
| GitHub | Source repository; documents and outputs are not stored there |
| `pytest` | Unit tests; they make no network calls (mapping tests read the seed CSV) |

Notes:

- **Authentication:** the pipeline uses the AI resource's key and the storage account's connection string from the git-ignored `.env` file. Blob uploads use the logged-in Azure CLI account.
- **What leaves the machine:** step 1 sends each PDF to Document Intelligence; steps 2 and 4 send the text of the SBC sections to Azure OpenAI; outputs, codes and decisions are stored in the storage account. All of it is public plan data.
- **Access to the review app:** the whole site is behind one shared password. Only a hash of it is stored, in the web app setting `REVIEW_PASSWORD_HASH`; it is not in this repository. The reviewer name is whatever the signed-in visitor types.
- **Cost:** the App Service plan (B1) is the only resource with a fixed monthly charge; it can be scaled down or stopped between demos. Storage and both AI services are pay-per-use with no idle charge. A full 25-plan run reads about 200 pages through Document Intelligence (billed per page), uses about 100k input and 160k output tokens, and makes a few hundred table operations.
- **Separate from HCM-Agent:** none of these resources are shared with the `clara-rg` resource group.

## Step 1: Ingest ([`ingest.py`](../benefit_coding/ingest.py), [`ocr.py`](../benefit_coding/ocr.py))

- **Read:** every PDF is sent to Azure Document Intelligence (`prebuilt-read`), which returns the text of each page. Digital and scanned documents take the same path.
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

The code library is a lookup table of `field, type, value, system_code`, held in the Azure Table Storage table `codelibrary`. It is a placeholder: 716 invented codes such as `PCP-CP0030` (PCP visit, $30 copay) that each client would replace with its own table. The CSV in the repository is the seed file; `python -m benefit_coding seed-codes` loads it into the table.

- Deductibles and out-of-pocket limits map to an accumulator code with the dollar amount as a parameter.
- Cost shares map to one code per component, so "$250 copay then 20%" gives two codes.
- A value the table does not hold (for example a $120 copay) is left **unmapped** and sent to review with suggestions: the nearest values in the table, and codes that already-coded plans from the same insurer used for that field.
- Each plan's result is written to the `codedplans` table (and to `./output/coded` for inspection). The same-insurer suggestions are a query on that table.

## Step 4: Validate ([`validate.py`](../benefit_coding/validate.py), [`judge.py`](../benefit_coding/judge.py))

Every coded plan goes through four kinds of check. A plan with any failed check is **blocked**: it cannot be approved until a reviewer has approved or edited every flagged field.

| Check | What it does | On a problem |
| --- | --- | --- |
| SBC reconciliation | The coded dollar and percent figures must appear in the passage cited from the SBC | Fail |
| Citation | The cited passage must exist in the document | Fail |
| Code mapping | Every value must have a system code | Fail |
| Consistency | Family amounts are not below individual amounts; the out-of-pocket limit is not below the deductible | Fail |
| ACA limit | In-network out-of-pocket limits above the 2026 federal maximum | Warning |
| Test claims | Eight scenarios must be priceable from the coded values | Fail |
| LLM judge | A second model call reads the document and rules each value supported, not supported or unclear | Fail / warning |

- **Test claims:** preventive visit, primary care, specialist, emergency room, MRI, hospital stay, generic drug and specialty drug. Each is priced as the first claim of the year: deductible if it applies, then copay, then coinsurance, capped at the out-of-pocket limit. The allowed amounts are illustrative round numbers, and nothing checks the results against a real claims system.
- **LLM judge:** one call per plan with the same document sections and rules the extractor saw. It runs on the same model as extraction, because no other model had quota on this subscription.
- **Seeded mismatch:** `seed-mismatch` copies a plan as `<plan>-SEEDED` and changes its specialist copay without touching the citation, to show the checks catching a value that disagrees with the SBC.

### How well step 4 catches errors

From the [validation report](validation-report.md), measured against the CMS published values:

| Measure | Result |
| --- | --- |
| Seeded mismatch caught | Yes, by SBC reconciliation and by the judge |
| Real wrong fields (13) flagged by the judge | 0 of 13 |
| Real wrong fields sent to review for any reason | 5 of 13 |
| Correct fields the judge questioned | 28 of 487 |
| Plans blocked by at least one failed check | 17 of 25 |

The judge did not catch any of the 13 real extraction errors. They are all drug-tier values read from the wrong column of a multi-column table, and the judge reads the same text and makes the same reading. What it does flag is mostly reasonable but different: for example "preauthorization may be required" coded as required. The deterministic reconciliation check is what reliably catches a value that disagrees with its citation.

## Step 5: Review ([`app.py`](../app.py), [`review.py`](../benefit_coding/review.py))

Live at <https://medbencoding-review-f946de69.azurewebsites.net>.

- **Plan list:** every validated plan with its failed checks, fields to review, decisions so far and status.
- **Plan page:** the source document on the left and the proposed fields and codes on the right, flagged fields first. "Show source" opens the cited page with the quoted passage highlighted. Each field shows its value, code, confidence, judge verdict and the reasons it was flagged.
- **Decisions:** approve, edit (corrected value or code) or reject per field, with an optional note. "Approve plan" stays disabled until every flagged field is approved or edited; the server enforces the same rule.
- **Audit trail:** every action is appended to the `audittrail` table with the AI's value and code, the correction, the reviewer name and a UTC timestamp, and is listed at the bottom of the plan page.
- **Also shown:** the automated checks and the eight test claims with how each was priced.

Deploying a new version:

```bash
git archive --format=zip -o review-app.zip HEAD app.py requirements.txt benefit_coding templates static
```

```bash
az webapp deploy -n medbencoding-review-f946de69 -g medical-benefit-coding-rg --src-path review-app.zip --type zip
```

The web app needs these settings: `AZURE_STORAGE_CONNECTION_STRING`; `REVIEW_PASSWORD_HASH` (a werkzeug hash of the shared password; without it nobody can sign in); `FLASK_SECRET_KEY` (a random string that signs the session cookie); and `SCM_DO_BUILD_DURING_DEPLOYMENT=true` so dependencies install on deploy.

## Results

Latest run (one end-to-end run on the 25 pinned plans, with step 1 on Azure Document Intelligence and step 3 on Azure Table Storage), scored against the values CMS publishes for each plan. Full detail is in the [accuracy report](accuracy-report.md).

| Measure | Result | Approval target |
| --- | --- | --- |
| Field accuracy, simple plans | 99.0% | 90%+ |
| Field accuracy, moderate plans | 95.0% | 80%+ |
| Field accuracy, all plans | 97.4% (487 of 500) | |
| Extracted values with a verified citation | 494 of 494 | 100% |
| Wrong fields that were flagged for review | 5 of 13 | |
| Fields mapped to a code | 484 of 550 | |
| Fields left unmapped (value not in the code table) | 10 | |
| Fields not stated in the SBC | 56 | |
| Fields sent to review | 102 of 550, between 0 and 11 per plan | |

How to read these numbers:

- **Accuracy is lower than with the local PDF reader.** The previous run, which read digital PDFs with a local text reader that has since been removed, scored 99.2% (99.7% simple, 98.5% moderate). All 13 misses in this run are drug-tier fields in multi-column tables (Mountain Health and Anthem). Document Intelligence returns table text in a different order, and the extraction rules were tuned on the earlier text; they have not been re-tuned, because this configuration was run once.
- **The extraction rules were tuned on these same 25 plans** using the local reader. The first untuned run scored 96.2%.
- **Unseen plans** were only measured with the local reader: ten other small-group plans scored 99.5% (199 of 200). They come from the same four insurers and were not re-run in this configuration.
- **Results vary slightly between runs.** The model is not deterministic; with the local reader, runs ranged from 99.2% to 100%.
- **The answer key is the insurer's filed cost sharing, not claims-system codes.** Extraction is scored; code mapping is only checked by unit tests because the code table is invented.
- **The "not stated" fields** are mostly the prior-authorization flags, which many SBCs do not mention, and are not scored.

## Not covered yet

- Only SBCs are extracted. Brochures are classified but not used.
- Scanned documents were checked on one image-only copy of an SBC through ingest only; extraction accuracy on scans is not measured. The script that made that copy has been removed.
- The review app has a single shared password rather than individual accounts, no limit on sign-in attempts, no work queue and no roles, and edits are free text: a corrected value is recorded in the audit trail but does not re-run mapping or validation.
- Review time and coder verdict are not measured; no benefit coder has used the screen.
- Parity and state-mandate checks, and the claims-system load (step 6), are production-phase work.
