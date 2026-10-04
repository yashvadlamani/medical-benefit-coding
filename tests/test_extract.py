from benefit_coding import extract

PAGES = [{"page": 1, "text": "What is the overall\ndeductible?\n$1,500 individual / $3,000 family"},
         {"page": 2, "text": "Specialist visit\n$40  copayment"}]


def item(**overrides):
    base = {"field": "specialist_visit", "status": "value", "amount": None, "copay": 40, "coinsurance_pct": None,
            "deductible_applies": False, "flag": None, "quote": "Specialist visit $40 copayment", "page": 2,
            "confidence": 0.95, "note": ""}
    return {**base, **overrides}


def test_citation_matches_across_line_breaks_and_spacing():
    assert extract.verify_citation("Specialist visit $40 copayment", 2, PAGES) == (True, 2)


def test_citation_on_wrong_page_is_corrected():
    assert extract.verify_citation("$1,500 individual", 2, PAGES) == (True, 1)


def test_invented_quote_is_rejected_and_sent_to_review():
    cleaned = extract._clean(item(quote="Specialist visit $25 copayment"), PAGES)
    assert cleaned["citation_valid"] is False
    assert cleaned["confidence"] == extract.UNCITED_CONFIDENCE
    assert cleaned["needs_review"] is True


def test_valid_confident_field_skips_review():
    cleaned = extract._clean(item(), PAGES)
    assert cleaned["citation_valid"] and not cleaned["needs_review"]


def test_numbers_of_the_wrong_kind_are_dropped():
    cleaned = extract._clean(item(field="deductible_individual_in", amount=1500, copay=40,
                                  quote="$1,500 individual", page=1), PAGES)
    assert cleaned["amount"] == 1500 and cleaned["copay"] is None


def test_zero_cost_share_becomes_no_charge():
    assert extract._clean(item(copay=0), PAGES)["status"] == "no_charge"


def test_citation_may_join_a_label_and_value_that_are_not_adjacent():
    pages = [{"page": 1, "text": "What is the overall deductible?\nIn-network: $500\nOut-of-network: $1,500 individual"}]
    assert extract.verify_citation("What is the overall deductible? Out-of-network: $1,500 individual", 1, pages)[0]
    assert extract.verify_citation("overall deductible? ... $1,500 individual", 1, pages)[0]


def test_citation_cannot_be_assembled_from_part_of_a_larger_number():
    pages = [{"page": 1, "text": "Specialist visit\n$125 copayment per visit"}]
    assert not extract.verify_citation("Specialist visit $25 copayment per visit", 1, pages)[0]
    assert not extract.verify_citation("Specialist visit $12 copayment per visit", 1, pages)[0]
    assert extract.verify_citation("Specialist visit $125 copayment per visit", 1, pages)[0]
