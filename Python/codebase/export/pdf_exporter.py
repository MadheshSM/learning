"""PDF export builder with summary, charts, and tables."""

import base64
from io import BytesIO
from typing import List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from export.metadata_rows import build_export_metadata_rows
from export.models import DashboardExportSnapshot, MAX_WIDGET_ROWS

# Register Arial (supports ₹ and other Unicode symbols) with fallback to Helvetica
_FONT_NAME = "Helvetica"
_FONT_NAME_BOLD = "Helvetica-Bold"
try:
    pdfmetrics.registerFont(TTFont("Arial", "C:/Windows/Fonts/arial.ttf"))
    pdfmetrics.registerFont(TTFont("ArialBd", "C:/Windows/Fonts/arialbd.ttf"))
    _FONT_NAME = "Arial"
    _FONT_NAME_BOLD = "ArialBd"
except Exception:
    pass  # Fall back to Helvetica on non-Windows or if fonts missing


def _pdf_escape(text: object) -> str:
    s = "" if text is None else str(text)
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _decode_image(raw: str) -> BytesIO | None:
    if not raw:
        return None
    value = raw.split(",", 1)[1] if "," in raw else raw
    try:
        binary = base64.b64decode(value)
        return BytesIO(binary)
    except Exception:
        return None


def _table_flowable(rows: List[List[object]]) -> Table:
    table = Table(rows, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D1D5DB")),
                ("FONTNAME", (0, 0), (-1, 0), _FONT_NAME_BOLD),
                ("FONTNAME", (0, 1), (-1, -1), _FONT_NAME),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def build_pdf(snapshot: DashboardExportSnapshot) -> bytes:
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4, leftMargin=28, rightMargin=28, topMargin=28, bottomMargin=28)
    styles = getSampleStyleSheet()
    # Override all styles to use Unicode-capable font
    for style_name in ("Title", "Heading1", "Heading2", "Heading3", "Heading4", "BodyText", "Normal"):
        if style_name in styles:
            styles[style_name].fontName = _FONT_NAME
    for style_name in ("Title", "Heading1", "Heading2", "Heading3", "Heading4"):
        if style_name in styles:
            styles[style_name].fontName = _FONT_NAME_BOLD
    story = []

    story.append(Paragraph("Dashboard Export Report", styles["Title"]))
    story.append(Spacer(1, 0.15 * inch))
    for key, value in build_export_metadata_rows(snapshot):
        story.append(
            Paragraph(f"<b>{_pdf_escape(key)}:</b> {_pdf_escape(value)}", styles["BodyText"])
        )
    story.append(Spacer(1, 0.2 * inch))

    for widget in snapshot.widgets:
        story.append(Paragraph(widget.title, styles["Heading3"]))
        data = widget.data or {}

        image_stream = _decode_image(widget.chart_image_base64 or "")
        if image_stream:
            try:
                max_width = 6.8 * inch
                img = Image(image_stream)
                # Read the native image dimensions
                iw, ih = img.imageWidth, img.imageHeight
                if iw and ih:
                    aspect = ih / iw
                    # For pie/doughnut, cap width so the chart stays circular
                    if widget.type in ("pie", "doughnut"):
                        max_width = min(4.5 * inch, max_width)
                    display_w = min(max_width, iw)
                    display_h = display_w * aspect
                    img.drawWidth = display_w
                    img.drawHeight = display_h
                else:
                    img.drawWidth = max_width
                    img.drawHeight = 3.6 * inch
                story.append(img)
                story.append(Spacer(1, 0.08 * inch))
            except Exception:
                story.append(Paragraph("Chart image unavailable.", styles["BodyText"]))

        table_rows: List[List[object]] = []
        if widget.type == "table":
            headers = data.get("headers", [])
            rows = data.get("rows", [])
            table_rows = [headers] + rows[:MAX_WIDGET_ROWS]
            if len(rows) > MAX_WIDGET_ROWS:
                table_rows.append([f"TRUNCATED: Showing first {MAX_WIDGET_ROWS} rows"])
        elif data.get("labels") and data.get("datasets"):
            labels = data.get("labels", [])
            datasets = data.get("datasets", [])
            header = ["Label", *[ds.get("label", "Value") for ds in datasets]]
            table_rows = [header]
            for i, label in enumerate(labels[:MAX_WIDGET_ROWS]):
                row = [label]
                for ds in datasets:
                    values = ds.get("data", [])
                    row.append(values[i] if i < len(values) else "")
                table_rows.append(row)
        elif widget.type == "kpi":
            table_rows = [
                ["Metric", "Value"],
                [widget.title, data.get("value", "")],
                ["Unit", data.get("unit", "")],
                ["Change", data.get("change", "")],
                ["Trend", data.get("trend", "")],
                ["Subtitle", data.get("subtitle", "")],
            ]

        if table_rows:
            story.append(_table_flowable(table_rows))
        else:
            story.append(Paragraph("No tabular representation available.", styles["BodyText"]))
        story.append(Spacer(1, 0.2 * inch))

    doc.build(story)
    output.seek(0)
    return output.read()

