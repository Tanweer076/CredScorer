"""Generate fake salary slips and bank statements for testing document screening.

Run from the backend folder:
    python make_fake_docs.py --name "Asha Rao" --salary 60000

It writes three sets of PDFs into fake_docs/:
  <name>_good_*.pdf             everything matches what the applicant declared
  <name>_low_income_*.pdf       the documents show 40% less income than declared
  <name>_wrong_name_*.pdf       the documents belong to someone else
"""
import argparse
import random
from datetime import date
from pathlib import Path

from faker import Faker
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

OUT_DIR = Path("fake_docs")
fake = Faker("en_IN")


def money(value: float) -> str:
    # ReportLab's built-in fonts have no rupee sign, so we write "Rs."
    return f"Rs. {value:,.0f}"


def last_months(n: int) -> list[date]:
    today = date.today().replace(day=1)
    months = []
    year, month = today.year, today.month
    for _ in range(n):
        month -= 1
        if month == 0:
            year, month = year - 1, 12
        months.append(date(year, month, 1))
    return list(reversed(months))


def salary_slip(path: Path, name: str, employer: str, gross: float) -> None:
    month = last_months(1)[0]
    deductions = round(gross * 0.12)
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 800, employer)
    c.setFont("Helvetica", 9)
    c.drawString(50, 785, fake.address().replace("\n", ", "))
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, 755, f"Salary Slip for {month:%B %Y}")
    c.setFont("Helvetica", 11)
    rows = [
        ("Employee Name", name),
        ("Employee ID", fake.bothify("EMP####")),
        ("Designation", fake.job()),
        ("PAN", fake.bothify("?????####?").upper()),
        ("", ""),
        ("Basic Salary", money(gross * 0.5)),
        ("House Rent Allowance", money(gross * 0.2)),
        ("Other Allowances", money(gross * 0.3)),
        ("Gross Earnings", money(gross)),
        ("Provident Fund", money(deductions * 0.75)),
        ("Professional Tax", money(deductions * 0.25)),
        ("Total Deductions", money(deductions)),
        ("Net Pay", money(gross - deductions)),
    ]
    for i, (label, value) in enumerate(rows):
        c.drawString(50, 720 - i * 20, label)
        c.drawString(300, 720 - i * 20, value)
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(50, 420, "This is a computer-generated salary slip and does not need a signature.")
    c.save()


def bank_statement(path: Path, name: str, employer: str, gross: float) -> None:
    net = gross - round(gross * 0.12)
    balance = random.randint(20_000, 150_000)
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 800, f"{fake.last_name()} Bank Ltd - Savings Account Statement")
    c.setFont("Helvetica", 10)
    c.drawString(50, 782, f"Account holder: {name}")
    c.drawString(50, 768, f"Account number: XXXXXX{fake.numerify('####')}")
    c.drawString(50, 744, "Date          Description                                   Amount            Balance")
    y = 726
    for month in last_months(6):
        entries = [
            (month.replace(day=1), f"SALARY CREDIT {employer[:28].upper()}", net),
            (month.replace(day=5), "RENT TRANSFER", -round(net * random.uniform(0.2, 0.3))),
            (month.replace(day=12), "UPI GROCERY STORE", -round(net * random.uniform(0.05, 0.12))),
            (month.replace(day=20), "CARD PAYMENT", -round(net * random.uniform(0.1, 0.3))),
        ]
        for day, text, amount in entries:
            balance += amount
            sign = "+" if amount > 0 else "-"
            c.drawString(50, y, f"{day:%d-%m-%Y}    {text:<44}{sign}{money(abs(amount)):>14}   {money(balance):>14}")
            y -= 14
        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, y, f"Closing balance {month:%b %Y}: {money(balance)}")
        c.setFont("Helvetica", 10)
        y -= 20
    c.save()


def make_set(prefix: str, name: str, employer: str, gross: float) -> None:
    salary_slip(OUT_DIR / f"{prefix}_salary_slip.pdf", name, employer, gross)
    bank_statement(OUT_DIR / f"{prefix}_bank_statement.pdf", name, employer, gross)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--name", required=True, help="Applicant's full name, as in their account")
    parser.add_argument("--salary", type=float, required=True, help="Declared monthly income")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)
    Faker.seed(args.seed)
    OUT_DIR.mkdir(exist_ok=True)
    slug = "_".join(args.name.lower().split())
    employer = fake.company()

    make_set(f"{slug}_good", args.name, employer, args.salary)
    make_set(f"{slug}_low_income", args.name, employer, args.salary * 0.6)
    make_set(f"{slug}_wrong_name", fake.name(), employer, args.salary)
    for path in sorted(OUT_DIR.glob(f"{slug}_*.pdf")):
        print(path)


if __name__ == "__main__":
    main()