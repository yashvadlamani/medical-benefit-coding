from benefit_coding import evaluate


def test_dollars():
    assert evaluate._dollars("$1,500 ") == 1500
    assert evaluate._dollars("$3000 per group") == 3000
    assert evaluate._dollars("$30.00 Copay after deductible") == 30
    assert evaluate._dollars("per person not applicable") is None
    assert evaluate._dollars("No Charge") is None


def test_percent():
    assert evaluate._percent("30.00% Coinsurance after deductible") == 30
    assert evaluate._percent("Not Applicable") is None


def test_actual_value_shapes():
    base = {"amount": None, "copay": None, "coinsurance_pct": None}
    assert evaluate.actual_value({**base, "kind": "amount", "status": "value", "amount": 1500}) == ("amount", 1500.0)
    assert evaluate.actual_value({**base, "kind": "amount", "status": "not_applicable"}) == ("amount", None)
    assert evaluate.actual_value({**base, "kind": "cost_share", "status": "no_charge"}) == ("cost_share", 0.0, 0.0)
    assert evaluate.actual_value({**base, "kind": "cost_share", "status": "value", "copay": 40}) == ("cost_share", 40.0, 0.0)
    assert evaluate.actual_value({**base, "kind": "cost_share", "status": "not_covered"}) == ("not_covered",)
