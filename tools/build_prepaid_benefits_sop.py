"""
Build the prepaid benefits SOP PDF used by the health-benefits GPT.
"""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = PROJECT_ROOT / "docs" / "Health_Benefits_Prepaid_Benefits_Supplement.pdf"


def build_pdf() -> None:
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="TitleCenter",
            parent=styles["Title"],
            alignment=TA_CENTER,
            fontSize=18,
            leading=22,
            spaceAfter=16,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionHeading",
            parent=styles["Heading2"],
            fontSize=13,
            leading=16,
            spaceBefore=10,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyTight",
            parent=styles["BodyText"],
            fontSize=10,
            leading=13,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SmallHeading",
            parent=styles["Heading3"],
            fontSize=11,
            leading=14,
            spaceBefore=8,
            spaceAfter=6,
        )
    )

    doc = SimpleDocTemplate(
        str(OUTPUT_PATH),
        pagesize=letter,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
    )

    story = [
        Paragraph(
            "Health Benefits Clearing<br/>Supplement: Prepaid Benefits, True-Ups, and Annual Premiums",
            styles["TitleCenter"],
        ),
        Paragraph(
            "Purpose: This supplement gives the AI and preparer a reusable procedure for annual prepaid "
            "benefit items that flow through a health benefits clearing account. It is designed to work "
            "alongside Document 0 (Client Setup Intake), Document 1 (Methodology Reference), Document 2 "
            "(Tieout Procedure), and Document 3 (Worked Examples).",
            styles["BodyTight"],
        ),
        Paragraph(
            "Use this supplement whenever a benefit-related transaction includes an annual premium, "
            "prior-period true-up, prepaid asset, monthly amortization pattern, or non-medical product "
            "such as Guardian DBL/PFL, disability, dental, vision, or life insurance.",
            styles["BodyTight"],
        ),
        Paragraph("1. When This SOP Applies", styles["SectionHeading"]),
        Paragraph(
            "Apply this supplement before calling a benefits-clearing item unexplained if any of the "
            "following are true:",
            styles["BodyTight"],
        ),
    ]

    applicability_items = [
        "The clearing account contains annual or one-time insurance payments rather than a normal monthly invoice.",
        "The invoice includes both a current-year premium and a prior-year true-up.",
        "The account contains non-medical products mixed with medical clearing activity.",
        "A prepaid asset or monthly amortization entry appears in the GL detail.",
        "Payroll deductions do not line up cleanly to monthly carrier activity because the product is billed annually.",
    ]
    story.append(
        ListFlowable(
            [ListItem(Paragraph(item, styles["BodyTight"])) for item in applicability_items],
            bulletType="bullet",
        )
    )

    story.extend(
        [
            Paragraph("2. Required Phase 1 Setup", styles["SectionHeading"]),
            Paragraph(
                "Before analyzing the account, confirm the product, carrier, payment method, billing cadence, "
                "coverage year, payroll frequency, and whether the company records the item in a shared clearing "
                "account, a prepaid asset account, or both.",
                styles["BodyTight"],
            ),
        ]
    )

    setup_table = Table(
        [
            ["Field", "Why it matters"],
            ["Carrier and product", "Distinguishes medical activity from Guardian, DBL/PFL, disability, dental, vision, or life items."],
            ["Billing cadence", "Determines whether the item should be treated as a monthly charge or an annual prepaid premium."],
            ["Coverage year", "Separates prior-year true-ups from the current-year premium."],
            ["Payroll frequency", "Explains why deductions may exceed or trail amortization in 3-pay or 2-pay months."],
            ["Posting method", "Confirms whether the payment hit clearing, prepaid, AP, or a manual journal entry."],
        ],
        colWidths=[1.7 * inch, 4.8 * inch],
        repeatRows=1,
    )
    setup_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbe7f3")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#9aa9b8")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("LEADING", (0, 0), (-1, -1), 11),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend([setup_table, Spacer(1, 0.15 * inch)])

    story.extend(
        [
            Paragraph("3. Decision Sequence", styles["SectionHeading"]),
            Paragraph(
                "Execute the following logic in order. Stop when the transaction is fully explained.",
                styles["BodyTight"],
            ),
        ]
    )
    decision_items = [
        "Separate non-medical products from medical clearing activity before performing the medical tieout.",
        "If the annual invoice includes a prior-year true-up, expense that portion immediately in the current close period unless a documented prior-period correction is being booked separately.",
        "Book the current-year premium portion to a prepaid asset and amortize it evenly over the coverage year unless the carrier terms require a different coverage pattern.",
        "Use monthly amortization as the benchmark for current-period expense, then compare payroll deductions to the amortization pattern over the full year rather than forcing a monthly divisor conversion.",
        "If payroll deductions for the product flow through the clearing account, compare their annualized total to the annual premium. In 3-pay months, deductions may exceed monthly amortization; in 2-pay months, amortization may exceed deductions.",
        "If a formula exists for the employer portion, execute it before presenting hypotheses. Standard formula: total carrier payment minus employee payroll deductions equals employer portion to expense.",
        "Only escalate after prepaid treatment, timing, true-up, and employer-portion formulas have been tested and documented.",
    ]
    story.append(
        ListFlowable(
            [ListItem(Paragraph(item, styles["BodyTight"])) for item in decision_items],
            bulletType="1",
            start="1",
        )
    )

    story.extend(
        [
            Paragraph("4. Scenario A - Guardian NY DBL/PFL Annual Invoice with Prepaid Amortization", styles["SectionHeading"]),
            Paragraph(
                "Fact pattern: Guardian issues an annual DBL/PFL invoice totaling 2,559.50. The invoice contains "
                "two components: 2,080.54 for the current coverage year and 478.96 for a prior-year true-up. "
                "Payroll deductions for DBL/PFL continue to run biweekly through the year.",
                styles["BodyTight"],
            ),
        ]
    )

    example_table = Table(
        [
            ["Component", "Amount", "Accounting treatment"],
            ["Current-year premium", "2,080.54", "Record as prepaid benefit asset and amortize over 12 months."],
            ["Prior-year true-up", "478.96", "Expense immediately in the current close period."],
            ["Total invoice", "2,559.50", "Matches Guardian annual bill."],
        ],
        colWidths=[1.8 * inch, 1.1 * inch, 3.6 * inch],
        repeatRows=1,
    )
    example_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbe7f3")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#9aa9b8")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("LEADING", (0, 0), (-1, -1), 11),
            ]
        )
    )
    story.extend([example_table, Spacer(1, 0.12 * inch)])
    story.extend(
        [
            Paragraph("Step 1: Record the annual invoice", styles["SmallHeading"]),
            Paragraph(
                "Journal entry on payment or bill recognition:<br/>"
                "DR Prepaid Benefits - DBL/PFL 2,080.54<br/>"
                "DR Benefits Expense - Prior-Year True-Up 478.96<br/>"
                "CR Cash or Accounts Payable 2,559.50",
                styles["BodyTight"],
            ),
            Paragraph("Step 2: Calculate monthly amortization", styles["SmallHeading"]),
            Paragraph(
                "Monthly amortization = 2,080.54 divided by 12 = 173.38 per month after rounding.",
                styles["BodyTight"],
            ),
            Paragraph("Step 3: Book monthly expense", styles["SmallHeading"]),
            Paragraph(
                "Monthly entry:<br/>DR Benefits Expense - DBL/PFL 173.38<br/>CR Prepaid Benefits - DBL/PFL 173.38",
                styles["BodyTight"],
            ),
            Paragraph("Step 4: Interpret the February prepaid entry", styles["SmallHeading"]),
            Paragraph(
                "If the GL shows a prepaid-related entry of 346.76 as of 2/28, test it against the amortization "
                "schedule first: 173.38 x 2 months = 346.76. If it matches, the balance is explained. It represents "
                "January and February amortization of the current-year premium, not an unexplained variance.",
                styles["BodyTight"],
            ),
            Paragraph("Step 5: Compare payroll deductions correctly", styles["SmallHeading"]),
            Paragraph(
                "Do not convert biweekly DBL/PFL deductions to a monthly amount with a divisor. Compare the annualized "
                "payroll deductions to the annual premium or document the monthly activity as a timing pattern. In a "
                "3-pay month, deductions may be higher than the single month of amortization; in a 2-pay month, "
                "amortization may exceed deductions. That pattern is expected and self-corrects over the year.",
                styles["BodyTight"],
            ),
        ]
    )

    story.append(PageBreak())
    story.extend(
        [
            Paragraph("5. Annual Tieout Rule for Payroll vs Carrier Activity", styles["SectionHeading"]),
            Paragraph(
                "When validating per-paycheck withholdings against a monthly carrier rate, use the annualized comparison. "
                "Do not create a monthly equivalent by multiplying a per-paycheck amount by an estimated monthly divisor.",
                styles["BodyTight"],
            ),
            Paragraph(
                "Required method:<br/>"
                "Payroll annual amount = per-paycheck withholding x 26 for biweekly payroll or x 24 for semimonthly payroll.<br/>"
                "Carrier annual amount = monthly carrier rate x 12.<br/>"
                "If the annual variance is within the documented rounding tolerance, the rates tie.",
                styles["BodyTight"],
            ),
            Paragraph("6. Employer Portion Formula", styles["SectionHeading"]),
            Paragraph(
                "When a non-medical product is billed through the clearing account, calculate the employer portion before "
                "offering explanations. Standard formula:<br/>"
                "Employer portion = total carrier payment minus employee payroll deductions.",
                styles["BodyTight"],
            ),
            Paragraph(
                "If the product is billed annually, apply the formula to the annual payment and then separate the result into "
                "prepaid current-year premium, current-period expense, and any prior-year true-up as needed.",
                styles["BodyTight"],
            ),
            Paragraph("7. Workpaper Documentation Language", styles["SectionHeading"]),
            Paragraph(
                "Example: 'Guardian DBL/PFL annual invoice of 2,559.50 reviewed. Split into 478.96 prior-year true-up "
                "expensed immediately and 2,080.54 current-year premium recorded as prepaid. Monthly amortization is 173.38. "
                "Prepaid-related balance at 2/28 of 346.76 ties to two months of amortization. No unexplained variance.'",
                styles["BodyTight"],
            ),
            Paragraph("8. Escalation Triggers", styles["SectionHeading"]),
            Paragraph(
                "Escalate only if one of the following remains true after applying this supplement: the invoice split cannot "
                "be supported, the prepaid balance does not match the amortization schedule, payroll deductions do not tie on "
                "an annual basis, the employer portion cannot be explained, or non-medical activity cannot be isolated from "
                "medical clearing activity.",
                styles["BodyTight"],
            ),
            Paragraph(
                "Upsourced Internal Document - Not for Client Distribution",
                styles["BodyTight"],
            ),
        ]
    )

    doc.build(story)


if __name__ == "__main__":
    build_pdf()
