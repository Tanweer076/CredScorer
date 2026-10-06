import json
from types import SimpleNamespace

import pytest
from reportlab.pdfgen import canvas

from app.documents import extraction
from app.documents.extraction import ExtractedDoc, MonthEntry, ScannedPDFError, extract, pdf_text
from app.documents.validation import names_match, validate


def slip(**changes) -> ExtractedDoc:
    data = dict(doc_type="salary_slip", person_name="Asha Rao", employer="Acme Ltd", pay_period="2026-09",
                monthly_gross_salary=60000, monthly_net_salary=52800, months=[])
    return ExtractedDoc(**{**data, **changes})


def statement(credits=(52800, 52800, 52800, 52800, 52800, 52800), balances=None, **changes) -> ExtractedDoc:
    balances = balances or [100000] * len(credits)
    months = [MonthEntry(month=f"2026-0{i + 1}", salary_credit=c, closing_balance=b)
              for i, (c, b) in enumerate(zip(credits, balances))]
    data = dict(doc_type="bank_statement", person_name="ASHA RAO", employer=None, pay_period=None,
                monthly_gross_salary=None, monthly_net_salary=None, months=months)
    return ExtractedDoc(**{**data, **changes})


@pytest.mark.parametrize("on_doc, applicant, expected", [
    ("Asha Rao", "Asha Rao", True),
    ("Ms. ASHA RAO", "Asha Rao", True),
    ("Asha K. Rao", "Asha Rao", True),
    ("Asha Mehta", "Asha Rao", False),
    ("Rao", "Asha Rao", True),  # surname-only documents still match
    ("", "Asha Rao", False),
])
def test_names_match(on_doc, applicant, expected):
    assert names_match(on_doc, applicant) is expected


def test_matching_salary_slip_passes():
    result = validate(slip(), "salary_slip", 60000, "Asha Rao")
    assert result.passed and result.confidence == 1.0 and result.issues == []


def test_salary_slip_with_lower_income_fails():
    result = validate(slip(monthly_gross_salary=36000, monthly_net_salary=31680), "salary_slip", 60000, "Asha Rao")
    assert not result.passed
    assert "differs from the salary slip" in result.issues[0]


def test_someone_elses_document_fails():
    result = validate(slip(person_name="Vikram Iyer"), "salary_slip", 60000, "Asha Rao")
    assert not result.passed
    assert "does not match the applicant" in result.issues[0]


def test_wrong_document_type_fails():
    result = validate(statement(), "salary_slip", 60000, "Asha Rao")
    assert not result.passed
    assert result.issues[0] == "uploaded as salary_slip but looks like bank_statement"


def test_matching_bank_statement_passes():
    result = validate(statement(), "bank_statement", 60000, "Asha Rao")
    assert result.passed and result.issues == []


def test_bank_statement_problems_add_up():
    result = validate(statement(credits=(20000, 20000), balances=[5000, -2000]), "bank_statement", 60000, "Asha Rao")
    assert not result.passed
    assert len(result.issues) == 3  # too few months, credits too low, overdrawn
    assert result.confidence == 0.4


def test_pdf_text_reads_a_generated_pdf(tmp_path):
    path = tmp_path / "slip.pdf"
    c = canvas.Canvas(str(path))
    c.drawString(50, 800, "Net Pay Rs. 52,800")
    c.save()
    assert "Net Pay Rs. 52,800" in pdf_text(str(path))


def test_pdf_without_text_is_reported_as_scanned(tmp_path):
    path = tmp_path / "scan.pdf"
    canvas.Canvas(str(path)).save()  # a page with no text, like a scanned image
    with pytest.raises(ScannedPDFError):
        pdf_text(str(path))


def test_extract_parses_gemini_json(monkeypatch):
    sent = {}

    def fake_generate_content(model, contents, config):
        sent["contents"] = contents
        return SimpleNamespace(text=json.dumps(slip().model_dump()))

    fake_client = SimpleNamespace(models=SimpleNamespace(generate_content=fake_generate_content))
    monkeypatch.setattr(extraction, "_get_client", lambda: fake_client)

    doc = extract("Employee Name Asha Rao ... Gross Earnings Rs. 60,000")

    assert doc.monthly_gross_salary == 60000
    assert "Gross Earnings Rs. 60,000" in sent["contents"]