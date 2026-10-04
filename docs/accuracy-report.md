# Extraction accuracy report

Scored 500 fields across 25 plans against the values published in the CMS Exchange Public Use Files (plan year 2026). The two prior-authorization flags have no published value and are not scored.

## Summary

| Measure | Result |
| --- | --- |
| Field accuracy, all plans | 97.4% |
| Field accuracy, simple plans | 99.0% |
| Field accuracy, moderate plans | 95.0% |
| Extracted values with a citation found in the document | 494 of 494 |
| Plans with every scored field correct | 19 of 25 |
| Wrong fields that were flagged for review | 5 of 13 |

## Accuracy by field

| Field | Correct | Accuracy |
| --- | --- | --- |
| deductible_individual_in | 25 of 25 | 100.0% |
| deductible_family_in | 25 of 25 | 100.0% |
| deductible_individual_oon | 25 of 25 | 100.0% |
| deductible_family_oon | 25 of 25 | 100.0% |
| oop_max_individual_in | 25 of 25 | 100.0% |
| oop_max_family_in | 25 of 25 | 100.0% |
| oop_max_individual_oon | 25 of 25 | 100.0% |
| oop_max_family_oon | 25 of 25 | 100.0% |
| pcp_visit | 25 of 25 | 100.0% |
| specialist_visit | 25 of 25 | 100.0% |
| preventive_care | 25 of 25 | 100.0% |
| emergency_room | 25 of 25 | 100.0% |
| urgent_care | 25 of 25 | 100.0% |
| inpatient_facility | 25 of 25 | 100.0% |
| outpatient_surgery_facility | 25 of 25 | 100.0% |
| imaging | 25 of 25 | 100.0% |
| rx_tier1_generic | 24 of 25 | 96.0% |
| rx_tier2_preferred_brand | 23 of 25 | 92.0% |
| rx_tier3_nonpreferred_brand | 20 of 25 | 80.0% |
| rx_tier4_specialty | 20 of 25 | 80.0% |

## Accuracy by plan

| Plan | Complexity | Correct | Accuracy |
| --- | --- | --- | --- |
| 32225MT0070004 | moderate | 20 of 20 | 100.0% |
| 32225MT0070006 | moderate | 20 of 20 | 100.0% |
| 32225MT0140001 | simple | 18 of 20 | 90.0% |
| 32225MT0140002 | simple | 19 of 20 | 95.0% |
| 32225MT0140003 | simple | 20 of 20 | 100.0% |
| 32225MT0160001 | simple | 20 of 20 | 100.0% |
| 32225MT0160002 | simple | 20 of 20 | 100.0% |
| 32225MT0160006 | simple | 20 of 20 | 100.0% |
| 38166WI0140001 | simple | 20 of 20 | 100.0% |
| 38166WI0140004 | simple | 20 of 20 | 100.0% |
| 38166WI0140011 | simple | 20 of 20 | 100.0% |
| 38166WI0140033 | moderate | 20 of 20 | 100.0% |
| 38166WI0140037 | moderate | 20 of 20 | 100.0% |
| 38166WI0140040 | simple | 20 of 20 | 100.0% |
| 38166WI0140044 | simple | 20 of 20 | 100.0% |
| 38166WI0150001 | simple | 20 of 20 | 100.0% |
| 38166WI0150044 | simple | 20 of 20 | 100.0% |
| 46944AL0280001 | simple | 20 of 20 | 100.0% |
| 46944AL0340001 | moderate | 20 of 20 | 100.0% |
| 46944AL0380001 | moderate | 20 of 20 | 100.0% |
| 46944AL0430001 | simple | 20 of 20 | 100.0% |
| 57601NH0350005 | moderate | 17 of 20 | 85.0% |
| 57601NH0350016 | moderate | 19 of 20 | 95.0% |
| 96751NH0160016 | moderate | 16 of 20 | 80.0% |
| 96751NH0160037 | moderate | 18 of 20 | 90.0% |

## Mismatches

| Plan | Field | Published value | Extracted | Confidence | Cited passage |
| --- | --- | --- | --- | --- | --- |
| 32225MT0140001 | rx_tier3_nonpreferred_brand | $200 copay | $200 copay + 50% | 0.70 | Non-preferred brand drugs ... Retail: $200 copayment/prescription, 50% coinsurance |
| 32225MT0140001 | rx_tier4_specialty | $250 copay | $250 copay + 50% | 0.90 | Specialty drugs ... $250 copayment/prescription, deductible does not apply, 50% coinsuranc |
| 32225MT0140002 | rx_tier3_nonpreferred_brand | $250 copay | $250 copay + 60% | 0.70 | Non-preferred brand drugs Retail: $250 copayment/prescription, 60% coinsurance |
| 57601NH0350005 | rx_tier2_preferred_brand | $60 copay | $70 copay | 0.90 | Typically Preferred Brand & Non-Preferred Generic Drugs (Tier 2) $70/prescription, Prescri |
| 57601NH0350005 | rx_tier3_nonpreferred_brand | 30% | $60 copay | 0.80 | Typically Non-Preferred Brand and Generic drugs (Tier 3) $60/prescription, Prescription Dr |
| 57601NH0350005 | rx_tier4_specialty | 40% | 50% | 0.80 | Typically Preferred Specialty (brand and generic) (Tier 4) 50% coinsurance up to $650/pres |
| 57601NH0350016 | rx_tier4_specialty | 40% | 50% | 0.90 | Typically Preferred Specialty (brand and generic) (Tier 4) 50% coinsurance up to $650/pres |
| 96751NH0160016 | rx_tier1_generic | $20 copay | $30 copay | 0.70 | Typically Generic (Tier 1b) ... $30/prescription, deductible does not apply (retail only) |
| 96751NH0160016 | rx_tier2_preferred_brand | $60 copay | $70 copay | 0.85 | Typically Preferred Brand & Non-Preferred Generic Drugs (Tier 2) ... $70/prescription, ded |
| 96751NH0160016 | rx_tier3_nonpreferred_brand | 30% | 40% | 0.70 | Typically Non-Preferred Brand and Generic drugs (Tier 3) ... 40% coinsurance up to $550/pr |
| 96751NH0160016 | rx_tier4_specialty | 40% | 50% | 0.70 | Typically Preferred Specialty (brand and generic) (Tier 4) ... 50% coinsurance up to $650/ |
| 96751NH0160037 | rx_tier3_nonpreferred_brand | 30% | 40% | 0.90 | Typically Non-Preferred Brand and Generic drugs (Tier 3) 40% coinsurance up to $500/prescr |
| 96751NH0160037 | rx_tier4_specialty | 40% | 50% | 0.90 | Typically Preferred Specialty (brand and generic) (Tier 4) 50% coinsurance up to $650/pres |
