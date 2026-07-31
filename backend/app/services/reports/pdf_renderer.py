from __future__ import annotations

import json
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.services.reports.complaint_brief_schema import ComplaintBrief


def _pdf_safe_text(value: Any) -> str:
    if value is None:
        text = "Not provided"
    elif isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    else:
        text = str(value)
    safe_chars = []
    for char in text:
        code = ord(char)
        if char in "\n\r\t" or 32 <= code <= 255:
            safe_chars.append(char)
        else:
            safe_chars.append(f"[U+{code:04X}]")
    return "".join(safe_chars).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _brief_table(rows: list[tuple[str, Any]], styles: dict[str, ParagraphStyle]) -> Table:
    table_data = [
        [Paragraph(_pdf_safe_text(label), styles["CellLabel"]), Paragraph(_pdf_safe_text(value), styles["Cell"])]
        for label, value in rows
    ]
    table = Table(table_data, colWidths=[42 * mm, 120 * mm], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D9DEEA")),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F5F7FB")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _rows_table(rows: list[dict[str, Any]], styles: dict[str, ParagraphStyle]) -> Table:
    keys = sorted({key for row in rows for key in row})[:6]
    table_data = [[Paragraph(_pdf_safe_text(key.replace("_", " ").title()), styles["CellLabel"]) for key in keys]]
    for row in rows[:20]:
        table_data.append([Paragraph(_pdf_safe_text(row.get(key)), styles["Cell"]) for key in keys])
    table = Table(table_data, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D9DEEA")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F5F7FB")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _page_footer(document_id: str):
    def _draw(canvas, doc) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#5B6475"))
        canvas.drawString(18 * mm, 12 * mm, _pdf_safe_text(document_id))
        canvas.drawRightString(192 * mm, 12 * mm, f"Page {doc.page}")
        canvas.restoreState()

    return _draw


def render_complaint_brief_pdf(brief: ComplaintBrief) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=20 * mm,
        title=brief.document_identifier,
    )
    sample_styles = getSampleStyleSheet()
    styles = {
        "Title": ParagraphStyle("BriefTitle", parent=sample_styles["Title"], fontName="Helvetica-Bold", fontSize=18, leading=22, spaceAfter=8),
        "Heading": ParagraphStyle("BriefHeading", parent=sample_styles["Heading2"], fontName="Helvetica-Bold", fontSize=12, leading=15, spaceBefore=10, spaceAfter=6),
        "Body": ParagraphStyle("BriefBody", parent=sample_styles["BodyText"], fontName="Helvetica", fontSize=8.5, leading=11),
        "Disclaimer": ParagraphStyle("BriefDisclaimer", parent=sample_styles["BodyText"], fontName="Helvetica-Bold", fontSize=8.5, leading=11, backColor=colors.HexColor("#FFF7ED"), borderColor=colors.HexColor("#F59E0B"), borderWidth=0.5, borderPadding=6),
        "Cell": ParagraphStyle("BriefCell", parent=sample_styles["BodyText"], fontName="Helvetica", fontSize=7.2, leading=9),
        "CellLabel": ParagraphStyle("BriefCellLabel", parent=sample_styles["BodyText"], fontName="Helvetica-Bold", fontSize=7.2, leading=9),
    }
    story = [
        Paragraph(_pdf_safe_text(brief.title), styles["Title"]),
        Paragraph(_pdf_safe_text(f"Document: {brief.document_identifier}"), styles["Body"]),
        Paragraph(_pdf_safe_text(f"Generated: {brief.generated_at.isoformat()}"), styles["Body"]),
        Spacer(1, 4),
        Paragraph(_pdf_safe_text(brief.disclaimer), styles["Disclaimer"]),
        Spacer(1, 8),
    ]
    for index, section in enumerate(brief.sections):
        if index and index % 7 == 0:
            story.append(PageBreak())
        story.append(Paragraph(_pdf_safe_text(section.title), styles["Heading"]))
        if section.fields:
            story.append(_brief_table([(field.label, field.value) for field in section.fields], styles))
            story.append(Spacer(1, 5))
        if section.rows:
            story.append(_rows_table(section.rows, styles))
            story.append(Spacer(1, 5))
        for note in section.notes:
            story.append(Paragraph(_pdf_safe_text(f"- {note}"), styles["Body"]))
        story.append(Spacer(1, 4))
    doc.build(story, onFirstPage=_page_footer(brief.document_identifier), onLaterPages=_page_footer(brief.document_identifier))
    return buffer.getvalue()
