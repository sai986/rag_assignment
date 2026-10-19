from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, Preformatted, SimpleDocTemplate, Spacer, Table, TableStyle


REPORT_MD = Path("report/report.md")
REPORT_PDF = Path("report/report.pdf")


styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="TitleCustom", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=18, leading=22, spaceAfter=14))
styles.add(ParagraphStyle(name="H2Custom", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=13, leading=16, spaceBefore=12, spaceAfter=6))
styles.add(ParagraphStyle(name="H3Custom", parent=styles["Heading3"], fontName="Helvetica-Bold", fontSize=11, leading=14, spaceBefore=9, spaceAfter=5))
styles.add(ParagraphStyle(name="BodyCustom", parent=styles["BodyText"], fontSize=9.2, leading=12, spaceAfter=5))
styles.add(ParagraphStyle(name="BulletCustom", parent=styles["BodyText"], fontSize=9.2, leading=12, leftIndent=14, firstLineIndent=-8, spaceAfter=3))
styles.add(ParagraphStyle(name="SmallCustom", parent=styles["BodyText"], fontSize=7.8, leading=9.5, spaceAfter=3))
styles.add(ParagraphStyle(name="CodeCustom", parent=styles["Code"], fontName="Courier", fontSize=7.5, leading=9, backColor=colors.whitesmoke, borderPadding=4, spaceAfter=6))


inline_code_re = re.compile(r"`([^`]+)`")
bold_re = re.compile(r"\*\*([^*]+)\*\*")
link_re = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline_markdown(text: str) -> str:
    text = escape_html(text)
    text = bold_re.sub(r"<b>\1</b>", text)
    text = inline_code_re.sub(r'<font name="Courier">\1</font>', text)
    text = link_re.sub(r"<u>\1</u> (\2)", text)
    return text


def split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def table_widths(header: list[str], available_width: float) -> list[float]:
    key = tuple(header)
    policies = {
        ("Metric", "Value"): [0.68, 0.32],
        ("Query", "Chunk", "Baseline Rank", "Re-ranked Rank", "Page Range", "Shift"): [0.47, 0.09, 0.11, 0.12, 0.13, 0.08],
        ("Chunk", "Baseline Rank", "Re-ranked Rank", "Page Range", "Reason"): [0.10, 0.12, 0.13, 0.13, 0.52],
        ("Pipeline", "Observation"): [0.22, 0.78],
        ("Measurement", "Baseline Retrieval Time", "Re-ranking Time", "Total Re-ranking Pipeline Time"): [0.43, 0.19, 0.18, 0.20],
        ("Query", "Baseline Retrieval Time", "Re-ranking Time", "Total Re-ranking Pipeline Time"): [0.46, 0.18, 0.17, 0.19],
    }
    weights = policies.get(key)
    if weights is None:
        weights = [1 / len(header)] * len(header)
    return [available_width * weight for weight in weights]


def build_table(rows: list[list[str]], available_width: float) -> Table:
    data = [[Paragraph(inline_markdown(cell), styles["SmallCustom"]) for cell in row] for row in rows]
    table = Table(data, colWidths=table_widths(rows[0], available_width), repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e9edf5")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#b9c0cc")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def markdown_to_story(text: str, available_width: float) -> list:
    story = []
    lines = text.splitlines()
    i = 0

    while i < len(lines):
        line = lines[i].rstrip()
        if not line.strip():
            i += 1
            continue

        if line.startswith("```"):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1
            story.append(Preformatted("\n".join(code_lines), styles["CodeCustom"]))
            continue

        if line.startswith("# "):
            story.append(Paragraph(inline_markdown(line[2:].strip()), styles["TitleCustom"]))
            i += 1
            continue

        if line.startswith("## "):
            story.append(Paragraph(inline_markdown(line[3:].strip()), styles["H2Custom"]))
            i += 1
            continue

        if line.startswith("### "):
            story.append(Paragraph(inline_markdown(line[4:].strip()), styles["H3Custom"]))
            i += 1
            continue

        if line.startswith("|") and i + 1 < len(lines) and lines[i + 1].startswith("|"):
            separator = lines[i + 1].replace("|", "").replace(":", "").replace("-", "").strip()
            if not separator:
                rows = [split_table_row(line)]
                i += 2
                while i < len(lines) and lines[i].startswith("|"):
                    rows.append(split_table_row(lines[i]))
                    i += 1
                story.append(build_table(rows, available_width))
                story.append(Spacer(1, 6))
                continue

        if line.startswith("- "):
            story.append(Paragraph("&bull; " + inline_markdown(line[2:].strip()), styles["BulletCustom"]))
            i += 1
            continue

        if re.match(r"^\d+\.\s+", line):
            story.append(Paragraph(inline_markdown(line.strip()), styles["BulletCustom"]))
            i += 1
            continue

        paragraph = [line.strip()]
        i += 1
        while i < len(lines):
            next_line = lines[i].rstrip()
            if not next_line.strip() or next_line.startswith(("#", "```", "|", "- ")) or re.match(r"^\d+\.\s+", next_line):
                break
            paragraph.append(next_line.strip())
            i += 1
        story.append(Paragraph(inline_markdown(" ".join(paragraph)), styles["BodyCustom"]))

    return story


def main() -> None:
    text = REPORT_MD.read_text(encoding="utf-8")
    margin = 0.7 * inch
    available_width = A4[0] - (2 * margin)
    doc = SimpleDocTemplate(
        str(REPORT_PDF),
        pagesize=A4,
        rightMargin=margin,
        leftMargin=margin,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
    )
    doc.build(markdown_to_story(text, available_width))
    print(f"Wrote {REPORT_PDF}")


if __name__ == "__main__":
    main()
