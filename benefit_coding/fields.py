"""The benefit fields the prototype codes for every plan."""
from dataclasses import dataclass

AMOUNT = "amount"          # a dollar accumulator: deductible or out-of-pocket maximum
COST_SHARE = "cost_share"  # what the member pays for a service: copay and/or coinsurance
FLAG = "flag"              # yes/no


@dataclass(frozen=True)
class Field:
    name: str
    kind: str
    service: str  # short service code used to build system codes
    description: str


FIELDS = [
    Field("deductible_individual_in", AMOUNT, "DED-IND-INN", "Overall in-network deductible, individual"),
    Field("deductible_family_in", AMOUNT, "DED-FAM-INN", "Overall in-network deductible, family"),
    Field("deductible_individual_oon", AMOUNT, "DED-IND-OON", "Overall out-of-network deductible, individual"),
    Field("deductible_family_oon", AMOUNT, "DED-FAM-OON", "Overall out-of-network deductible, family"),
    Field("oop_max_individual_in", AMOUNT, "OOP-IND-INN", "In-network out-of-pocket limit, individual"),
    Field("oop_max_family_in", AMOUNT, "OOP-FAM-INN", "In-network out-of-pocket limit, family"),
    Field("oop_max_individual_oon", AMOUNT, "OOP-IND-OON", "Out-of-network out-of-pocket limit, individual"),
    Field("oop_max_family_oon", AMOUNT, "OOP-FAM-OON", "Out-of-network out-of-pocket limit, family"),
    Field("pcp_visit", COST_SHARE, "PCP", "Primary care visit to treat an injury or illness"),
    Field("specialist_visit", COST_SHARE, "SPC", "Specialist visit"),
    Field("preventive_care", COST_SHARE, "PRV", "Preventive care, screening, immunization"),
    Field("emergency_room", COST_SHARE, "ER", "Emergency room care"),
    Field("urgent_care", COST_SHARE, "UC", "Urgent care"),
    Field("inpatient_facility", COST_SHARE, "IP", "Hospital stay, facility fee"),
    Field("outpatient_surgery_facility", COST_SHARE, "OPS", "Outpatient surgery, facility fee"),
    Field("imaging", COST_SHARE, "IMG", "Imaging (CT/PET scans, MRIs)"),
    Field("rx_tier1_generic", COST_SHARE, "RX1", "Generic drugs, retail"),
    Field("rx_tier2_preferred_brand", COST_SHARE, "RX2", "Preferred brand drugs, retail"),
    Field("rx_tier3_nonpreferred_brand", COST_SHARE, "RX3", "Non-preferred brand drugs, retail"),
    Field("rx_tier4_specialty", COST_SHARE, "RX4", "Specialty drugs"),
    Field("prior_auth_imaging", FLAG, "PA-IMG", "Prior authorization required for imaging"),
    Field("prior_auth_inpatient", FLAG, "PA-IP", "Prior authorization required for a hospital stay"),
]
BY_NAME = {f.name: f for f in FIELDS}
