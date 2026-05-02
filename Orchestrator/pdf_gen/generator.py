"""
PackGuard — PDF Report Generator
Produces a polished downloadable PDF using ReportLab.
Includes: decision banner, failure mode table, per-mode probability bars,
narrative, recommended actions, debate log, and citations.
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def generate_pdf(report: dict, lot_id: str, output_dir: str = "/tmp") -> str:
    """
    Generate a PDF reliability report and return the file path.

    Args:
        report:     The dict returned by run_orchestrator()
        lot_id:     Lot identifier string
        output_dir: Directory to write the PDF into

    Returns:
        Absolute path to the generated PDF file
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import mm, cm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            HRFlowable, KeepTogether
        )
        from reportlab.graphics.shapes import Drawing, Rect, String, Line
        from reportlab.graphics import renderPDF
    except ImportError:
        raise ImportError("Run: pip install reportlab")

    # ── Colour palette ────────────────────────────────────────────────────────
    DARK        = colors.HexColor("#2C2C2A")
    MID         = colors.HexColor("#5F5E5A")
    LIGHT_BG    = colors.HexColor("#F1EFE8")
    SHIP_GREEN  = colors.HexColor("#1D9E75")
    HOLD_AMBER  = colors.HexColor("#BA7517")
    REJECT_RED  = colors.HexColor("#A32D2D")
    ACCENT_BLUE = colors.HexColor("#185FA5")
    WHITE       = colors.white

    DECISION_COLORS = {
        "ship":   SHIP_GREEN,
        "hold":   HOLD_AMBER,
        "reject": REJECT_RED,
    }

    decision = report.get("final_decision", "hold").lower()
    dec_color = DECISION_COLORS.get(decision, HOLD_AMBER)

    # ── File path ─────────────────────────────────────────────────────────────
    filename = f"packguard_{lot_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    path = os.path.join(output_dir, filename)

    doc = SimpleDocTemplate(
        path,
        pagesize=A4,
        topMargin=20*mm,
        bottomMargin=20*mm,
        leftMargin=20*mm,
        rightMargin=20*mm,
    )

    # ── Styles ────────────────────────────────────────────────────────────────
    styles = getSampleStyleSheet()

    H1   = ParagraphStyle("H1", fontName="Helvetica-Bold", fontSize=20,
                          textColor=DARK, leading=24, spaceAfter=2)
    H2   = ParagraphStyle("H2", fontName="Helvetica-Bold", fontSize=13,
                          textColor=DARK, leading=16, spaceBefore=14, spaceAfter=6)
    BODY = ParagraphStyle("BODY", fontName="Helvetica", fontSize=10,
                          textColor=DARK, leading=15, spaceAfter=4)
    SMALL= ParagraphStyle("SMALL", fontName="Helvetica", fontSize=8.5,
                          textColor=MID, leading=12)
    MONO = ParagraphStyle("MONO", fontName="Courier", fontSize=8.5,
                          textColor=MID, leading=12, leftIndent=8)

    story = []

    # ── Header ────────────────────────────────────────────────────────────────
    story.append(Paragraph("PackGuard Reliability Report", H1))
    story.append(Paragraph(
        f"Lot ID: <b>{lot_id}</b> &nbsp;·&nbsp; "
        f"Application: <b>{report.get('target_application', report.get('_audit', {}).get('lot_id',''))}</b> &nbsp;·&nbsp; "
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}",
        SMALL
    ))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=0.5, color=MID))
    story.append(Spacer(1, 10))

    # ── Decision banner ───────────────────────────────────────────────────────
    p_fail   = report.get("overall_p_fail", 0)
    dppm     = report.get("dppm_equivalent", p_fail * 1e6)
    cost     = report.get("cost_saved_usd", 0)
    lifetime = report.get("predicted_lifetime_years", 0)

    banner_data = [[
        Paragraph(f"<b>{decision.upper()}</b>", ParagraphStyle(
            "BAN", fontName="Helvetica-Bold", fontSize=14, textColor=WHITE, leading=16)),
        Paragraph(f"<b>P(fail)</b><br/>{p_fail:.6%}", ParagraphStyle(
            "BAN2", fontName="Helvetica", fontSize=9, textColor=WHITE, leading=13)),
        Paragraph(f"<b>DPPM equiv.</b><br/>{dppm:.2f}", ParagraphStyle(
            "BAN3", fontName="Helvetica", fontSize=9, textColor=WHITE, leading=13)),
        Paragraph(f"<b>Cost saved</b><br/>${cost:,.0f}", ParagraphStyle(
            "BAN4", fontName="Helvetica", fontSize=9, textColor=WHITE, leading=13)),
        Paragraph(f"<b>Predicted life</b><br/>{lifetime:.1f} yr", ParagraphStyle(
            "BAN5", fontName="Helvetica", fontSize=9, textColor=WHITE, leading=13)),
    ]]

    banner_table = Table(banner_data, colWidths=[60, 75, 72, 72, 72])
    banner_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), dec_color),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ("GRID",          (0, 0), (-1, -1), 0.5, colors.HexColor("#FFFFFF44")),
        ("ROUNDEDCORNERS", [6]),
    ]))
    story.append(banner_table)
    story.append(Spacer(1, 14))

    # ── Top failure modes table ───────────────────────────────────────────────
    story.append(Paragraph("Top Failure Modes", H2))

    modes = report.get("top_failure_modes", [])
    if modes:
        headers = ["Failure Mode", "P(fail)", "Physics Model", "Step", "KB Case"]
        rows = [headers]
        for m in modes[:5]:
            rows.append([
                m.get("mode", "").replace("_", " ").title(),
                f"{m.get('p_fail', 0):.5%}",
                m.get("physics_model", "—"),
                str(m.get("checkpoint", "—")),
                m.get("kb_case_id") or "—",
            ])

        col_w = [120, 60, 115, 35, 55]
        t = Table(rows, colWidths=col_w)
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), DARK),
            ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, -1), 8.5),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [LIGHT_BG, WHITE]),
            ("GRID",          (0, 0), (-1, -1), 0.4, colors.lightgrey),
            ("ALIGN",         (1, 0), (-1, -1), "CENTER"),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(t)
    else:
        story.append(Paragraph("No failure modes reported.", BODY))

    story.append(Spacer(1, 4))

    # ── Probability bars (text-based since no canvas) ─────────────────────────
    story.append(Paragraph("Per-Mode Risk Visualisation", H2))

    bar_rows = []
    for m in modes[:5]:
        pf = m.get("p_fail", 0)
        bar_len = max(1, int(pf / max(modes[0].get("p_fail", 0.01), 0.0001) * 30))
        bar = "█" * bar_len
        bar_rows.append([
            Paragraph(m.get("mode","").replace("_"," ").title(), SMALL),
            Paragraph(f'<font color="#{dec_color.hexval()[2:]}">{bar}</font> {pf:.4%}',
                      ParagraphStyle("BAR", fontName="Courier", fontSize=8, leading=12,
                                     textColor=dec_color))
        ])

    if bar_rows:
        bt = Table(bar_rows, colWidths=[130, 250])
        bt.setStyle(TableStyle([
            ("TOPPADDING",    (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(bt)

    # ── Debate Protocol ───────────────────────────────────────────────────────
    debate = report.get("_audit", {}).get("debate", {})
    if debate.get("triggered"):
        story.append(Paragraph("Debate Protocol", H2))
        story.append(Paragraph(
            f"<b>Rule {debate.get('rule_fired')} fired:</b> {debate.get('rule_description','')}",
            BODY
        ))
        story.append(Paragraph(debate.get("reasoning", ""), BODY))
        if debate.get("override_applied"):
            story.append(Paragraph(
                "<b>⚠ Override applied.</b> Debate rule overrode checkpoint decision.",
                ParagraphStyle("WARN", fontName="Helvetica-Bold", fontSize=10,
                               textColor=REJECT_RED, leading=14)
            ))

    # ── Narrative ─────────────────────────────────────────────────────────────
    story.append(Paragraph("Engineer Narrative", H2))
    narrative = report.get("narrative", "No narrative generated.")
    for para in narrative.split("\n"):
        if para.strip():
            story.append(Paragraph(para.strip(), BODY))
            story.append(Spacer(1, 3))

    # ── Recommended actions ───────────────────────────────────────────────────
    actions = report.get("recommended_actions", [])
    if actions:
        story.append(Paragraph("Recommended Actions", H2))
        for i, action in enumerate(actions, 1):
            story.append(Paragraph(f"{i}. {action}", BODY))

    # ── Confidence interval ───────────────────────────────────────────────────
    ci = report.get("confidence_interval", [0, 0])
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"Predicted lifetime: <b>{lifetime:.1f} years</b> "
        f"(90% CI: {ci[0]:.1f} – {ci[1]:.1f} years)",
        BODY
    ))

    # ── Citations ─────────────────────────────────────────────────────────────
    cites = report.get("citations", [])
    if cites:
        story.append(Paragraph("Citations & Standards", H2))
        for cite in cites:
            story.append(Paragraph(f"• {cite}", SMALL))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 12))
    story.append(HRFlowable(width="100%", thickness=0.5, color=MID))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "PackGuard v2.0 · Micron Case Study Competition 2026 · "
        "Decisions made by deterministic physics models. LLM = writer only.",
        SMALL
    ))

    doc.build(story)
    print(f"[PDF] Report saved to: {path}")
    return path


