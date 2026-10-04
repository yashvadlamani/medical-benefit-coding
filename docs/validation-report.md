# Validation report

Step 4 run on 25 plans. The LLM judge and the automated checks are compared with the values published in the CMS Exchange Public Use Files, which neither of them sees.

## Catching wrong fields

| Measure | Result |
| --- | --- |
| Scored fields | 500 |
| Fields that disagree with the published value | 13 |
| Wrong fields flagged by extraction confidence alone | 5 of 13 |
| Wrong fields flagged by the LLM judge | 0 of 13 |
| Wrong fields sent to review after step 4 (any reason) | 5 of 13 |
| Correct fields the judge questioned (false alarms) | 28 of 487 |
| Correct fields sent to review after step 4 (any reason) | 78 of 487 |
| Plans blocked by at least one failed check | 17 of 25 |

## Checks raised

| Check | Failed | Warnings |
| --- | --- | --- |
| code_mapping | 10 | 0 |
| judge | 37 | 5 |
| test_claim | 4 | 0 |

## Wrong fields and what the judge said

| Plan | Field | Extracted | Judge verdict | Judge reason |
| --- | --- | --- | --- | --- |
| 32225MT0140001 | rx_tier3_nonpreferred_brand | $200 copay + 50% coinsurance | supported | Page 2 shows "Non-preferred brand drugs ... Retail: $200 copayment/prescription, 50% coinsurance". |
| 32225MT0140001 | rx_tier4_specialty | $250 copay + 50% coinsurance, deductible does not apply | supported | Page 3 shows "Specialty drugs ... $250 copayment/prescription, deductible does not apply, 50% coinsurance". |
| 32225MT0140002 | rx_tier3_nonpreferred_brand | $250 copay + 60% coinsurance, after deductible | supported | Non-preferred brand drugs Retail: $250 copayment/prescription, 60% coinsurance (page 2) (no 'deductible does not apply' stated) |
| 57601NH0350005 | rx_tier2_preferred_brand | $70 copay, after deductible | supported | Page 3: 'Typically Preferred Brand & Non-Preferred Generic Drugs (Tier 2) $70/prescription, Prescription Drug deductible applies (retail only)'. |
| 57601NH0350005 | rx_tier3_nonpreferred_brand | $60 copay, after deductible | supported | Page 3: 'Typically Non-Preferred Brand and Generic drugs (Tier 3) $60/prescription, Prescription Drug deductible applies (retail)'. |
| 57601NH0350005 | rx_tier4_specialty | 50% coinsurance, after deductible | supported | Page 3: 'Typically Preferred Specialty (brand and generic) (Tier 4) 50% coinsurance up to $650/prescription' and page 4 indicates the prescription drug deductible applies. |
| 57601NH0350016 | rx_tier4_specialty | 50% coinsurance, deductible does not apply | supported | Page 3 Typically Preferred Specialty (Tier 4) 50% coinsurance up to $650/prescription, deductible does not apply (retail only). |
| 96751NH0160016 | rx_tier1_generic | $30 copay, deductible does not apply | supported | Page 3 shows 'Typically Generic (Tier 1b) ... $30/prescription, deductible does not apply (retail only)'. |
| 96751NH0160016 | rx_tier2_preferred_brand | $70 copay, deductible does not apply | supported | Page 3 shows 'Typically Preferred Brand & Non-Preferred Generic Drugs (Tier 2) ... $70/prescription, deductible does not apply (retail only)'. |
| 96751NH0160016 | rx_tier3_nonpreferred_brand | 40% coinsurance, deductible does not apply | supported | Page 3 shows 'Typically Non-Preferred Brand and Generic drugs (Tier 3) ... 40% coinsurance up to $550/prescription, deductible does not apply (retail and home delivery)'. |
| 96751NH0160016 | rx_tier4_specialty | 50% coinsurance, deductible does not apply | supported | Page 3 shows 'Typically Preferred Specialty (brand and generic) (Tier 4) ... 50% coinsurance up to $650/prescription, deductible does not apply (retail only)'. |
| 96751NH0160037 | rx_tier3_nonpreferred_brand | 40% coinsurance, after deductible | supported | Page 3 shows "Typically Non-Preferred Brand and Generic drugs (Tier 3) 40% coinsurance up to $500/prescription (retail only)". |
| 96751NH0160037 | rx_tier4_specialty | 50% coinsurance, after deductible | supported | Page 3 shows "Typically Preferred Specialty ... (Tier 4) 50% coinsurance up to $650/prescription (retail only)". |

## Seeded mismatch

`38166WI0140040-SEEDED` has its specialist copay deliberately changed. Checks that caught it: sbc_reconciliation ($100 copay does not appear in the cited SBC passage); judge (Page 2 shows "Specialist visit $75 copayment/visit" (not $100).).
