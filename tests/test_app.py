from app import highlight


def test_highlight_marks_the_quote_across_line_breaks():
    html = highlight("Specialist visit\n$40 copayment\nNot covered", "Specialist visit $40 copayment")
    assert html == "<mark>Specialist visit\n$40 copayment</mark>\nNot covered"


def test_highlight_marks_separate_pieces_of_a_joined_quote():
    html = highlight("Generic drugs (Tier 1)\nRetail\n$5 copayment", "Generic drugs (Tier 1) ... $5 copayment")
    assert html.count("<mark>") == 2 and "<mark>5 copayment</mark>" in html


def test_highlight_escapes_document_text():
    assert "<script>" not in highlight("<script>alert(1)</script> $40 copay", "$40 copay")
