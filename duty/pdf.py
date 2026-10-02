from io import BytesIO

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from common.pdf import _section_table, _text


def _document(buffer, title, pagesize=A4):
    return SimpleDocTemplate(
        buffer,
        pagesize=pagesize,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=title,
    )


def _heading(story, styles, title, subtitle):
    story.append(Paragraph(title, styles["Title"]))
    story.append(Paragraph(subtitle, styles["Heading3"]))
    story.append(Spacer(1, 8))


def build_daily_roster_pdf(report_date, roster, company=None):
    buffer = BytesIO()
    scope = company.organization_name if company else "1 BIR"
    title = f"1 BIR — Daily Duty Roster — {report_date:%d %b %Y}"
    document = _document(buffer, title)
    styles = getSampleStyleSheet()
    story = []
    _heading(
        story,
        styles,
        "DAILY DUTY ROSTER — 1 BIR",
        f"{scope} · {report_date:%d %B %Y}",
    )
    post_rows = [
        [
            str(row["serial"]),
            _text(row["post"].name),
            str(row["day"] or "—"),
            str(row["night"] or "—"),
            str(row["total"]),
            _text(row["names_day"]),
            _text(row["names_night"]),
        ]
        for row in roster["post_rows"]
    ]
    story.extend(
        _section_table(
            "Duty by post",
            ["Ser", "Place", "Day", "Ni", "Total", "Day detail", "Night detail"],
            post_rows,
            styles,
        )
    )
    named_rows = [
        [
            str(row["serial"]),
            _text(row["soldier"].army_number),
            _text(row["soldier"].rank),
            _text(row["soldier"].name),
            _text(row["platoon"]),
            _text(row["post"].name),
            row["assignment"].get_shift_display(),
            row["assignment"].get_status_display(),
        ]
        for row in roster["named_rows"]
    ]
    story.extend(
        _section_table(
            "Named roll",
            ["Ser", "Army No", "Rk", "Name", "Pl", "Post", "Shift", "Status"],
            named_rows,
            styles,
        )
    )
    document.build(story)
    buffer.seek(0)
    return buffer


def build_monthly_roster_pdf(month_start, summary, company=None):
    buffer = BytesIO()
    scope = company.organization_name if company else "1 BIR"
    title = f"1 BIR — Monthly Duty Roster — {month_start:%b %Y}"
    document = _document(buffer, title, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    story = []
    _heading(
        story,
        styles,
        "MONTHLY DUTY ROSTER SUMMARY — 1 BIR",
        f"{scope} · {month_start:%B %Y}",
    )
    soldier_rows = [
        [
            str(row["serial"]),
            _text(row["soldier"].army_number),
            _text(row["soldier"].rank),
            _text(row["soldier"].name),
            _text(row["platoon"]),
            str(row["day"]),
            str(row["night"]),
            str(row["total"]),
        ]
        for row in summary["soldier_rows"]
    ]
    story.extend(
        _section_table(
            "Soldier duty days",
            ["Ser", "Army No", "Rk", "Name", "Pl / Coy", "Day", "Night", "Total"],
            soldier_rows,
            styles,
        )
    )
    post_rows = [
        [
            str(row["serial"]),
            _text(row["post"].name),
            row["post"].get_duty_type_display(),
            str(row["day"]),
            str(row["night"]),
            str(row["total"]),
        ]
        for row in summary["post_rows"]
    ]
    story.extend(
        _section_table(
            "Post duty days",
            ["Ser", "Place", "Type", "Day", "Night", "Total"],
            post_rows,
            styles,
        )
    )
    document.build(story)
    buffer.seek(0)
    return buffer
