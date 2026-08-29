from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _text(value):
    if value in (None, ""):
        return "—"
    return str(value)


def _section_table(title, headers, rows, styles):
    flowables = [Paragraph(title, styles["Heading2"])]
    if not rows:
        flowables.append(Paragraph("None recorded.", styles["Normal"]))
        flowables.append(Spacer(1, 6))
        return flowables
    data = [headers, *rows]
    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Times-Roman"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.90, 0.90, 0.88)),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.Color(0.7, 0.7, 0.7)),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    flowables.append(table)
    flowables.append(Spacer(1, 8))
    return flowables


def build_soldier_pdf(soldier):
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=f"1 BIR — {soldier.army_number} {soldier.name}",
    )
    styles = getSampleStyleSheet()
    story = [
        Paragraph("1 BIR — Soldier Record", styles["Title"]),
        Paragraph(
            f"{_text(soldier.army_number)} · {_text(soldier.rank)} · {_text(soldier.name)}",
            styles["Heading3"],
        ),
        Spacer(1, 6),
    ]

    particulars = [
        ["Organization", _text(soldier.organization)],
        ["Date of birth", _text(soldier.dob)],
        ["Enrollment", _text(soldier.doe)],
        ["Age", _text(soldier.age)],
        ["Service years", _text(soldier.service_years)],
        ["Batch", _text(soldier.batch)],
        ["NID", _text(soldier.nid_number)],
        ["Passport", _text(soldier.passport_number)],
        ["Service ID", _text(soldier.service_id_card_number)],
        ["Present address", _text(soldier.present_address)],
        ["Permanent address", _text(soldier.permanent_address)],
        ["Discipline", _text(soldier.discipline)],
        ["Punishment", _text(soldier.punishment)],
    ]
    story.extend(_section_table("Particulars", ["Field", "Value"], particulars, styles))

    story.extend(
        _section_table(
            "Service history",
            ["Organization", "Rank", "Start", "End"],
            [
                [
                    _text(item.organization),
                    _text(item.rank),
                    _text(item.start_date),
                    _text(item.end_date),
                ]
                for item in soldier.service_histories.all()
            ],
            styles,
        )
    )
    story.extend(
        _section_table(
            "Civil education",
            ["Level", "Institution", "From", "To", "Grade"],
            [
                [
                    _text(item.level),
                    _text(item.institution_name),
                    _text(item.from_date),
                    _text(item.to_date),
                    _text(item.grade),
                ]
                for item in soldier.civil_educations.all()
            ],
            styles,
        )
    )
    story.extend(
        _section_table(
            "Medical category",
            ["Type", "From", "To"],
            [
                [_text(item.type), _text(item.from_date), _text(item.to_date)]
                for item in soldier.medical_categories.all()
            ],
            styles,
        )
    )
    story.extend(
        _section_table(
            "Annual performance",
            ["Year", "Score", "Report"],
            [
                [_text(item.year), _text(item.score), _text(item.report)]
                for item in soldier.annual_performance_reports.all()
            ],
            styles,
        )
    )
    story.extend(
        _section_table(
            "Appointments",
            ["Appointment", "Organization", "Start", "End"],
            [
                [
                    _text(item.appointment_name),
                    _text(item.organization),
                    _text(item.start_date),
                    _text(item.end_date),
                ]
                for item in soldier.appointment_histories.all()
            ],
            styles,
        )
    )
    story.extend(
        _section_table(
            "Family",
            ["Relation", "Occupation", "Remarks"],
            [
                [_text(item.relation_name), _text(item.occupation), _text(item.remarks)]
                for item in soldier.family_members.all()
            ],
            styles,
        )
    )
    story.extend(
        _section_table(
            "Contact",
            ["Type", "Number"],
            [
                [_text(item.get_type_of_number_display()), _text(item.mobile_number)]
                for item in soldier.mobile_numbers.all()
            ],
            styles,
        )
    )
    story.extend(
        _section_table(
            "Leave",
            ["Slot", "Type", "From", "To", "Status"],
            [
                [
                    _text(item.get_slot_display()),
                    _text(item.leave_type),
                    _text(item.from_date),
                    _text(item.to_date),
                    _text(item.get_status_display()),
                ]
                for item in soldier.leave_states.all()
            ],
            styles,
        )
    )
    story.extend(
        _section_table(
            "Qualifications",
            ["Year", "PE", "SPL", "Next promotion"],
            [
                [
                    _text(item.year),
                    _text(item.pe),
                    _text(item.spl),
                    "Yes" if item.qual_for_next_promotion else "No",
                ]
                for item in soldier.qualifications.all()
            ],
            styles,
        )
    )

    document.build(story)
    buffer.seek(0)
    return buffer
