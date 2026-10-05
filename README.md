# Automated Medical Benefit Coding

AI-assisted benefit coding for a health insurer's sales team: when an account (employer group) is sold, an AI pipeline reads its plan documents, extracts cost-sharing rules with source citations, maps them to claims-system codes, validates them automatically, and hands a benefit coder a ready-to-approve plan. Sales reps see each account's setup status and a plain-language summary of every plan.

**AI drafts and humans decide.** Nothing loads to the claims system without passing automated checks and a coder's approval.

## Who it is for

The tool is built for the **sales team**, to get a sold account's plans set up correctly and on time.

| User | What they need | What the tool gives them |
| --- | --- | --- |
| Sales rep / account manager | To know whether each account's plans will be ready by the effective date, and to talk about the plan with the account accurately | An account list with setup status, days to the effective date and open items; a plain-language summary of each plan with what members would pay |
| Benefit coder on the sales team | To turn each sold plan into system codes without re-keying the documents | A drafted, cited and pre-checked setup per plan to approve, edit or reject |
| Sales lead | To see which accounts are at risk of a late or wrong setup | The same account list, ordered by what is not ready and soonest effective date |

Everything is organised as **account → plans sold to it → fields of each plan**. An account is ready when every one of its plans is approved.

## Problem

After a sale, benefit coders translate each of the account's plans (SBC, SPD, benefit grid, riders) into claims-system parameters by hand. The process is slow at peak enrollment, depends on scarce experts, and causes payment errors when codes don't match what sales promised. Meanwhile the rep has no view of whether the account will be ready by its effective date.

## Solution

A six-stage pipeline that turns an account's plan documents into proposed benefit codes, each traceable to its source sentence, with a human approving everything that loads, and an account view that shows sales where every sold plan stands.

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

A rough first draft of the prototype is complete: pipeline steps 1 to 5 (ingest, AI extraction, code mapping, automated validation with an LLM judge, and a sales workspace with account views and a coding review screen) run on 25 public small-group plans, grouped under 12 fictional accounts. Step 6 (claims-system load) is production-phase work. See [Pipeline](docs/pipeline.md) to run it.

**Live app:** <https://medbencoding-review-f946de69.azurewebsites.net>

## Services

| Service | Used for |
| --- | --- |
| Azure Blob Storage | Storing the public plan documents, answer key and pipeline outputs |
| Azure Document Intelligence | Reading every plan document, digital or scanned (step 1) |
| Azure OpenAI (`gpt-5-mini`) | Benefit extraction (step 2) and the LLM judge (step 4) |
| Azure Table Storage | Code library and the codes assigned to each plan (step 3); reviewer decisions and audit trail (step 5) |
| Azure App Service | Hosting the sales workspace: account views, plan summaries and the coding review screen (step 5) |
| CMS Exchange Public Use Files and insurer websites | Public source documents and published values |

Scoring runs locally with no external service. Details are in [Pipeline](docs/pipeline.md#services-used).

## Documentation

| Document | Contents |
| --- | --- |
| [Architecture](docs/architecture.md) | The six-stage coding pipeline and learning loop |
| [Implementation plan](docs/implementation-plan.md) | Business case, delivery plan, prototype and production phases, compliance, testing, success metrics, risks, rollout, approvals, glossary |
| [Pipeline](docs/pipeline.md) | How steps 1 to 5 work, the Azure and external services each step uses, how to run them, and results |
| [Validation report](docs/validation-report.md) | Step 4 checks and how the LLM judge did against the published values |
| [Accuracy report](docs/accuracy-report.md) | Field-by-field extraction accuracy on the 25 prototype plans |
| [Data sources](docs/data-sources.md) | Public documents used by the prototype, where they are stored, and how to re-download them |

## License

Copyright (c) 2026 Repository Owner. All rights reserved. See [LICENSE](LICENSE).
