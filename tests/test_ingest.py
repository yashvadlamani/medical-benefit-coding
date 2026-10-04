from benefit_coding import ingest

SBC_PAGES = [
    "Summary of Benefits and Coverage: What this Plan Covers\nImportant Questions\nAnswers\n"
    "What is the overall deductible?\n$1,500 individual / $3,000 family",
    "Common\nMedical Event\nServices You May Need\nSpecialist visit\n$40 copayment",
    "Excluded Services & Other Covered Services:\nCosmetic surgery\n"
    "Your Rights to Continue Coverage: call us\nAbout these Coverage Examples:\nPeg is Having a Baby",
]


def test_classifies_sbc():
    assert ingest.classify(SBC_PAGES) == "sbc"


def test_classifies_unknown_document_as_other():
    assert ingest.classify(["Quarterly newsletter", "Wellness tips"]) == "other"


def test_splits_sbc_at_template_headings():
    sections = ingest.split_sections(SBC_PAGES, "sbc")
    assert [s.name for s in sections] == [
        "header", "important_questions", "common_medical_events",
        "excluded_and_other_services", "rights_and_notices", "coverage_examples"]
    events = sections[2]
    assert (events.start_page, events.end_page) == (2, 2)
    assert "Specialist visit" in events.parts[0]["text"]
    assert "Cosmetic surgery" not in events.parts[0]["text"]


def test_sections_on_one_page_do_not_overlap():
    sections = {s.name: s for s in ingest.split_sections(SBC_PAGES, "sbc")}
    assert "Peg is Having a Baby" in sections["coverage_examples"].parts[0]["text"]
    assert "Peg is Having a Baby" not in sections["rights_and_notices"].parts[0]["text"]


def test_other_documents_split_by_page():
    sections = ingest.split_sections(["one", "two"], "other")
    assert [(s.name, s.start_page) for s in sections] == [("page_1", 1), ("page_2", 2)]
