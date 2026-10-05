# Implementation Plan: Prototype to Production

AI-assisted benefit coding for health insurance benefit operations: an AI pipeline reads plan documents, extracts cost-sharing rules with source citations, maps them to claims-system codes, validates them automatically, and hands a coder a ready-to-approve plan.

**AI drafts and humans decide.** Nothing loads to the claims system without passing automated checks and a coder's approval.

| Phase | Duration | Outcome |
| --- | --- | --- |
| Phase 1: Prototype | 4 weeks | Live demo and scorecard; go/no-go decision |
| Phase 2: Production build | ~8 weeks after approval | Go-live on the first line of business |
| Total | ~3 months | Kickoff to production launch |

The six-stage pipeline is described in [architecture.md](architecture.md).

## Who it is for

The tool is built for the **sales team**, to get a sold account's plans set up correctly and on time.

| User | What they need | What the tool gives them |
| --- | --- | --- |
| Sales rep / account manager | To know whether each account's plans will be ready by the effective date, and to talk about the plan with the account accurately | An account list with setup status, days to the effective date and open items; a plain-language summary of each plan with what members would pay |
| Benefit coder on the sales team | To turn each sold plan into system codes without re-keying the documents | A drafted, cited and pre-checked setup per plan to approve, edit or reject |
| Sales lead | To see which accounts are at risk of a late or wrong setup | The same account list, ordered by what is not ready and soonest effective date |

Everything is organised as **account → plans sold to it → fields of each plan**. An account is ready when every one of its plans is approved.


## Contents