# ── CLI quick-test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Synthetic report for testing PDF layout without a full orchestrator call
    mock_report = {
        "final_decision": "reject",
        "overall_p_fail": 0.94,
        "dppm_equivalent": 940000,
        "predicted_lifetime_years": 0.3,
        "confidence_interval": [0.1, 0.5],
        "cost_saved_usd": 1847.0,
        "debate_triggered": True,
        "debate_rule_fired": 2,
        "override_applied": True,
        "top_failure_modes": [
            {"mode": "die_crack_propagation", "p_fail": 0.94,
             "physics_model": "Griffith Crack Propagation", "checkpoint": 1,
             "kb_case_id": "KB-002"},
        ],
        "recommended_actions": [
            "Kill lot immediately — do not proceed to die attach.",
            "Inspect dicing blade wear — replace blade every 500 wafer passes.",
            "Root cause: edge chip 2.1mm exceeds JEDEC JESD22-B116 1.5mm limit.",
        ],
        "narrative": (
            "LOT REJECTED. Die crack propagation detected at checkpoint 1 (dicing). "
            "Griffith Crack Propagation model predicts the 2.1mm edge chip will grow "
            "to critical fracture length at reflow step (245°C thermal shock). "
            "Survival Simulator confirms catastrophic fracture probability 94%. "
            "Continuing to die attach would waste $1,847 of processing cost per lot. "
            "Immediate action: kill lot. Replace dicing blade and recalibrate cut depth."
        ),
        "citations": [
            "JEDEC JESD22-B116 edge chip classification",
            "Griffith fracture mechanics — critical crack length formula",
            "KB-002 die crack propagation automotive BGA",
        ],
        "_audit": {
            "lot_id": "LOT-TEST-001",
            "debate": {
                "triggered": True,
                "rule_fired": 2,
                "rule_description": "SPC drift >3σ overrides specification compliance",
                "reasoning": "Process drifted 3.2σ — will be out of spec tomorrow.",
                "override_applied": True,
            },
            "per_mode_probs": {"die_crack_propagation": 0.94},
            "kb_cases_used": ["KB-002"],
        },
        "target_application": "automotive",
    }

    out = generate_pdf(mock_report, "LOT-TEST-001")
    print(f"PDF written to: {out}")
