from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def build_soldier_pdf(soldier):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 60
    pdf.setFont("Times-Bold", 16)
    pdf.drawString(50, y, "1 BIR — Soldier Record")
    y -= 30
    pdf.setFont("Times-Roman", 11)
    lines = [
        f"Name: {soldier.name}",
        f"Army Number: {soldier.army_number}",
        f"Rank: {soldier.rank}",
        f"Organization: {soldier.organization}",
        f"Date of Birth: {soldier.dob}",
        f"Enrollment: {soldier.doe}",
    ]
    for line in lines:
        pdf.drawString(50, y, line)
        y -= 18
    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer
