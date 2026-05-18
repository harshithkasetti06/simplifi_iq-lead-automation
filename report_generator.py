"""
report_generator.py
Uses Groq (free LLaMA 3) to generate a personalized business audit report,
then converts it into a professional PDF using ReportLab.
"""

import os
import re
import logging
import json
import google.generativeai as genai
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.pdfgen import canvas
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Colors ────────────────────────────────────────────────────────────────────
DARK_BG    = colors.HexColor("#0a0a0f")
ACCENT     = colors.HexColor("#6c63ff")
ACCENT2    = colors.HexColor("#ff6584")
ACCENT3    = colors.HexColor("#43e97b")
LIGHT_TEXT = colors.HexColor("#f0f0f8")
MUTED      = colors.HexColor("#8888aa")
CARD_BG    = colors.HexColor("#16161f")
BORDER     = colors.HexColor("#2a2a3a")
WHITE      = colors.white
BLACK      = colors.black


# ─── AI Report Generation ──────────────────────────────────────────────────────

def generate_report_content(context_summary: str, lead_data: dict) -> dict:
    """
    Generate AI business audit report using Gemini.
    """

    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

    model = genai.GenerativeModel("gemini-1.5-flash")

    company = lead_data.get("company_name", "the company")
    industry = lead_data.get("industry", "")
    challenge = lead_data.get("challenge", "")

    prompt = f"""
You are a senior business consultant at SimplifiIQ.

Analyze this company and generate a professional business audit report.

COMPANY DATA:
{context_summary}

Return ONLY valid JSON.

JSON FORMAT:
{{
  "executive_summary": "",
  "company_overview": "",
  "digital_presence_score": "",
  "digital_presence_analysis": "",
  "strengths": [],
  "opportunities": [],
  "ai_automation_opportunities": [],
  "key_recommendations": [
    {{
      "title": "",
      "description": "",
      "priority": "",
      "timeline": ""
    }}
  ],
  "industry_insights": "",
  "competitive_landscape": "",
  "next_steps": "",
  "report_date": "{datetime.now().strftime('%B %d, %Y')}",
  "analyst_note": ""
}}

Industry: {industry}

Challenge:
{challenge}
"""

    try:
        response = model.generate_content(prompt)

        raw = response.text.strip()

        # Remove markdown if exists
        raw = raw.replace("```json", "").replace("```", "").strip()

        import json

        report = json.loads(raw)

        logger.info("Gemini report generated successfully.")

        return report

    except Exception as e:
        logger.error(f"Gemini error: {e}")
        

        return build_fallback_report(lead_data)


def build_fallback_report(lead_data: dict) -> dict:
    """Fallback report if AI generation fails."""
    company = lead_data.get("company_name", "Your Company")
    industry = lead_data.get("industry", "your industry")
    return {
        "executive_summary": f"{company} is a promising company in the {industry} sector. Based on our initial assessment, there are significant opportunities for growth and automation that SimplifIQ can help unlock.",
        "company_overview": f"{company} operates in the {industry} space. Our team has identified several key areas where AI-driven automation could significantly improve operations and revenue.",
        "digital_presence_score": "7/10 - Good foundation with room for improvement",
        "digital_presence_analysis": f"{company} has an established online presence. There are opportunities to enhance digital touchpoints and automate customer engagement workflows.",
        "strengths": ["Established market presence", "Clear value proposition", "Industry expertise", "Customer focus"],
        "opportunities": ["Process automation", "Lead generation optimization", "Customer experience enhancement", "Data-driven decision making"],
        "ai_automation_opportunities": ["Automated lead qualification", "AI-powered customer support", "Intelligent reporting dashboards"],
        "key_recommendations": [
            {"title": "Automate Lead Follow-up", "description": "Implement an AI-driven lead nurturing system to ensure every prospect receives timely, personalized outreach without manual effort.", "priority": "High", "timeline": "1-2 months"},
            {"title": "AI Customer Support", "description": "Deploy an intelligent chatbot to handle routine inquiries 24/7, freeing your team for high-value interactions.", "priority": "High", "timeline": "2-3 months"},
            {"title": "Data Analytics Dashboard", "description": "Create unified reporting to track key metrics and enable data-driven decisions across all departments.", "priority": "Medium", "timeline": "2-4 months"},
            {"title": "Workflow Automation", "description": "Identify and automate repetitive internal processes to reduce operational costs and improve team productivity.", "priority": "Medium", "timeline": "3-6 months"},
        ],
        "industry_insights": f"The {industry} sector is rapidly adopting AI automation tools. Companies that invest in automation now are seeing 30-40% reduction in operational costs.",
        "competitive_landscape": f"Leading companies in {industry} are leveraging AI for competitive advantage. Early adopters are gaining significant market share.",
        "next_steps": "We'd love to schedule a 30-minute discovery call to discuss your specific situation and show you exactly how SimplifIQ can help. Our team is ready to build a custom automation roadmap for you.",
        "report_date": datetime.now().strftime("%B %d, %Y"),
        "analyst_note": f"We were impressed by {company}'s clear focus on delivering value to their clients."
    }


# ─── PDF Generation ─────────────────────────────────────────────────────────────

def priority_color(priority: str):
    p = priority.lower()
    if p == "high":
        return colors.HexColor("#ff6584")
    elif p == "medium":
        return colors.HexColor("#f5a623")
    return colors.HexColor("#43e97b")


def create_pdf(report: dict, lead_data: dict, output_path: str) -> str:
    """
    Generate a professional dark-themed PDF audit report.
    Returns the output path.
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=18*mm,
        rightMargin=18*mm,
        topMargin=20*mm,
        bottomMargin=20*mm,
    )

    W, H = A4
    full_name = f"{lead_data.get('first_name', '')} {lead_data.get('last_name', '')}".strip()
    company = lead_data.get("company_name", "Company")
    industry = lead_data.get("industry", "")
    report_date = report.get("report_date", datetime.now().strftime("%B %d, %Y"))

    story = []

    # ── Styles ──────────────────────────────────────────────────────────────────
    def style(name, **kwargs):
        base = ParagraphStyle(name, **kwargs)
        return base

    s_title = style("Title",
        fontName="Helvetica-Bold", fontSize=26, textColor=WHITE,
        spaceAfter=4, leading=32)
    s_subtitle = style("Subtitle",
        fontName="Helvetica", fontSize=13, textColor=MUTED,
        spaceAfter=2)
    s_section = style("Section",
        fontName="Helvetica-Bold", fontSize=13, textColor=ACCENT,
        spaceBefore=14, spaceAfter=6, leading=16)
    s_body = style("Body",
        fontName="Helvetica", fontSize=10, textColor=LIGHT_TEXT,
        spaceAfter=6, leading=15, alignment=TA_JUSTIFY)
    s_bullet = style("Bullet",
        fontName="Helvetica", fontSize=10, textColor=LIGHT_TEXT,
        spaceAfter=4, leading=14, leftIndent=12, bulletIndent=0)
    s_card_title = style("CardTitle",
        fontName="Helvetica-Bold", fontSize=11, textColor=WHITE,
        spaceAfter=4)
    s_card_body = style("CardBody",
        fontName="Helvetica", fontSize=9, textColor=MUTED,
        spaceAfter=2, leading=13)
    s_small = style("Small",
        fontName="Helvetica", fontSize=8, textColor=MUTED)
    s_big_score = style("BigScore",
        fontName="Helvetica-Bold", fontSize=32, textColor=ACCENT,
        alignment=TA_CENTER)
    s_label = style("Label",
        fontName="Helvetica-Bold", fontSize=8, textColor=ACCENT,
        spaceAfter=2, leading=10, letterSpacing=1)
    s_white_bold = style("WhiteBold",
        fontName="Helvetica-Bold", fontSize=10, textColor=WHITE, leading=14)

    def add_section_header(title: str, icon: str = ""):
        story.append(Spacer(1, 6))
        story.append(Paragraph(f"{icon}  {title}".strip(), s_section))
        story.append(HRFlowable(
            width="100%", thickness=1,
            color=BORDER, spaceAfter=8
        ))

    def add_chip_row(items: list, chip_color=ACCENT):
        """Add colored chip-style labels in a row."""
        if not items:
            return
        chip_data = [[Paragraph(f"• {item}", style("chip",
            fontName="Helvetica", fontSize=9, textColor=WHITE,
            leading=12)) for item in items[:4]]]
        t = Table(chip_data, colWidths=[(W - 36*mm) / min(len(items), 4)] * min(len(items), 4))
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), chip_color),
            ("ROWBACKGROUNDS", (0,0), (-1,-1), [chip_color]),
            ("BOX", (0,0), (-1,-1), 0.5, BORDER),
            ("INNERGRID", (0,0), (-1,-1), 0.5, BORDER),
            ("TOPPADDING", (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LEFTPADDING", (0,0), (-1,-1), 8),
            ("RIGHTPADDING", (0,0), (-1,-1), 8),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("ROUNDEDCORNERS", [4,4,4,4]),
        ]))
        story.append(t)
        story.append(Spacer(1, 8))

    # ── COVER / HEADER ────────────────────────────────────────────────────────
    # Top header bar
    header_data = [[
        Paragraph("SIMPLIFIQ", style("logo",
            fontName="Helvetica-Bold", fontSize=18, textColor=WHITE)),
        Paragraph("AI BUSINESS INTELLIGENCE REPORT", style("tag",
            fontName="Helvetica", fontSize=8, textColor=MUTED,
            alignment=TA_LEFT))
    ]]
    header_table = Table(header_data, colWidths=[(W-36*mm)*0.4, (W-36*mm)*0.6])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), CARD_BG),
        ("TOPPADDING", (0,0), (-1,-1), 14),
        ("BOTTOMPADDING", (0,0), (-1,-1), 14),
        ("LEFTPADDING", (0,0), (-1,-1), 16),
        ("RIGHTPADDING", (0,0), (-1,-1), 16),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("BOX", (0,0), (-1,-1), 0, CARD_BG),
        ("LINEBELOW", (0,0), (-1,-1), 2, ACCENT),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 20))

    # Title area
    story.append(Paragraph("BUSINESS AUDIT REPORT", style("cover_label",
        fontName="Helvetica-Bold", fontSize=9, textColor=ACCENT,
        letterSpacing=2, spaceAfter=8)))
    story.append(Paragraph(f"Prepared for {company}", s_title))
    story.append(Paragraph(f"Attention: {full_name}  •  {industry}  •  {report_date}", s_subtitle))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=2, color=ACCENT, spaceAfter=16))

    # ── EXECUTIVE SUMMARY ────────────────────────────────────────────────────
    add_section_header("Executive Summary", "◆")
    exec_box_data = [[Paragraph(report.get("executive_summary", ""), s_body)]]
    exec_box = Table(exec_box_data, colWidths=[W - 36*mm])
    exec_box.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), CARD_BG),
        ("BOX", (0,0), (-1,-1), 1, ACCENT),
        ("TOPPADDING", (0,0), (-1,-1), 14),
        ("BOTTOMPADDING", (0,0), (-1,-1), 14),
        ("LEFTPADDING", (0,0), (-1,-1), 16),
        ("RIGHTPADDING", (0,0), (-1,-1), 16),
        ("LINEBEFORE", (0,0), (0,-1), 4, ACCENT),
    ]))
    story.append(exec_box)

    # Analyst note
    if report.get("analyst_note"):
        story.append(Spacer(1, 6))
        story.append(Paragraph(f"💡 {report['analyst_note']}", style("analyst",
            fontName="Helvetica-Oblique", fontSize=9, textColor=MUTED,
            leading=14, leftIndent=8)))

    story.append(Spacer(1, 10))

    # ── COMPANY OVERVIEW + DIGITAL SCORE (side by side) ──────────────────────
    score_text = report.get("digital_presence_score", "7/10")
    score_num = score_text.split("/")[0].strip() if "/" in score_text else score_text.split()[0]

    overview_col = [
        Paragraph("COMPANY OVERVIEW", s_label),
        Paragraph(report.get("company_overview", ""), s_body),
    ]
    score_col = [
        Paragraph("DIGITAL PRESENCE SCORE", style("scoreLabel",
            fontName="Helvetica-Bold", fontSize=8, textColor=ACCENT,
            alignment=TA_CENTER, spaceAfter=4)),
        Paragraph(score_num, s_big_score),
        Paragraph("out of 10", style("outof",
            fontName="Helvetica", fontSize=9, textColor=MUTED,
            alignment=TA_CENTER, spaceAfter=6)),
        Paragraph(report.get("digital_presence_analysis", ""), style("scoreBody",
            fontName="Helvetica", fontSize=9, textColor=MUTED,
            leading=13, alignment=TA_CENTER)),
    ]

    from reportlab.platypus import KeepInFrame
    col_w = W - 36*mm
    overview_frame = [[p] for p in overview_col]
    score_frame = [[p] for p in score_col]

    two_col = Table(
        [[
            [Paragraph("COMPANY OVERVIEW", s_label)] + [Paragraph(report.get("company_overview",""), s_body)],
            [Paragraph("DIGITAL SCORE", style("sl2",fontName="Helvetica-Bold",fontSize=8,textColor=ACCENT,alignment=TA_CENTER,spaceAfter=4)),
             Paragraph(score_num, s_big_score),
             Paragraph("/ 10", style("o2",fontName="Helvetica",fontSize=9,textColor=MUTED,alignment=TA_CENTER,spaceAfter=6)),
             Paragraph(report.get("digital_presence_analysis",""), style("sb2",fontName="Helvetica",fontSize=9,textColor=MUTED,leading=13,alignment=TA_CENTER))]
        ]],
        colWidths=[col_w * 0.62, col_w * 0.35],
        rowHeights=None,
    )
    two_col.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,0), CARD_BG),
        ("BACKGROUND", (1,0), (1,0), CARD_BG),
        ("BOX", (0,0), (0,0), 0.5, BORDER),
        ("BOX", (1,0), (1,0), 0.5, ACCENT),
        ("TOPPADDING", (0,0), (-1,-1), 14),
        ("BOTTOMPADDING", (0,0), (-1,-1), 14),
        ("LEFTPADDING", (0,0), (-1,-1), 14),
        ("RIGHTPADDING", (0,0), (-1,-1), 14),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("VALIGN", (1,0), (1,0), "MIDDLE"),
        ("ALIGN", (1,0), (1,0), "CENTER"),
        ("COLPADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(two_col)
    story.append(Spacer(1, 12))

    # ── STRENGTHS + OPPORTUNITIES ─────────────────────────────────────────────
    add_section_header("Strengths & Opportunities")

    strengths = report.get("strengths", [])
    opportunities = report.get("opportunities", [])

    def make_list_col(title, items, accent_col):
        rows = [[Paragraph(title, style("ct",fontName="Helvetica-Bold",fontSize=10,textColor=accent_col,spaceAfter=8))]]
        for item in items:
            rows.append([Paragraph(f"  ▸  {item}", style("li",fontName="Helvetica",fontSize=9,textColor=LIGHT_TEXT,leading=14,spaceAfter=4))])
        return rows

    s_rows = make_list_col("✦ Strengths", strengths, ACCENT3)
    o_rows = make_list_col("✦ Opportunities", opportunities, ACCENT2)

    max_rows = max(len(s_rows), len(o_rows))
    while len(s_rows) < max_rows: s_rows.append([Paragraph("")])
    while len(o_rows) < max_rows: o_rows.append([Paragraph("")])

    combined = [[s_rows[i][0], o_rows[i][0]] for i in range(max_rows)]
    so_table = Table(combined, colWidths=[col_w * 0.49, col_w * 0.49])
    so_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,-1), CARD_BG),
        ("BACKGROUND", (1,0), (1,-1), CARD_BG),
        ("BOX", (0,0), (0,-1), 0.5, BORDER),
        ("BOX", (1,0), (1,-1), 0.5, BORDER),
        ("TOPPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING", (0,0), (-1,-1), 12),
        ("RIGHTPADDING", (0,0), (-1,-1), 12),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("COLPADDING", (0,0), (-1,-1), 8),
    ]))
    story.append(so_table)
    story.append(Spacer(1, 12))

    # ── AI AUTOMATION OPPORTUNITIES ──────────────────────────────────────────
    add_section_header("AI Automation Opportunities", "⚡")
    ai_ops = report.get("ai_automation_opportunities", [])
    for i, op in enumerate(ai_ops):
        row = Table(
            [[Paragraph(f"0{i+1}", style("num",fontName="Helvetica-Bold",fontSize=20,textColor=ACCENT,alignment=TA_CENTER)),
              Paragraph(op, style("aibody",fontName="Helvetica",fontSize=10,textColor=LIGHT_TEXT,leading=14))]],
            colWidths=[40, col_w - 40]
        )
        row.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), CARD_BG),
            ("BOX", (0,0), (-1,-1), 0.5, BORDER),
            ("LINEBEFORE", (0,0), (0,-1), 3, ACCENT),
            ("TOPPADDING", (0,0), (-1,-1), 12),
            ("BOTTOMPADDING", (0,0), (-1,-1), 12),
            ("LEFTPADDING", (0,0), (-1,-1), 12),
            ("RIGHTPADDING", (0,0), (-1,-1), 12),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ]))
        story.append(row)
        story.append(Spacer(1, 6))

    story.append(Spacer(1, 8))

    # ── KEY RECOMMENDATIONS ──────────────────────────────────────────────────
    add_section_header("Key Recommendations", "◈")
    recommendations = report.get("key_recommendations", [])

    for rec in recommendations:
        pri = rec.get("priority", "Medium")
        pri_col = priority_color(pri)
        timeline = rec.get("timeline", "")

        header_row = [
            Paragraph(rec.get("title", ""), s_card_title),
            Paragraph(f"● {pri}", style("pri",fontName="Helvetica-Bold",fontSize=8,textColor=pri_col,alignment=TA_LEFT)),
            Paragraph(f"⏱ {timeline}", style("tl",fontName="Helvetica",fontSize=8,textColor=MUTED,alignment=TA_LEFT)),
        ]
        body_row = [
            Paragraph(rec.get("description", ""), style("recdesc",fontName="Helvetica",fontSize=9,textColor=MUTED,leading=13)),
            Paragraph(""), Paragraph("")
        ]

        rec_table = Table(
            [header_row, body_row],
            colWidths=[col_w * 0.55, col_w * 0.22, col_w * 0.21],
        )
        rec_table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), CARD_BG),
            ("BOX", (0,0), (-1,-1), 0.5, BORDER),
            ("LINEBEFORE", (0,0), (0,-1), 3, pri_col),
            ("TOPPADDING", (0,0), (-1,0), 12),
            ("BOTTOMPADDING", (0,-1), (-1,-1), 12),
            ("TOPPADDING", (0,1), (-1,-1), 4),
            ("LEFTPADDING", (0,0), (-1,-1), 14),
            ("RIGHTPADDING", (0,0), (-1,-1), 10),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("SPAN", (0,1), (-1,1)),
        ]))
        story.append(rec_table)
        story.append(Spacer(1, 8))

    story.append(Spacer(1, 6))

    # ── INDUSTRY INSIGHTS + COMPETITIVE LANDSCAPE ─────────────────────────────
    add_section_header("Industry Insights", "◉")
    ins_data = [
        [Paragraph("Industry Trends", style("it",fontName="Helvetica-Bold",fontSize=10,textColor=ACCENT3,spaceAfter=6)),
         Paragraph("Competitive Landscape", style("cl",fontName="Helvetica-Bold",fontSize=10,textColor=ACCENT2,spaceAfter=6))],
        [Paragraph(report.get("industry_insights",""), s_card_body),
         Paragraph(report.get("competitive_landscape",""), s_card_body)],
    ]
    ins_table = Table(ins_data, colWidths=[col_w*0.49, col_w*0.49])
    ins_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), CARD_BG),
        ("BOX", (0,0), (0,-1), 0.5, BORDER),
        ("BOX", (1,0), (1,-1), 0.5, BORDER),
        ("TOPPADDING", (0,0), (-1,-1), 12),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ("LEFTPADDING", (0,0), (-1,-1), 14),
        ("RIGHTPADDING", (0,0), (-1,-1), 14),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("COLPADDING", (0,0), (-1,-1), 8),
    ]))
    story.append(ins_table)
    story.append(Spacer(1, 12))

    # ── NEXT STEPS ──────────────────────────────────────────────────────────
    add_section_header("Next Steps", "→")
    ns_data = [[
        Paragraph("🚀", style("rocket",fontName="Helvetica",fontSize=24,alignment=TA_CENTER)),
        Paragraph(report.get("next_steps",""), style("ns",fontName="Helvetica",fontSize=10,textColor=LIGHT_TEXT,leading=15))
    ]]
    ns_table = Table(ns_data, colWidths=[40, col_w - 40])
    ns_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), CARD_BG),
        ("BOX", (0,0), (-1,-1), 1, ACCENT),
        ("LINEBELOW", (0,-1), (-1,-1), 3, ACCENT),
        ("TOPPADDING", (0,0), (-1,-1), 16),
        ("BOTTOMPADDING", (0,0), (-1,-1), 16),
        ("LEFTPADDING", (0,0), (-1,-1), 14),
        ("RIGHTPADDING", (0,0), (-1,-1), 14),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(ns_table)
    story.append(Spacer(1, 16))

    # ── FOOTER ──────────────────────────────────────────────────────────────
    footer_data = [[
        Paragraph("SimplifIQ  •  Simplifying AI Adoption for Businesses", style("fl",fontName="Helvetica-Bold",fontSize=9,textColor=MUTED)),
        Paragraph(f"Generated: {report_date}  •  simplifiq.com", style("fr",fontName="Helvetica",fontSize=8,textColor=MUTED,alignment=TA_LEFT)),
    ]]
    footer_table = Table(footer_data, colWidths=[col_w * 0.6, col_w * 0.4])
    footer_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), CARD_BG),
        ("TOPPADDING", (0,0), (-1,-1), 12),
        ("BOTTOMPADDING", (0,0), (-1,-1), 12),
        ("LEFTPADDING", (0,0), (-1,-1), 16),
        ("RIGHTPADDING", (0,0), (-1,-1), 16),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LINEABOVE", (0,0), (-1,0), 1, BORDER),
    ]))
    story.append(footer_table)

    # Build PDF with dark background
    def dark_background(canvas_obj, doc):
        canvas_obj.saveState()
        canvas_obj.setFillColor(DARK_BG)
        canvas_obj.rect(0, 0, W, H, fill=True, stroke=False)
        canvas_obj.restoreState()

    doc.build(story, onFirstPage=dark_background, onLaterPages=dark_background)
    logger.info(f"PDF generated: {output_path}")
    return output_path


def generate_full_report(lead_data: dict, context_summary: str, output_dir: str = "generated_pdfs") -> str:
    """
    Full pipeline: generate AI content → create PDF → return PDF path.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Generate AI content
    report = generate_report_content(context_summary, lead_data)

    # Build PDF filename
    company_slug = re.sub(r'[^a-zA-Z0-9]', '_', lead_data.get("company_name", "report")).lower()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{company_slug}_audit_{timestamp}.pdf"
    output_path = os.path.join(output_dir, filename)

    # Generate PDF
    create_pdf(report, lead_data, output_path)
    return output_path