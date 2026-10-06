"""Try Gemini extraction + validation on one PDF, without the database or the API.

Run from the backend folder:
    python try_extraction.py fake_docs/asha_rao_good_salary_slip.pdf salary_slip --name "Asha Rao" --income 60000
"""
import argparse
import json

from app.documents.extraction import extract, pdf_text
from app.documents.validation import validate

parser = argparse.ArgumentParser()
parser.add_argument("pdf")
parser.add_argument("doc_type", choices=["salary_slip", "bank_statement"])
parser.add_argument("--name", required=True, help="Applicant's name")
parser.add_argument("--income", type=float, required=True, help="Declared monthly income")
args = parser.parse_args()

doc = extract(pdf_text(args.pdf))
print("Gemini extracted:")
print(json.dumps(doc.model_dump(), indent=2))

result = validate(doc, args.doc_type, args.income, args.name)
print(f"\nConfidence: {result.confidence}  ->  {'PASS' if result.passed else 'FAIL'}")
for issue in result.issues:
    print(f"  - {issue}")