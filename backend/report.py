"""PDF Report generation service using ReportLab."""

from __future__ import annotations

import io
from pathlib import Path
from uuid import UUID
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as RLImage,
    KeepTogether,
    HRFlowable,
)

from backend.models import Scan


def generate_scan_pdf(scan: Scan, artifact_base_dir: str = "uploads/artifacts") -> bytes:
    """Generate a professional forensic PDF report from a stored Scan record."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    result_data = scan.to_scan_result()
    styles = getSampleStyleSheet()

    # Custom palette (Digital Forensics dark navy / charcoal / accent blue)
    primary_color = colors.HexColor("#0f172a")  # Slate 900
    secondary_color = colors.HexColor("#334155")  # Slate 700
    accent_color = colors.HexColor("#2563eb")  # Blue 600
    light_bg = colors.HexColor("#f8fafc")  # Slate 50
    border_color = colors.HexColor("#cbd5e1")  # Slate 300

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=primary_color,
        spaceAfter=4,
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=secondary_color,
        spaceAfter=15,
    )

    heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=primary_color,
        spaceBefore=12,
        spaceAfter=6,
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=primary_color,
    )

    muted_style = ParagraphStyle(
        'BodyMuted',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=secondary_color,
    )

    disclaimer_style = ParagraphStyle(
        'DisclaimerText',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#b45309"),  # Amber 700
    )

    story: list[any] = []

    # Header / Title
    story.append(Paragraph("PHANTOM PHOENIX", title_style))
    story.append(Paragraph("DIGITAL MEDIA AUTHENTICITY & FORENSIC INTELLIGENCE REPORT", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=accent_color, spaceAfter=12))

    # Executive Summary / Verdict Box
    verdict = result_data.get("verdict", {})
    verdict_label = verdict.get("label", "UNKNOWN")
    risk_level = verdict.get("risk", "unknown").upper()
    
    verdict_color = colors.HexColor("#16a34a") if verdict_label == "LIKELY_REAL" else (
        colors.HexColor("#dc2626") if verdict_label == "LIKELY_AI" else colors.HexColor("#d97706")
    )

    summary_data = [
        [
            Paragraph("<b>Scan ID:</b>", body_style),
            Paragraph(str(scan.id), body_style),
            Paragraph("<b>Verdict:</b>", body_style),
            Paragraph(f"<font color='{verdict_color.hexval()}'><b>{verdict_label}</b></font>", body_style),
        ],
        [
            Paragraph("<b>Timestamp (UTC):</b>", body_style),
            Paragraph(str(scan.created_at), body_style),
            Paragraph("<b>Risk Level:</b>", body_style),
            Paragraph(f"<b>{risk_level}</b>", body_style),
        ],
        [
            Paragraph("<b>File SHA-256:</b>", body_style),
            Paragraph(f"<font size=7>{scan.sha256}</font>", body_style),
            Paragraph("<b>Filename:</b>", body_style),
            Paragraph(scan.filename, body_style),
        ],
    ]

    summary_table = Table(summary_data, colWidths=[1.3 * inch, 2.7 * inch, 1.1 * inch, 1.9 * inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), light_bg),
        ('BOX', (0, 0), (-1, -1), 1, border_color),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 10))

    # Image Properties
    story.append(Paragraph("Image Properties", heading_style))
    props_data = [
        [
            Paragraph("<b>Format / Media Type:</b>", body_style),
            Paragraph(scan.media_type, body_style),
            Paragraph("<b>Dimensions:</b>", body_style),
            Paragraph(f"{scan.width} × {scan.height} px", body_style),
        ],
        [
            Paragraph("<b>File Size:</b>", body_style),
            Paragraph(f"{scan.byte_size:,} bytes", body_style),
            Paragraph("<b>Color Mode:</b>", body_style),
            Paragraph("RGB", body_style),
        ],
    ]
    props_table = Table(props_data, colWidths=[1.5 * inch, 2.5 * inch, 1.3 * inch, 1.7 * inch])
    props_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, border_color),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(props_table)
    story.append(Spacer(1, 10))

    # AI Detector Output
    story.append(Paragraph("AI Detector Inference", heading_style))
    models = result_data.get("models", [])
    if models:
        m = models[0]
        fake_prob = m.get("fake_probability")
        prob_str = f"{fake_prob:.4f} ({fake_prob * 100:.1f}%)" if fake_prob is not None else "N/A"
        model_data = [
            [Paragraph("<b>Model ID:</b>", body_style), Paragraph(m.get("model_id", "N/A"), body_style)],
            [Paragraph("<b>Fake Probability:</b>", body_style), Paragraph(prob_str, body_style)],
            [Paragraph("<b>Raw Logit:</b>", body_style), Paragraph(str(m.get("raw_logit", "N/A")), body_style)],
            [Paragraph("<b>Threshold Policy:</b>", body_style), Paragraph(m.get("threshold_policy", "N/A"), body_style)],
            [Paragraph("<b>Device / Duration:</b>", body_style), Paragraph(f"{m.get('device', 'N/A')} ({m.get('duration_seconds', 0)}s)", body_style)],
        ]
        model_table = Table(model_data, colWidths=[2.0 * inch, 5.0 * inch])
        model_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.5, border_color),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(model_table)
    else:
        story.append(Paragraph("No model inference results available.", body_style))
    story.append(Spacer(1, 10))

    # Verdict Rationale & Limitations
    story.append(Paragraph("Verdict Rationale & Limitations", heading_style))
    rationales = verdict.get("rationale", [])
    rat_text = "<br/>".join([f"• {r}" for r in rationales]) if rationales else "No rationale provided."
    story.append(Paragraph(rat_text, body_style))
    story.append(Spacer(1, 6))

    not_claimed = verdict.get("not_claimed", [])
    nc_text = "<b>Explicitly Not Claimed / Limitations:</b> " + "; ".join(not_claimed)
    story.append(Paragraph(nc_text, muted_style))
    story.append(Spacer(1, 10))

    # Forensic Indicators & Evidence Items
    story.append(Paragraph("Forensic Indicators & Evidence Assessment", heading_style))
    evidence_items = result_data.get("evidence_items", [])
    if evidence_items:
        ev_data = [[
            Paragraph("<b>Source / ID</b>", body_style),
            Paragraph("<b>Category</b>", body_style),
            Paragraph("<b>Method</b>", body_style),
            Paragraph("<b>Interpretation / Status</b>", body_style),
        ]]
        for ev in evidence_items:
            ev_data.append([
                Paragraph(f"<b>{ev.get('id')}</b>", body_style),
                Paragraph(ev.get("evidence_category", "N/A"), body_style),
                Paragraph(ev.get("method", "N/A"), body_style),
                Paragraph(ev.get("interpretation", "N/A"), body_style),
            ])
        ev_table = Table(ev_data, colWidths=[1.5 * inch, 1.4 * inch, 1.1 * inch, 3.0 * inch])
        ev_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), light_bg),
            ('BOX', (0, 0), (-1, -1), 0.5, border_color),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(ev_table)
    else:
        story.append(Paragraph("No forensic evidence items recorded.", body_style))
    story.append(Spacer(1, 10))

    # Forensic Artifact Visualizations (ELA, Noise, FFT)
    story.append(Paragraph("Forensic Artifact Visualizations", heading_style))
    artifact_flowables: list[any] = []
    
    for ind in result_data.get("indicators", []):
        artifact_rel = ind.get("artifact")
        if artifact_rel:
            art_path = Path(artifact_rel)
            if art_path.is_file():
                try:
                    img_flow = RLImage(str(art_path), width=2.0 * inch, height=2.0 * inch)
                    caption = Paragraph(f"<b>{ind.get('id').upper()} Artifact</b><br/><font size=7>{ind.get('note', '')[:80]}</font>", muted_style)
                    artifact_flowables.append([img_flow, caption])
                except Exception:
                    pass

    if artifact_flowables:
        # Arrange in pairs if possible
        grid_data = []
        row = []
        for item in artifact_flowables:
            row.extend(item)
            if len(row) == 4:  # 2 images with captions
                grid_data.append(row)
                row = []
        if row:
            while len(row) < 4:
                row.append(Paragraph("", body_style))
            grid_data.append(row)

        art_table = Table(grid_data, colWidths=[2.2 * inch, 1.3 * inch, 2.2 * inch, 1.3 * inch])
        art_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(art_table)
    else:
        story.append(Paragraph("No visual forensic artifacts available for this scan.", body_style))
    story.append(Spacer(1, 15))

    # Screening Aid Disclaimer Footer
    story.append(HRFlowable(width="100%", thickness=0.5, color=border_color, spaceAfter=8))
    story.append(Paragraph(
        "<b>DISCLAIMER:</b> This report is generated by PHANTOM PHOENIX as an automated screening aid for digital media authenticity "
        "and forensic intelligence. It provides computed observations, heuristic indicators, and model inference probabilities. "
        "It does NOT constitute legal proof, copyright verification, or definitive authentication of media provenance. "
        "All heuristic findings carry inherent limitations and must be interpreted by qualified forensic examiners.",
        disclaimer_style,
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()