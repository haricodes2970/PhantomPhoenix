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

    # Forensic Artifact Visualizations (ELA, Noise, FFT, Grad-CAM)
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

    # Also include Grad-CAM from explainability if available
    explainability = result_data.get("explainability", {})
    if explainability.get("artifact"):
        art_path = Path(explainability["artifact"])
        if art_path.is_file():
            try:
                img_flow = RLImage(str(art_path), width=2.0 * inch, height=2.0 * inch)
                caption = Paragraph(f"<b>GRAD-CAM Artifact</b><br/><font size=7>ViT attention rollout heatmap</font>", muted_style)
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

    # Six-Part Investigator Evidence Report
    story.append(HRFlowable(width="100%", thickness=1.5, color=accent_color, spaceAfter=10))
    story.append(Paragraph("INVESTIGATOR EVIDENCE REPORT (Six-Part Structure)", heading_style))
    story.append(Spacer(1, 6))

    investigator_report = result_data.get("investigator_report")
    if investigator_report:
        render_investigator_report_sections(story, investigator_report, body_style, muted_style, heading_style, border_color, light_bg)
    else:
        story.append(Paragraph("Investigator evidence report not available for this scan.", body_style))

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


def render_investigator_report_sections(
    story: list[Any],
    report: dict[str, Any],
    body_style: ParagraphStyle,
    muted_style: ParagraphStyle,
    heading_style: ParagraphStyle,
    border_color: colors.Color,
    light_bg: colors.Color,
) -> None:
    """Render all six sections of the investigator evidence report."""

    def safe_text(val: Any) -> str:
        """Convert value to safe string for Paragraph."""
        if val is None:
            return "N/A"
        return str(val)

    def section_heading(title: str) -> None:
        story.append(Paragraph(title, heading_style))
        story.append(Spacer(1, 4))

    def key_value_table(data: list[list], col_widths: list[float]) -> None:
        table = Table(data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), light_bg),
            ('BOX', (0, 0), (-1, -1), 0.5, border_color),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(table)
        story.append(Spacer(1, 8))

    def bullet_list(items: list[str]) -> None:
        if not items:
            story.append(Paragraph("<i>None</i>", muted_style))
        else:
            for item in items:
                story.append(Paragraph(f"• {safe_text(item)}", body_style))
        story.append(Spacer(1, 4))

    # Section 1: File Integrity & Provenance
    section_heading("Section 1: File Integrity & Provenance")
    s1 = report.get("section_1_file_integrity", {})
    s1_data = [
        [Paragraph("<b>SHA-256:</b>", body_style), Paragraph(f"<font size=7>{safe_text(s1.get('sha256'))}</font>", body_style)],
        [Paragraph("<b>Original Filename:</b>", body_style), Paragraph(safe_text(s1.get('original_filename')), body_style)],
        [Paragraph("<b>Internal Identifier:</b>", body_style), Paragraph(safe_text(s1.get('internal_identifier')), body_style)],
        [Paragraph("<b>File Format:</b>", body_style), Paragraph(safe_text(s1.get('file_format')), body_style)],
        [Paragraph("<b>Dimensions:</b>", body_style), Paragraph(safe_text(s1.get('dimensions')), body_style)],
        [Paragraph("<b>File Size:</b>", body_style), Paragraph(f"{s1.get('file_size_bytes', 0):,} bytes", body_style)],
        [Paragraph("<b>Integrity Status:</b>", body_style), Paragraph(safe_text(s1.get('integrity_status')), body_style)],
        [Paragraph("<b>Provenance Status:</b>", body_style), Paragraph(safe_text(s1.get('provenance_status')), body_style)],
        [Paragraph("<b>Scan ID:</b>", body_style), Paragraph(safe_text(s1.get('scan_id')), body_style)],
        [Paragraph("<b>Analysis Timestamp (UTC):</b>", body_style), Paragraph(safe_text(s1.get('analysis_timestamp_utc')), body_style)],
    ]
    key_value_table(s1_data, [2.0 * inch, 5.0 * inch])

    if s1.get('exif_fields'):
        story.append(Paragraph("<b>EXIF Fields (sample):</b>", body_style))
        for k, v in list(s1['exif_fields'].items())[:10]:
            story.append(Paragraph(f"  {safe_text(k)}: {safe_text(v)}", muted_style))
    if s1.get('missing_metadata_observations'):
        story.append(Paragraph("<b>Missing Metadata Observations:</b>", body_style))
        bullet_list(s1['missing_metadata_observations'])

    # Section 2: Source Discovery
    section_heading("Section 2: Source Discovery")
    s2 = report.get("section_2_source_discovery", {})
    s2_data = [
        [Paragraph("<b>Status:</b>", body_style), Paragraph(safe_text(s2.get('status')).upper(), body_style)],
        [Paragraph("<b>Match Method:</b>", body_style), Paragraph(safe_text(s2.get('match_method')), body_style)],
        [Paragraph("<b>Match Strength:</b>", body_style), Paragraph(safe_text(s2.get('match_strength')), body_style)],
        [Paragraph("<b>Earliest Known Source:</b>", body_style), Paragraph("Yes" if s2.get('earliest_known_source') else "No", body_style)],
    ]
    key_value_table(s2_data, [2.0 * inch, 5.0 * inch])
    if s2.get('candidate_urls'):
        story.append(Paragraph("<b>Candidate URLs:</b>", body_style))
        bullet_list(s2['candidate_urls'])
    if s2.get('supporting_evidence'):
        story.append(Paragraph("<b>Supporting Evidence:</b>", body_style))
        bullet_list(s2['supporting_evidence'])
    if s2.get('limitations'):
        story.append(Paragraph("<b>Limitations:</b>", body_style))
        bullet_list(s2['limitations'])

    # Section 3: Publisher Intelligence
    section_heading("Section 3: Publisher & Account Intelligence")
    s3 = report.get("section_3_publisher_intelligence", {})
    s3_data = [
        [Paragraph("<b>Status:</b>", body_style), Paragraph(safe_text(s3.get('status')).upper(), body_style)],
        [Paragraph("<b>Account Name:</b>", body_style), Paragraph(safe_text(s3.get('account_name')), body_style)],
        [Paragraph("<b>Source URL:</b>", body_style), Paragraph(safe_text(s3.get('source_url')), body_style)],
        [Paragraph("<b>Relationship:</b>", body_style), Paragraph(safe_text(s3.get('relationship')), body_style)],
        [Paragraph("<b>Verification Status:</b>", body_style), Paragraph(safe_text(s3.get('verification_status')), body_style)],
    ]
    key_value_table(s3_data, [2.0 * inch, 5.0 * inch])
    if s3.get('limitations'):
        story.append(Paragraph("<b>Limitations:</b>", body_style))
        bullet_list(s3['limitations'])

    # Section 4: Generator Attribution
    section_heading("Section 4: Generator & Editing Attribution")
    s4 = report.get("section_4_generator_attribution", {})
    s4_data = [
        [Paragraph("<b>Status:</b>", body_style), Paragraph(safe_text(s4.get('status')).upper(), body_style)],
        [Paragraph("<b>Method:</b>", body_style), Paragraph(safe_text(s4.get('method')), body_style)],
    ]
    key_value_table(s4_data, [2.0 * inch, 5.0 * inch])
    candidates = s4.get('candidates', [])
    if candidates:
        story.append(Paragraph("<b>Candidate Families:</b>", body_style))
        for c in candidates:
            fam = safe_text(c.get('family'))
            conf = c.get('confidence', 0)
            ev_type = safe_text(c.get('evidence_type'))
            story.append(Paragraph(f"  • {fam}: confidence {conf:.2f} (evidence: {ev_type})", body_style))
    else:
        story.append(Paragraph("<i>No candidate families identified</i>", muted_style))
    if s4.get('limitations'):
        story.append(Paragraph("<b>Limitations:</b>", body_style))
        bullet_list(s4['limitations'])

    # Section 5: External Investigation Evidence
    section_heading("Section 5: External Investigation Evidence")
    s5 = report.get("section_5_external_evidence", {})
    s5_data = [
        [Paragraph("<b>Status:</b>", body_style), Paragraph(safe_text(s5.get('status')).upper(), body_style)],
        [Paragraph("<b>Source:</b>", body_style), Paragraph(safe_text(s5.get('source')), body_style)],
        [Paragraph("<b>Retrieval Time (UTC):</b>", body_style), Paragraph(safe_text(s5.get('retrieval_time_utc')), body_style)],
        [Paragraph("<b>Verification Status:</b>", body_style), Paragraph(safe_text(s5.get('verification_status')), body_style)],
    ]
    key_value_table(s5_data, [2.0 * inch, 5.0 * inch])
    if s5.get('platform_records'):
        story.append(Paragraph("<b>Platform Records:</b>", body_style))
        bullet_list([str(r) for r in s5['platform_records']])
    if s5.get('public_urls'):
        story.append(Paragraph("<b>Public URLs:</b>", body_style))
        bullet_list(s5['public_urls'])
    if s5.get('access_limitations'):
        story.append(Paragraph("<b>Access Limitations:</b>", body_style))
        bullet_list(s5['access_limitations'])

    # Section 6: Evidence Preservation & Corroboration
    section_heading("Section 6: Evidence Preservation & Corroboration")
    s6 = report.get("section_6_evidence_preservation", {})
    s6_data = [
        [Paragraph("<b>Original File Hash:</b>", body_style), Paragraph(f"<font size=7>{safe_text(s6.get('original_file_hash'))}</font>", body_style)],
        [Paragraph("<b>Scan Identifier:</b>", body_style), Paragraph(safe_text(s6.get('scan_identifier')), body_style)],
        [Paragraph("<b>Analysis Timestamp (UTC):</b>", body_style), Paragraph(safe_text(s6.get('analysis_timestamp_utc')), body_style)],
        [Paragraph("<b>Detector Version:</b>", body_style), Paragraph(safe_text(s6.get('detector_version')), body_style)],
        [Paragraph("<b>Corroboration Status:</b>", body_style), Paragraph(safe_text(s6.get('corroboration_status')).upper(), body_style)],
    ]
    key_value_table(s6_data, [2.0 * inch, 5.0 * inch])

    if s6.get('forensic_versions'):
        story.append(Paragraph("<b>Forensic Module Versions:</b>", body_style))
        for k, v in s6['forensic_versions'].items():
            story.append(Paragraph(f"  {safe_text(k)}: {safe_text(v)}", muted_style))

    if s6.get('supporting_observations'):
        story.append(Paragraph("<b>Supporting Observations:</b>", body_style))
        bullet_list(s6['supporting_observations'])

    if s6.get('artifact_references'):
        story.append(Paragraph("<b>Artifact References:</b>", body_style))
        bullet_list(s6['artifact_references'])

    if s6.get('evidence_relationships'):
        story.append(Paragraph("<b>Evidence Relationships:</b>", body_style))
        bullet_list(s6['evidence_relationships'])

    if s6.get('integrity_checks'):
        story.append(Paragraph("<b>Integrity Checks:</b>", body_style))
        bullet_list(s6['integrity_checks'])

    if s6.get('outstanding_questions'):
        story.append(Paragraph("<b>Outstanding Questions:</b>", body_style))
        bullet_list(s6['outstanding_questions'])