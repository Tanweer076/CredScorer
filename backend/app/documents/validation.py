"""Check what Gemini extracted against what the applicant declared.

Every problem lowers a confidence score that starts at 1.0. A document passes
when its confidence stays at or above PASS_CONFIDENCE. The issues are stored so
an underwriter can see exactly why a document failed.
"""
from dataclasses import dataclass, field

from app.documents.extraction import ExtractedDoc

PASS_CONFIDENCE = 0.7
INCOME_TOLERANCE = 0.15  # slip gross may differ from declared income by up to 15%
TITLES = {"mr", "mrs", "ms", "miss", "dr", "shri", "smt", "kumari"}


@dataclass
class ValidationResult:
    confidence: float = 1.0
    issues: list[str] = field(default_factory=list)

    def flag(self, issue: str, penalty: float) -> None:
        self.issues.append(issue)
        self.confidence = round(max(self.confidence - penalty, 0.0), 2)

    @property
    def passed(self) -> bool:
        return self.confidence >= PASS_CONFIDENCE


def _name_tokens(name: str) -> set[str]:
    words = "".join(ch if ch.isalpha() else " " for ch in name.lower()).split()
    return {w for w in words if w not in TITLES}


def names_match(on_document: str, applicant: str) -> bool:
    """'Asha Rao' matches 'Ms. ASHA RAO' and 'Asha K. Rao', not 'Asha Mehta'."""
    doc, app = _name_tokens(on_document), _name_tokens(applicant)
    if not doc or not app:
        return False
    shorter, longer = sorted([doc, app], key=len)
    return shorter <= longer


def _gap(actual: float, declared: float) -> float:
    return abs(actual - declared) / declared


def validate(doc: ExtractedDoc, expected_type: str, declared_income: float, applicant_name: str) -> ValidationResult:
    result = ValidationResult()

    if doc.doc_type != expected_type:
        result.flag(f"uploaded as {expected_type} but looks like {doc.doc_type}", 0.6)

    if doc.person_name is None:
        result.flag("no name found on the document", 0.2)
    elif not names_match(doc.person_name, applicant_name):
        result.flag(f"name on document ({doc.person_name}) does not match the applicant ({applicant_name})", 0.4)

    if expected_type == "salary_slip":
        _check_salary_slip(doc, declared_income, result)
    elif expected_type == "bank_statement":
        _check_bank_statement(doc, declared_income, result)
    return result


def _check_salary_slip(doc: ExtractedDoc, declared: float, result: ValidationResult) -> None:
    if doc.employer is None:
        result.flag("no employer found on the salary slip", 0.1)
    gross, net = doc.monthly_gross_salary, doc.monthly_net_salary
    if gross is None and net is None:
        result.flag("no salary amount found on the salary slip", 0.4)
        return
    if gross is not None and net is not None and net > gross:
        result.flag("net pay is higher than gross pay", 0.2)
    if declared > 0:
        # Declared income is compared with gross pay; if only net pay is shown, allow for deductions.
        amount, tolerance = (gross, INCOME_TOLERANCE) if gross is not None else (net, 0.30)
        if _gap(amount, declared) > tolerance:
            result.flag(f"declared income ({declared:,.0f}) differs from the salary slip "
                        f"({amount:,.0f}) by {_gap(amount, declared):.0%}", 0.4)


def _check_bank_statement(doc: ExtractedDoc, declared: float, result: ValidationResult) -> None:
    if len(doc.months) < 3:
        result.flag(f"statement covers {len(doc.months)} month(s); at least 3 are needed", 0.2)
    credits = [m.salary_credit for m in doc.months if m.salary_credit]
    if not credits:
        result.flag("no salary credits found in the bank statement", 0.3)
    elif declared > 0:
        average = sum(credits) / len(credits)
        # Salary credits are take-home pay, so they are usually 5-30% below declared (gross) income.
        if not 0.7 * declared <= average <= 1.15 * declared:
            result.flag(f"average salary credit ({average:,.0f}) does not fit the declared income "
                        f"({declared:,.0f})", 0.4)
    if any(m.closing_balance is not None and m.closing_balance < 0 for m in doc.months):
        result.flag("account was overdrawn in at least one month", 0.1)