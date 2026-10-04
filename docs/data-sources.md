# Prototype data sources

The prototype runs on public documents only. They are downloaded by [`ingest/download_public_docs.py`](../ingest/download_public_docs.py) and stored in Azure Blob Storage, not in this repository.

## Where the documents live

| | |
| --- | --- |
| Resource group | `medical-benefit-coding-rg` (Central US) |
| Storage account | `medbencodingf946de69` (Standard LRS, public access disabled) |
| Container | `prototype-docs` |
| Tables | `codelibrary`, `codedplans` (step 3); `reviewdecisions`, `audittrail` (step 5) |

The same resource group also holds the Azure AI Services resource used by the pipeline; see [Services used](pipeline.md#services-used) for the full list of Azure and external services.

## Folder structure

```
prototype-docs/
├── manifest.csv                      one row per file: source URL, size, SHA-256, plan metadata
├── raw/                              files exactly as published
│   ├── cms-puf/2026/                 CMS Exchange Public Use Files (zip)
│   ├── sbc/2026/<state>-<insurer>/   <plan id>_sbc.pdf, one per plan
│   └── plan-brochures/2026/<state>-<insurer>/
├── golden/2026/                      answer key for the 25 plans
│   ├── selected-plans.csv            the 25 plans, complexity, and SBC path
│   ├── plan-attributes.csv           deductibles, OOP maximums, SBC coverage examples
│   └── benefits-and-cost-sharing.csv copay and coinsurance per benefit
└── reference/
    ├── cms-puf-data-dictionaries/    column definitions for the two Public Use Files
    ├── sbc-template/                 CMS sample completed SBC
    └── av-calculator/                2026 Actuarial Value Calculator methodology
```

## What was collected

| Pipeline step | Content | Files | Source |
| --- | --- | --- | --- |
| 1. Ingest | SBC PDFs for 25 small-group plans | 25 | Insurer sites, linked from the CMS Plan Attributes file |
| 1. Ingest | Plan brochures and outlines of coverage | 10 | Insurer sites, linked from the CMS Plan Attributes file |
| 2. Extract | Published cost-sharing values (answer key) | 2 zips, 3 CSV subsets | CMS Exchange Public Use Files, plan year 2026 |
| 4. Validate | Coverage example amounts per plan | in `plan-attributes.csv` | CMS Plan Attributes file (`SBCHaving...` columns) |
| 4. Validate | Actuarial value methodology | 1 | CMS |
| Reference | Data dictionaries, sample completed SBC | 3 | CMS |

## The 25 plans

Pinned in [`ingest/plans.csv`](../ingest/plans.csv). All are 2026 small-group (SHOP) medical plans on the federal exchange.

| Insurer | State | Simple | Moderate |
| --- | --- | --- | --- |
| Blue Cross and Blue Shield of Alabama | AL | 2 | 2 |
| Mountain Health CO-OP | MT | 6 | 2 |
| Anthem Blue Cross and Blue Shield (PPO and HMO entities) | NH | 0 | 4 |
| Security Health Plan | WI | 7 | 2 |
| **Total** | | **15** | **10** |

- **Simple:** one in-network tier and not HSA-eligible.
- **Moderate:** multiple in-network tiers or HSA-eligible (high-deductible) design.

These four insurers are the only ones offering small-group medical plans in the 2026 federal exchange files.

## Not yet collected

- **Federal employee plan brochures (OPM)** and **state exchange benefit grids** (for example Covered California): no stable download links were found. To be added by hand for the long-document and grid cases.
- **Riders and scanned documents:** not published anywhere. To be created synthetically in prototype week 4.
- **Code system:** the placeholder code table is built in the mapping step, not downloaded.

## Known issues with the public links

- Most Anthem SBC links in the CMS file return "document not found". The four Anthem plans in the set are ones whose links work.
- Blue Cross and Blue Shield of Alabama links use a mixed-case host name that fails in curl; the script lower-cases the host.

## Re-running

```bash
python ingest/download_public_docs.py --upload
```

Requires `curl` and a logged-in Azure CLI. Files already in `./data` are not downloaded again. `./data` is git-ignored.
