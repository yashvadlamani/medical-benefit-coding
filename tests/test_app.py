from app import highlight


def test_highlight_marks_the_quote_across_line_breaks():
    html = highlight("Specialist visit\n$40 copayment\nNot covered", "Specialist visit $40 copayment")
    assert html == "<mark>Specialist visit\n$40 copayment</mark>\nNot covered"


def test_highlight_marks_separate_pieces_of_a_joined_quote():
    html = highlight("Generic drugs (Tier 1)\nRetail\n$5 copayment", "Generic drugs (Tier 1) ... $5 copayment")
    assert html.count("<mark>") == 2 and "<mark>5 copayment</mark>" in html


def test_highlight_escapes_document_text():
    assert "<script>" not in highlight("<script>alert(1)</script> $40 copay", "$40 copay")


def client(monkeypatch, password="test-only-value"):
    from werkzeug.security import generate_password_hash

    import app as review_app
    monkeypatch.setenv("REVIEW_PASSWORD_HASH", generate_password_hash(password))
    return review_app.app.test_client()


def test_pages_redirect_to_login_when_signed_out(monkeypatch):
    c = client(monkeypatch)
    response = c.get("/plan/ABC?field=pcp_visit")
    assert response.status_code == 302 and response.headers["Location"].startswith("/login?next=")
    assert c.post("/plan/ABC/decision", data={"action": "approve"}).status_code == 302
    assert c.get("/healthz").status_code == 200


def test_wrong_password_is_refused(monkeypatch):
    c = client(monkeypatch)
    assert c.post("/login", data={"password": "nope"}).status_code == 401
    assert c.get("/plan/ABC").headers["Location"].startswith("/login")


def test_right_password_signs_in_and_sign_out_ends_it(monkeypatch):
    c = client(monkeypatch)
    response = c.post("/login", data={"password": "test-only-value", "next": "/healthz"})
    assert response.status_code == 302 and response.headers["Location"] == "/healthz"
    with c.session_transaction() as s:
        assert s["signed_in"] is True
    c.post("/logout")
    assert c.get("/plan/ABC").headers["Location"].startswith("/login")


def test_login_does_not_redirect_to_another_site(monkeypatch):
    c = client(monkeypatch)
    response = c.post("/login", data={"password": "test-only-value", "next": "//evil.example"})
    assert response.headers["Location"] == "/"


def test_nobody_can_sign_in_when_no_password_is_configured(monkeypatch):
    import app as review_app
    monkeypatch.delenv("REVIEW_PASSWORD_HASH", raising=False)
    assert review_app.app.test_client().post("/login", data={"password": ""}).status_code == 401