- [Who it is for](#who-it-is-for)
- [Business case](#business-case)
- [Delivery plan](#delivery-plan)
- [Phase 1: Prototype (weeks 1 to 4)](#phase-1-prototype-weeks-1-to-4)
- [Phase 2: Production build (about 8 weeks)](#phase-2-production-build-about-8-weeks)
- [Compliance and security](#compliance-and-security)
- [Testing and quality assurance](#testing-and-quality-assurance)
- [Success metrics](#success-metrics)
- [Risks and mitigations](#risks-and-mitigations)
- [Rollout and adoption](#rollout-and-adoption)
- [Approvals and support needed](#approvals-and-support-needed)
- [Glossary](#glossary)

## Business case

Manual coding is the bottleneck between a signed sale and a correctly paying plan, and the sales team owns that gap. The prototype measures how much of it AI can remove.

| Pain point | Impact today | What the product changes |
| --- | --- | --- |
| Manual re-keying of plan documents | Hours per group, missed effective dates | AI drafts every field; coder reviews |
| Peak-season backlog | Overtime, contractors, late ID cards | Same coders handle more groups |
| Coding errors | Claim reprocessing, penalties, complaints | Automated SBC and test-claim checks before load |
| Inconsistent interpretation | Same benefit coded differently | One rules library applied every time |
| Sales promises not reflected in system | Post-sale disputes, renewal churn | Mismatches flagged before go-live |
| Reps cannot see setup progress | Status chased by email; late surprises near the effective date | Account view with status, open items and days to the effective date |
| Reps restate benefits from memory or the PDF | Inconsistent answers to the account | Plain-language plan summary drawn from the same coded values |

### Value model

To be filled in with baseline numbers gathered in week 1 of the prototype:

- **Hours saved** = groups per year × hours per group today × share of work automated
- **Error savings** = coding-related adjustments per year × cost per adjustment × reduction
- **Revenue timing** = earlier effective dates on new groups
- **Sales time** = hours reps spend chasing setup status and answering benefit questions per account

Because the build is lean (about 3 months end to end), the main costs are LLM usage, hosting, and coder review time for validation.

## Delivery plan

| Phase | When | Focus |
| --- | --- | --- |
| Prototype, week 1 | Weeks 1 to 4 | Data and setup |
| Prototype, week 2 | | AI extraction |
| Prototype, week 3 | | Mapping, checks, UI |
| Prototype, week 4 | | Tune and live demo |
| **Approval gate** | End of week 4 | Demo meets criteria |
| Sprint 1 | Build weeks 1-2 | Secure environment, CI/CD, full code library |
| Sprint 2 | Build weeks 3-4 | Claims-system integration, full benefit set and checks |
| Sprint 3 | Build weeks 5-6 | Review queue, audit trail, learning loop, intake form |
| Sprint 4 | Build weeks 7-8 | Regression, sign-off, UAT, parallel run, go-live |
| **Go-live** | | First line of business, then hypercare |

The approval gate is the only decision point. If the demo misses its criteria, the scorecard shows which fields need work before the build is reconsidered.

## Phase 1: Prototype (weeks 1 to 4)

The prototype shows AI turning 25 real, publicly available plan documents into proposed benefit codes, with citations, a review screen, and simulated claim outcomes. It ends in a go/no-go demo.

No client documents or system codes are available yet, so every prototype step runs on public sources. Client data replaces them in Phase 2 without changing the pipeline.

### Scope

- 25 small-group (SHOP) medical plans from the federal exchange, each with a public SBC and published cost-sharing values to score against (15 simple, 10 moderate), drawn from several insurers
- About 20 fields per plan: in- and out-of-network deductibles and OOP max, PCP and specialist copays, preventive, ER, urgent care, inpatient, outpatient surgery, imaging, Rx tiers 1 to 4, prior auth flags
- Public plan documents only: no member PHI and no client data, so no BAA is needed until client documents are introduced
- **Out of scope:** live claims-system integration, client code libraries, custom plans, dental and vision

### Public data sources

| Pipeline step | What the prototype needs | Public source |
| --- | --- | --- |
| 1. Ingest | SBC documents | SBC PDFs published by insurers, linked from the CMS Exchange Plan Attributes Public Use File |
| 1. Ingest | Long SPD-style documents | Federal employee plan brochures (OPM); state employee and public university plan documents |
| 1. Ingest | Benefit grids | State exchange standard benefit designs (for example Covered California) |
| 1. Ingest | Riders and scanned documents | Not published: synthetic riders written against a real plan, and real SBCs degraded into scan-like images |
| 2. Extract | Verified values to score against | CMS Exchange Benefits and Cost Sharing and Plan Attributes Public Use Files (copays, coinsurance, deductibles, OOP maximums per plan) |
| 3. Map | Target code system | A placeholder code table built on public benefit categories: X12 service type codes or the CMS plans-and-benefits template fields |
| 4. Validate | SBC reconciliation | Coded values compared with the same public SBC; mismatches seeded by altering one value in a copy |
| 4. Validate | Expected test-claim results | The Coverage Examples printed on every SBC (having a baby, managing type 2 diabetes, simple fracture) |
| 4. Validate | Plausibility check | CMS Actuarial Value Calculator |
| 5. Review | Reviewers and baseline time | Not public: internal reviewers time themselves coding a plan by hand from the SBC, then with the tool |

Limits of public data, to state openly in the pitch:

- Published values are the insurer's filed cost sharing, not a client's claims-system codes. The code table is a stand-in each client replaces with its own.
- Public SBCs are clean digital PDFs. OCR handling is shown on degraded copies, not on real broker scans.
- Review-time and "would use it daily" results come from internal reviewers until client coders take part.
- Exchange file layouts and SBC links change yearly and must be confirmed in week 1.

### Prototype stack

- Enterprise LLM with structured JSON output for extraction
- Python service for parsing, OCR, extraction, and code mapping
- Code library as a simple lookup table (field, value, system code), filled with placeholder codes based on public benefit categories
- Lightweight web workspace for the sales team: accounts and their sold plans with setup status, a plain-language summary of each plan, and a review screen with the source document beside proposed fields and codes
- Fictional accounts grouping the public plans, since no real account data is used
- Rules-based cost calculator standing in for the claims system, pricing 8 claim scenarios per plan and checked against the SBC Coverage Examples

### Weekly plan

| Week | Focus | Deliverable |
| --- | --- | --- |
| 1 | Data and setup | Exchange Public Use Files downloaded and SBC links confirmed; 25 plans selected and their SBCs collected; golden dataset built from the published values; field list and placeholder code table agreed; manual baseline review time measured |
| 2 | Extraction | All fields extracted from the public SBCs with citations and confidence; first accuracy report against the published values |
| 3 | Mapping, checks, review screen | Fields mapped to placeholder codes; SBC reconciliation working; claim calculator matching the SBC Coverage Examples; review screen usable |
| 4 | Tune and demo | Misses fixed; synthetic rider and scanned-copy cases added; final scorecard; reviewers time their reviews; live demo |

### Demo script (20 minutes)

1. Open the account list as a sales rep: which accounts are ready, which are not, and how close each effective date is. Open one account and its plan summary.
2. Upload a public SBC the system has never seen, from an insurer outside the 25-plan set.
3. Fields populate, each with a confidence score and its highlighted source sentence.
4. Low-confidence fields are flagged, and a seeded SBC mismatch is caught.
5. A coder edits one field and approves; the audit trail records the change, and the account moves to "Ready to load".
6. Test claims (preventive, specialist, ER, MRI, generic and specialty Rx) show member cost for each, alongside the SBC's own Coverage Examples.
7. Close on the scorecard: accuracy by field, review time versus today, plans needing no edits.

### Approval criteria for Phase 2

| Measure | Target |
| --- | --- |
| Field accuracy, simple plans | 90%+ |
| Field accuracy, moderate plans | 80%+ |
| Fields with a valid source citation | 100% |
| Review time per simple plan | Under 15 minutes |
| Seeded SBC mismatches caught | All |
| Coder verdict | Majority would use it daily |

Accuracy is scored against the published exchange values. Review time and coder verdict come from internal reviewers during the prototype and are re-measured with client coders once a client takes part.

## Phase 2: Production build (about 8 weeks)

Phase 2 turns the prototype into a secure, integrated product in four 2-week sprints, ending with go-live on the first line of business.

| Sprint | Weeks | Focus | Done when |
| --- | --- | --- | --- |
| 1 | 1-2 | Production foundations | Secure environment with SSO, encryption, logging, CI/CD; prototype refactored into services; full code library loaded |
| 2 | 3-4 | Claims integration and full benefit set | Codes load to the claims test region by API or load file; full medical and Rx benefit set covered; parity and state-mandate checks live |
| 3 | 5-6 | Reviewer workflow and learning loop | Work queue, approvals, audit trail, and reporting dashboard; reviewer corrections captured to improve accuracy; standard intake form for sales |
| 4 | 7-8 | Hardening and launch | Regression suite on a 200-plan golden set; security and compliance sign-off; coder UAT and parallel run; go-live and hypercare |

### Production-ready checklist

- [ ] Runs in the firm's approved cloud with SSO and role-based access
- [ ] BAA in place with the LLM provider; no data retained for model training
- [ ] Model and prompt versions pinned; changes go through regression tests
- [ ] Every coded field stores source passage, confidence, reviewer, and timestamp
- [ ] Automated SBC reconciliation and test claims block bad loads
- [ ] Monitoring and alerts for errors, latency, and accuracy drift
- [ ] Runbook, fallback to manual coding, and support process documented
- [ ] Coders trained; two-week parallel run passed before cutover

> **Timing note:** Go-live should avoid the October to January enrollment peak. If approval lands late, launch on off-cycle groups first.

## Compliance and security

The prototype avoids member PHI entirely. The production build adds the controls needed to pass HIPAA and model-risk review before go-live.

| Requirement | Prototype | Production |
| --- | --- | --- |
| HIPAA | Public plan documents only, no PHI or client data; BAA required before any client document is used | Encryption at rest and in transit, access logging, minimum necessary access |
| ACA / SBC consistency | SBC reconciliation demonstrated | Mismatch blocks the load |
| Mental health parity (MHPAEA) | Not in scope | Automated cost-sharing comparison |
| State mandates | Not in scope | Rules for situs states of the first LOB |
| AI controls | Citations and confidence per field | Plus pinned versions, regression gates, human approval on every plan |
| Audit and retention | Basic change log | Source, AI output, reviewer decision, final code kept together |
| Model risk | Informal review | Documentation aligned with the firm's model governance policy |

## Testing and quality assurance

A coded plan passes only when test claims pay exactly as the plan document says they should.

1. **Golden dataset.** 25 public exchange plans scored against CMS-published values for the prototype, grown to 200 client-verified plans for production, covering simple and moderate designs. Every change is scored against it.
2. **Field-level accuracy.** Precision and recall per field (deductible, copay, coinsurance, OOP max, prior auth, Rx tiers), not just an overall score.
3. **Test claims.** Standard scenarios per plan (preventive, specialist, ER, MRI, generic and specialty Rx, out-of-network) must produce the expected member cost. In the prototype, the SBC Coverage Examples supply the expected totals.
4. **SBC reconciliation.** Coded values compared to the issued SBC line by line; any mismatch blocks the load.
5. **Parallel run.** For two weeks before cutover, coders code new groups both ways; outputs are compared.
6. **Post-launch audit.** Sample 10% of approved plans monthly and track claim adjustments traced to coding.

## Success metrics

Speed gains count only if accuracy holds. A faster process with more claim adjustments is a failure.

| Metric | Prototype (week 4) | Production launch | 3 months after launch |
| --- | --- | --- | --- |
| First-pass field accuracy | 85%+ overall | 90%+ | 95% |
| Review time per standard plan | Under 15 min | Under 15 min | Under 10 min |
| Plans needing no edits | Measured | 30% | 50% |
| SBC mismatch rate at load | Seeded errors caught | Under 2% | Under 0.5% |
| Coding-related claim adjustments | n/a | No increase | 30% reduction |
| Groups per coder | Baseline | 1.5x | 2x |
| Coder adoption on launch LOB | Positive verdict | 80% of new groups | 95% of new groups |
| Days from sale to approved setup, per account | Not measured (fictional accounts) | Baseline measured | Tracked against baseline |
| Accounts fully set up before their effective date | Not measured | Baseline measured | Tracked against baseline |
| Sales rep adoption of the account view | Positive verdict | Measured | Measured |

## Risks and mitigations

The two biggest risks are a wrong code reaching production and an 8-week build slipping. Scope is kept tight to protect against both.

| Risk | Mitigation |
| --- | --- |
| AI misreads or invents a benefit value | Source citation per field, confidence thresholds, human approval on every plan, test claims before load |
| Claims system has no usable API | Confirm in prototype week 1; fall back to generated load files |
| Tight timeline slips | Fixed scope: one LOB, standard medical plans; anything else moves to a later release |
| Delays waiting on data, SMEs, or approvals | Secure plan samples, coder time, and security review dates before kickoff |
| Messy source documents (scans, broker spreadsheets) | OCR quality check; unreadable documents route to manual coding |
| Coder resistance | Coders validate outputs from week 1 and shape the review screen |
| LLM provider changes model behavior | Pin model versions; rerun regression suite before any upgrade |
| Launch collides with enrollment peak | Go live on off-cycle groups; no cutover October to January |

## Rollout and adoption

The product launches on one line of business, proves itself for a month, then expands.

**Sales reps and account managers**

- Reps see setup status for each sold account and its plans (built in the prototype, on fictional accounts)
- A plain-language summary of each plan supports conversations with the account (built in the prototype)
- Standard digital intake form replaces free-form emails and spreadsheets (production)
- Accounts and effective dates come from the sales system of record instead of being entered by hand (production)
- A later release adds a codeability check at quote stage, flagging benefits the claims system can't support before the proposal goes out

**Benefit coders on the sales team**

- Involved from prototype week 1 as validators of AI output
- Roles shift toward review, exceptions, and QA rather than data entry
- Accuracy dashboards shared openly so trust is earned with data

**Expansion after launch**

Add lines of business one at a time, then complex plans, dental, and vision, each gated by the same accuracy targets.

## Approvals and support needed

To start the prototype:

- [ ] Sponsor approval for the 4-week prototype
- [ ] CMS Exchange Public Use Files downloaded and SBC links confirmed for the 25 selected plans
- [ ] A few hours a week from two reviewers with benefit-coding experience to validate output
- [ ] One or two sales reps to react to the account view and plan summary
- [ ] LLM API access (no BAA needed while only public documents are used)
- [ ] Demo date booked with decision makers for the end of week 4

To start the production build (after the demo):

- [ ] Go decision based on the approval criteria
- [ ] Client plan documents with verified codes, the client's code library, and a HIPAA-eligible LLM environment under a BAA
- [ ] Claims-system test region access and integration contact
- [ ] Security and compliance review dates booked for weeks 6 to 8
- [ ] Launch line of business and go-live window confirmed
- [ ] Access to the sales system that holds accounts, sold plans and effective dates

## Glossary

| Term | Meaning |
| --- | --- |
| SBC | Summary of Benefits and Coverage |
| SHOP | Small Business Health Options Program (small-group exchange plans) |
| Public Use Files | Yearly CMS data files describing every plan on the federal exchange |
| SPD | Summary Plan Description |
| OOP max | Out-of-pocket maximum |
| LOB | Line of business |
| BAA | Business Associate Agreement |
| PHI | Protected health information |
| MHPAEA | Mental Health Parity and Addiction Equity Act |
| UAT | User acceptance testing |
