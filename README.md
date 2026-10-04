# Automated Medical Benefit Coding

AI-assisted benefit coding for health insurance benefit operations: an AI pipeline reads plan documents, extracts cost-sharing rules with source citations, maps them to claims-system codes, validates them automatically, and hands a coder a ready-to-approve plan.

**AI drafts and humans decide.** Nothing loads to the claims system without passing automated checks and a coder's approval.

## Problem

Benefit coders translate each sold plan (SBC, SPD, benefit grid, riders) into claims-system parameters by hand. The process is slow at peak enrollment, depends on scarce experts, and causes payment errors when codes don't match what sales promised.

## Solution

A six-stage pipeline that turns plan documents into proposed benefit codes, each traceable to its source sentence, with a human approving everything that loads.

Targets for the production release:

- Review time for a standard plan under 15 minutes, versus hours today
- First-pass field accuracy of 90%+ on standard medical plans
- Every coded value traceable to its source sentence, with a full audit trail
- No increase in coding-related claim adjustments

## Timeline

| Phase | Duration | Outcome |
| --- | --- | --- |
| Phase 1: Prototype | 4 weeks | Live demo and scorecard; go/no-go decision |
| Phase 2: Production build | ~8 weeks after approval | Go-live on the first line of business |
| Total | ~3 months | Kickoff to production launch |

## Status

Pipeline steps 1 to 3 (ingest, AI extraction, code mapping) are implemented in `benefit_coding/` and run on 25 public small-group plans. Steps 4 to 6 (validation, review screen, claims-system load) are not built yet. See [Pipeline](docs/pipeline.md) to run it.

## Services

| Service | Used for |
| --- | --- |
| Azure Blob Storage | Storing the public plan documents and answer key |
| Azure Document Intelligence | OCR for scanned documents (step 1) |
| Azure OpenAI (`gpt-5-mini`) | Benefit extraction (step 2) |
| CMS Exchange Public Use Files and insurer websites | Public source documents and published values |

Step 3 (code mapping) and scoring run locally with no external service. Details are in [Pipeline](docs/pipeline.md#services-used).

## Documentation

| Document | Contents |
| --- | --- |
| [Architecture](docs/architecture.md) | The six-stage coding pipeline and learning loop |
| [Implementation plan](docs/implementation-plan.md) | Business case, delivery plan, prototype and production phases, compliance, testing, success metrics, risks, rollout, approvals, glossary |
| [Pipeline](docs/pipeline.md) | How steps 1 to 3 (ingest, extract, map) work, the Azure and external services each step uses, how to run them, and results |
| [Accuracy report](docs/accuracy-report.md) | Field-by-field extraction accuracy on the 25 prototype plans |
| [Data sources](docs/data-sources.md) | Public documents used by the prototype, where they are stored, and how to re-download them |

## License

Copyright (c) 2026 Repository Owner. All rights reserved. See [LICENSE](LICENSE).
