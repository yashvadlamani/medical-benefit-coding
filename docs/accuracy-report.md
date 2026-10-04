# Extraction accuracy report

Scored 500 fields across 25 plans against the values published in the CMS Exchange Public Use Files (plan year 2026). The two prior-authorization flags have no published value and are not scored.

## Summary

| Measure | Result |
| --- | --- |
| Field accuracy, all plans | 99.2% |
| Field accuracy, simple plans | 99.7% |
| Field accuracy, moderate plans | 98.5% |
| Extracted values with a citation found in the document | 503 of 503 |
| Plans with every scored field correct | 22 of 25 |
| Wrong fields that were flagged for review | 3 of 4 |

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
| outpatient_surgery_facility | 24 of 25 | 96.0% |
| imaging | 25 of 25 | 100.0% |
| rx_tier1_generic | 24 of 25 | 96.0% |
| rx_tier2_preferred_brand | 23 of 25 | 92.0% |
| rx_tier3_nonpreferred_brand | 25 of 25 | 100.0% |
| rx_tier4_specialty | 25 of 25 | 100.0% |

## Accuracy by plan

| Plan | Complexity | Correct | Accuracy |
| --- | --- | --- | --- |
| 32225MT0070004 | moderate | 20 of 20 | 100.0% |
| 32225MT0070006 | moderate | 20 of 20 | 100.0% |
| 32225MT0140001 | simple | 20 of 20 | 100.0% |
| 32225MT0140002 | simple | 20 of 20 | 100.0% |
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
| 46944AL0430001 | simple | 19 of 20 | 95.0% |
| 57601NH0350005 | moderate | 20 of 20 | 100.0% |
| 57601NH0350016 | moderate | 19 of 20 | 95.0% |
| 96751NH0160016 | moderate | 18 of 20 | 90.0% |
| 96751NH0160037 | moderate | 20 of 20 | 100.0% |

## Mismatches

| Plan | Field | Published value | Extracted | Confidence | Cited passage |
| --- | --- | --- | --- | --- | --- |
| 46944AL0430001 | rx_tier2_preferred_brand | no charge | $35 copay | 0.70 | Tier 2 Drugs $35 copay (retail) Deductible does not apply |
| 57601NH0350016 | outpatient_surgery_facility | $500 copay | $500 copay + 20% | 0.60 | Facility fee (e.g., ambulatory surgery center) ... $500/visit 20% coinsurance |
| 96751NH0160016 | rx_tier1_generic | $20 copay | $30 copay | 0.70 | Typically Generic (Tier 1b) $30/prescription, deductible does not apply (retail only) |
| 96751NH0160016 | rx_tier2_preferred_brand | $60 copay | $70 copay | 0.90 | Typically Preferred Brand & Non-Preferred Generic Drugs (Tier 2) ... $70/prescription, ded |
