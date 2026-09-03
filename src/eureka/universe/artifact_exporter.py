"""
Artifact export subsystem for EUREKA.

Turns a CanonicalWorkState into real, downloadable artifacts. Unlike a plain LLM
that only streams text, EUREKA renders its *mathematical / cognitive layer* —
the ACFL fuzzy satisfaction matrix and the Pareto frontier — into every format,
so the export carries the decision math, not just prose.

Formats:
    txt    -> plain text
    md     -> markdown
    docx   -> Word (python-docx)
    pdf    -> PDF  (reportlab)
    pptx   -> presentation (python-pptx)
    png    -> bitmap of the ACFL decision surface (matplotlib)
    svg    -> vector of the ACFL decision surface (matplotlib)

Design: a single build_export_payload() normalizes the canonical state into plain
data; _build_content() turns that payload into a format-agnostic content model
(headings / paragraphs / bullets / tables / kv). Each renderer walks that model, so
the four document formats stay consistent. Chart formats (png/svg) render directly
from the payload.
"""
from __future__ import annotations

import io
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .canonical_state import CanonicalWorkState

# --------------------------------------------------------------------------- #
# Payload normalization
# --------------------------------------------------------------------------- #

def _s(v: Optional[Any]) -> str:
    """Coerce anything to a safe string, tolerating None."""
    if v is None:
        return ""
    if isinstance(v, (list, tuple)):
        return ", ".join(str(x) for x in v)
    return str(v)


def _wscore(canonical: CanonicalWorkState, alt: str, crit: str, scores: Dict[str, Any], weights: Dict[str, float]) -> float:
    """Weighted satisfaction contribution of a single criterion for an alternative."""
    try:
        return float(scores.get(alt, {}).get(crit, 0.0))
    except (TypeError, ValueError):
        return 0.0


def weighted_total(canonical: CanonicalWorkState, alt: str, scores: Dict[str, Any], weights: Dict[str, float], criteria: Optional[List[str]] = None) -> float:
    """Weighted mean satisfaction (0..1) for an alternative across its criteria.

    Falls back to equal weighting for any criterion not covered by the declared
    weights (so a mismatched weight table never fabricates a score).
    """
    criteria = criteria or canonical.acfl.criteria or []
    if not criteria:
        return 0.0
    num = 0.0
    den = 0.0
    for c in criteria:
        w = float(weights.get(c, 0.5) or 0.5)
        num += w * _wscore(canonical, alt, c, scores, weights)
        den += w
    return round(num / den, 3) if den else 0.0


def _dominates(x: str, y: str, scores: Dict[str, Any]) -> bool:
    """True if alternative x strictly Pareto-dominates y on every shared criterion."""
    rx = scores.get(x, {}) or {}
    ry = scores.get(y, {}) or {}
    keys = set(rx.keys()) | set(ry.keys())
    if not keys:
        return False
    strictly_better = False
    for k in keys:
        vx = float(rx.get(k, 0.0) or 0.0)
        vy = float(ry.get(k, 0.0) or 0.0)
        if vx < vy:
            return False
        if vx > vy:
            strictly_better = True
    return strictly_better


def pareto_frontier(alternatives: List[str], scores: Dict[str, Any]) -> List[str]:
    """Derive the Pareto-optimal (non-dominated) subset from the satisfaction matrix."""
    return [a for a in alternatives if not any(_dominates(b, a, scores) for b in alternatives if b != a)]


def best_frontier_label(payload: Dict[str, Any], alt: str) -> str:
    """Prefer the declared alternative id, then its human description if known."""
    label = payload.get("alt_labels", {}).get(alt, alt)
    return label


def build_export_payload(canonical: CanonicalWorkState) -> Dict[str, Any]:
    """Flatten a CanonicalWorkState into plain JSON-able data for rendering."""
    result = canonical.result
    acfl = canonical.acfl
    problem = canonical.problem
    work = canonical.work
    frozen = canonical.frozen_result

    # Friendly labels for alternatives (from the prescription model when present).
    alt_labels: Dict[str, str] = {}
    if canonical.prescriptive_knowledge and canonical.prescriptive_knowledge.prescriptions:
        for presc in canonical.prescriptive_knowledge.prescriptions:
            for alt in (presc.alternatives or []):
                alt_ids = getattr(alt, "alternative_id", None)
                desc = getattr(alt, "description", None) or getattr(alt, "title", None) or ""
                if alt_ids and desc:
                    alt_labels[alt_ids] = desc if len(desc) <= 90 else desc[:87] + "..."

    story_arc = []
    if canonical.extracted_entities:
        story_arc = canonical.extracted_entities.get("story_arc", []) or []

    # Weighted satisfaction table. ACFL may leave alternatives/criteria empty; we
    # derive them from the normalized_scores matrix so the fuzzy layer is still
    # rendered when the prescriptor populated scores but not the meta lists.
    scores = acfl.normalized_scores or {}
    weights = acfl.weights or {}
    criteria = list(acfl.criteria or [])
    alternatives = list(acfl.alternatives or [])

    if not criteria and isinstance(scores, dict):
        for _a, row in scores.items():
            if isinstance(row, dict) and row:
                criteria = list(row.keys())
                break
    if not alternatives and isinstance(scores, dict):
        alternatives = [k for k, v in scores.items() if isinstance(v, dict)]

    weighted = {a: weighted_total(canonical, a, scores, weights, criteria) for a in alternatives}

    # Frontier: trust the declared ACFL frontier; otherwise derive the Pareto-optimal
    # set from the satisfaction matrix (a genuine mathematical derivation, not a guess).
    frontier = list(acfl.frontier or [])
    derived_frontier = False
    if not frontier and criteria and alternatives:
        frontier = pareto_frontier(alternatives, scores)
        derived_frontier = bool(frontier)

    # Human-selected alternative (the operator's decision that sits alongside the math).
    selected_alternative = None
    if canonical.prescriptive_knowledge and canonical.prescriptive_knowledge.prescriptions:
        presc = canonical.prescriptive_knowledge.prescriptions[-1]
        sel = getattr(presc, "selected_alternative", None)
        if sel is not None:
            selected_alternative = getattr(sel, "alternative_id", None) if not isinstance(sel, str) else sel

    em_pipeline = []
    for em in (canonical.em_pipeline or []):
        em_pipeline.append({"em": getattr(em, "canonical_em", ""), "status": getattr(em, "status", "")})

    exec_steps = []
    for st in (canonical.execution_plan.steps if canonical.execution_plan else []):
        exec_steps.append({
            "step_id": getattr(st, "step_id", ""),
            "capability": getattr(st, "capability_id", ""),
            "em": getattr(st, "canonical_em", ""),
            "status": getattr(st, "status", ""),
        })

    return {
        "work_id": getattr(work, "work_id", ""),
        "title": getattr(work, "title", ""),
        "user_intent": getattr(work, "user_intent", ""),
        "status": canonical.status,
        "active_em": canonical.active_em,
        "active_capability": canonical.active_capability,
        "execution_phase": canonical.execution_phase,
        "execution_progress": canonical.execution_progress,
        "confidence": getattr(result, "confidence", None) if result else None,
        "summary": getattr(result, "summary", None) if result else None,
        "findings": (getattr(result, "findings", []) or []) if result else [],
        "recommendations": (getattr(result, "recommendations", []) or []) if result else [],
        "alternatives": (getattr(result, "alternatives", []) or []) if result else [],
        "scores": scores,
        "calculations": (getattr(result, "calculations", {}) or {}) if result else {},
        "limitations": (getattr(result, "limitations", []) or []) if result else [],
        "gaps": (getattr(result, "gaps", []) or []) if result else [],
        "provenance": (getattr(result, "provenance", []) or []) if result else [],
        "evidence_ids": (getattr(result, "evidence_ids", []) or []) if result else [],
        "acfl": {
            "weights": weights,
            "criteria": criteria,
            "alternatives": alternatives,
            "normalized_scores": scores,
            "weighted": weighted,
            "frontier": frontier,
            "derived_frontier": derived_frontier,
            "selected_alternative": selected_alternative,
        },
        "problem": {
            "objective": getattr(problem, "objective", "") if problem else "",
            "intent": getattr(problem, "intent", "") if problem else "",
            "context": getattr(problem, "context", "") if problem else "",
            "horizon": getattr(problem, "horizon", "") if problem else "",
            "risk": getattr(problem, "risk", "") if problem else "",
            "success_criteria": (getattr(problem, "success_criteria", []) or []) if problem else [],
            "requested_outputs": (getattr(problem, "requested_outputs", []) or []) if problem else [],
            "domain_context": getattr(problem, "domain_context", "") if problem else "",
        },
        "frozen": {
            "ref": getattr(frozen, "result_id", "") if frozen else "",
            "status": getattr(frozen, "status", "") if frozen else "",
            "freeze_signature": getattr(frozen, "freeze_signature", "") if frozen else "",
            "validated_knowledge": len(getattr(frozen, "validated_knowledge", []) or []) if frozen else 0,
            "validated_predictions": len(getattr(frozen, "validated_predictions", []) or []) if frozen else 0,
            "validated_prescriptions": len(getattr(frozen, "validated_prescriptions", []) or []) if frozen else 0,
            "unknowns": (getattr(frozen, "unknowns", []) or []) if frozen else [],
            "contradictions": (getattr(frozen, "contradictions", []) or []) if frozen else [],
        },
        "story_arc": story_arc,
        "em_pipeline": em_pipeline,
        "exec_steps": exec_steps,
        "decision_points": len(canonical.decision_points or []),
        "alt_labels": alt_labels,
    }


# --------------------------------------------------------------------------- #
# Format-agnostic content model
# --------------------------------------------------------------------------- #

def _build_content(p: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build a list of content blocks consumed by every document renderer."""
    content: List[Dict[str, Any]] = []
    add_h = lambda lvl, txt: content.append({"type": "heading", "level": lvl, "text": txt})
    add_p = lambda txt: content.append({"type": "para", "text": txt})
    add_b = lambda items: content.append({"type": "bullets", "items": items})
    add_kv = lambda items: content.append({"type": "kv", "items": items})
    add_t = lambda headers, rows: content.append({"type": "table", "headers": headers, "rows": rows})

    # --- Header block ---
    add_kv({
        "Work ID": p["work_id"] or "—",
        "Estado": p["status"] or "—",
        "EM Activo": p["active_em"] or "—",
        "Capacidad activa": p["active_capability"] or "—",
        "Fase": p["execution_phase"] or "—",
        "Progreso": _s(p["execution_progress"]) or "—",
        "Confianza": _s(p["confidence"]) or "—",
    })

    if p["problem"]["objective"]:
        add_h(1, "Problema")
        add_p(p["problem"]["objective"])
        if p["problem"]["intent"] and p["problem"]["intent"] != p["problem"]["objective"]:
            add_p("Intención original: " + p["problem"]["intent"])
        if p["problem"]["context"]:
            add_p("Contexto: " + p["problem"]["context"])

    # --- Summary ---
    if p["summary"]:
        add_h(1, "Resumen ejecutivo")
        add_p(p["summary"])

    # --- Findings ---
    if p["findings"]:
        add_h(1, "Hallazgos")
        add_b(p["findings"])

    # --- Fuzzy decision layer (the mathematical/cognitive differentiator) ---
    criteria = p["acfl"]["criteria"]
    alternatives = p["acfl"]["alternatives"]
    scores = p["acfl"]["normalized_scores"]
    if criteria and alternatives:
        acfl = p["acfl"]
        add_h(1, "Capa de decisión difusa (ACFL)")
        add_p("Matriz de satisfacción difusa por criterio (0..1). Cada celda refleja el grado "
              "de membresía de la alternativa respecto al criterio; la columna Ponderado agrega "
              "los criterios usando los pesos declarados (o ponderación uniforme si el criterio "
              "no tiene peso). Esta es la capa matemática que EUREKA inyecta por encima de la "
              "generación de lenguaje del LLM.")
        headers = ["Alternativa"] + list(criteria) + ["Ponderado"]
        rows = []
        for a in alternatives:
            label = best_frontier_label(p, a)
            if acfl.get("selected_alternative") and a == acfl["selected_alternative"]:
                label = label + "  ★ (seleccionada)"
            row = [label]
            for c in criteria:
                v = scores.get(a, {}).get(c, 0.0)
                row.append(f"{v:.2f}")
            row.append(f"{acfl['weighted'].get(a, 0.0):.3f}")
            rows.append(row)
        add_t(headers, rows)

        frontier = acfl["frontier"]
        if frontier:
            kind = "Derivado de la matriz (dominancia Pareto)" if acfl.get("derived_frontier") else "Declarado por ACFL"
            add_h(2, "Frente de Pareto (no dominadas)")
            add_p(kind + ":")
            add_b([best_frontier_label(p, a) for a in frontier])
        weights = acfl["weights"]
        if weights:
            add_kv({f"Peso: {k}": f"{v:g}" for k, v in weights.items() if isinstance(v, (int, float))})

    # --- Recommendations ---
    if p["recommendations"]:
        add_h(1, "Recomendaciones")
        add_b(p["recommendations"])

    # --- Story arc (cognitive narrative) ---
    if p["story_arc"]:
        add_h(1, "Arco cognitivo")
        add_b([
            f"{_s(step.get('phase'))}: {_s(step.get('content'))}"
            for step in p["story_arc"]
        ])

    # --- Calculations ---
    if p["calculations"]:
        add_h(1, "Cálculos")
        add_kv({k: _s(v) for k, v in p["calculations"].items()})

    # --- Execution / pipeline evidence ---
    if p["exec_steps"]:
        add_h(1, "Pipeline de ejecución")
        headers = ["Paso", "Capacidad", "EM", "Estado"]
        rows = [[s["step_id"], s["capability"], s["em"], s["status"]] for s in p["exec_steps"]]
        add_t(headers, rows)

    if p["em_pipeline"]:
        add_kv({e["em"]: e["status"] for e in p["em_pipeline"]})

    if p["frozen"]["ref"]:
        add_h(1, "Resultado congelado")
        f = p["frozen"]
        add_kv({
            "Referencia": f["ref"],
            "Estado": f["status"],
            "Firma": f["freeze_signature"] or "—",
            "Conocimiento validado": f["validated_knowledge"],
            "Predicciones validadas": f["validated_predictions"],
            "Prescripciones validadas": f["validated_prescriptions"],
        })

    # --- Provenance & evidence ---
    if p["evidence_ids"] or p["provenance"]:
        add_h(1, "Procedencia y evidencia")
        if p["evidence_ids"]:
            add_b([f"Evidence: {e}" for e in p["evidence_ids"]])
        if p["provenance"]:
            add_b(p["provenance"])

    # --- Limitations / gaps / unknowns ---
    combined_limit = list(p["limitations"]) + list(p["gaps"]) + list(p["frozen"]["unknowns"])
    if combined_limit:
        add_h(1, "Limitaciones, huecos e incógnitas")
        add_b(combined_limit)

    # --- Footer ---
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    add_p(f"Generado por EUREKA // motor cognitivo con capa matemática (ACFL). · timestamp {now} · trabajo {p['work_id']}")
    return content


# --------------------------------------------------------------------------- #
# TXT / Markdown
# --------------------------------------------------------------------------- #

def _render_text_model(content: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for blk in content:
        t = blk["type"]
        if t == "heading":
            lines.append("")
            lines.append("#" * blk["level"] + " " + blk["text"])
            lines.append("")
        elif t == "para":
            lines.append(blk["text"])
        elif t == "bullets":
            for it in blk["items"]:
                lines.append("  - " + it)
        elif t == "kv":
            for k, v in blk["items"].items():
                lines.append(f"  {k}: {v}")
        elif t == "table":
            if blk["headers"]:
                lines.append("  | " + " | ".join(blk["headers"]) + " |")
                lines.append("  |" + "---|" * len(blk["headers"]))
            for row in blk["rows"]:
                lines.append("  | " + " | ".join(str(c) for c in row) + " |")
            lines.append("")
    return "\n".join(lines).strip() + "\n"


def render_text(p: Dict[str, Any]) -> str:
    return _render_text_model(_build_content(p))


def render_markdown(p: Dict[str, Any]) -> str:
    lines: List[str] = []
    for blk in _build_content(p):
        t = blk["type"]
        if t == "heading":
            lines.append(("#" * blk["level"]) + " " + blk["text"])
        elif t == "para":
            lines.append(blk["text"])
        elif t == "bullets":
            for it in blk["items"]:
                lines.append("- " + it)
        elif t == "kv":
            lines.append("")
            for k, v in blk["items"].items():
                lines.append(f"- **{k}:** {v}")
        elif t == "table":
            lines.append("")
            if blk["headers"]:
                lines.append("| " + " | ".join(blk["headers"]) + " |")
                lines.append("|" + "---|" * len(blk["headers"]))
            for row in blk["rows"]:
                lines.append("| " + " | ".join(str(c).replace("|", r"\|") for c in row) + " |")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


# --------------------------------------------------------------------------- #
# DOCX
# --------------------------------------------------------------------------- #

def render_docx(p: Dict[str, Any]) -> bytes:
    from docx import Document
    doc = Document()
    doc.add_heading(f"EUREKA · {p['title'] or p['work_id']}", 0)

    for blk in _build_content(p):
        t = blk["type"]
        if t == "heading":
            doc.add_heading(blk["text"], blk["level"])
        elif t == "para":
            doc.add_paragraph(blk["text"])
        elif t == "bullets":
            for it in blk["items"]:
                doc.add_paragraph(it, style="List Bullet")
        elif t == "kv":
            for k, v in blk["items"].items():
                doc.add_paragraph(f"{k}: {v}")
        elif t == "table":
            if not blk["headers"]:
                continue
            tbl = doc.add_table(rows=1, cols=len(blk["headers"]))
            tbl.style = "Light Grid Accent 1"
            for j, h in enumerate(blk["headers"]):
                tbl.rows[0].cells[j].text = str(h)
            for row in blk["rows"]:
                cells = tbl.add_row().cells
                for j, c in enumerate(row):
                    cells[j].text = str(c)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# --------------------------------------------------------------------------- #
# PDF
# --------------------------------------------------------------------------- #

def _pdf_fonts() -> Tuple[Optional[str], dict]:
    """Register a unicode-capable font (DejaVu via matplotlib) when available."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.fonts import addMapping
    try:
        import matplotlib
        data_path = matplotlib.get_data_path()
        base = os.path.join(str(data_path), "fonts", "ttf")
        reg = os.path.join(base, "DejaVuSans.ttf")
        bold = os.path.join(base, "DejaVuSans-Bold.ttf")
        if os.path.exists(reg):
            pdfmetrics.registerFont(TTFont("DejaVu", reg))
            font = "DejaVu"
            mapping = {}
            if os.path.exists(bold):
                pdfmetrics.registerFont(TTFont("DejaVu-Bold", bold))
            addMapping("DejaVu", 0, 0, "DejaVu")
            addMapping("DejaVu", 1, 0, "DejaVu-Bold")
            return font, {}
    except Exception:
        pass
    return "Helvetica", {}


def render_pdf(p: Dict[str, Any]) -> bytes:
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    font, _ = _pdf_fonts()
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("EurekaH1", parent=styles["Heading1"], fontName=font, textColor=colors.HexColor("#0F6E6E"))
    h2 = ParagraphStyle("EurekaH2", parent=styles["Heading2"], fontName=font, textColor=colors.HexColor("#0F6E6E"))
    body = ParagraphStyle("EurekaBody", parent=styles["BodyText"], fontName=font)
    head = ParagraphStyle("EurekaHead", parent=styles["Normal"], fontName=font,
                          textColor=colors.white, fontSize=8, leading=10)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=LETTER, topMargin=0.7 * inch, bottomMargin=0.7 * inch)
    story = []

    story.append(Paragraph(f"EUREKA · {_s(p['title']) or _s(p['work_id'])}", h1))
    story.append(Spacer(1, 6))

    for blk in _build_content(p):
        t = blk["type"]
        if t == "heading":
            story.append(Paragraph(_s(blk["text"]), h1 if blk["level"] <= 1 else h2))
            story.append(Spacer(1, 4))
        elif t == "para":
            story.append(Paragraph(_s(blk["text"]), body))
            story.append(Spacer(1, 4))
        elif t == "bullets":
            for it in blk["items"]:
                story.append(Paragraph("&#8226;&nbsp; " + _s(it), body))
                story.append(Spacer(1, 2))
        elif t == "kv":
            for k, v in blk["items"].items():
                story.append(Paragraph(f"<b>{_s(k)}:</b>&nbsp; {_s(v)}", body))
                story.append(Spacer(1, 2))
        elif t == "table":
            if not blk["headers"]:
                continue
            data = [blk["headers"]] + [[str(c) for c in row] for row in blk["rows"]]
            tbl = Table(data, repeatRows=1, colWidths=[1.4 * inch] + [1.1 * inch] * (len(blk["headers"]) - 1))
            tbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F6E6E")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), font),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F2")]),
            ]))
            story.append(tbl)
            story.append(Spacer(1, 8))

    doc.build(story)
    return buf.getvalue()


# --------------------------------------------------------------------------- #
# PPTX
# --------------------------------------------------------------------------- #

def render_pptx(p: Dict[str, Any]) -> bytes:
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    teal = RGBColor(0x0F, 0x6E, 0x6E)

    def _new_slide(title: str = ""):
        layout = prs.slide_layouts[5] if len(prs.slide_layouts) > 5 else prs.slide_layouts[0]
        slide = prs.slides.add_slide(layout)
        if title:
            tb = slide.shapes.title  # may be None on layout 5
            if tb is not None:
                tb.text = title
                for para in tb.text_frame.paragraphs:
                    for run in para.runs:
                        run.font.size = Pt(26)
                        run.font.bold = True
                        run.font.color.rgb = teal
        return slide

    # Title slide
    layout0 = prs.slide_layouts[0]
    ts = prs.slides.add_slide(layout0)
    ts.shapes.title.text = f"EUREKA · {p['title'] or p['work_id']}"
    if ts.placeholders and len(ts.placeholders) > 1:
        sub = ts.placeholders[1]
        sub.text = "Motor cognitivo con capa matemática (ACFL)"
        for para in sub.text_frame.paragraphs:
            for run in para.runs:
                run.font.size = Pt(18)

    for blk in _build_content(p):
        t = blk["type"]

        # Tables become their own slide (landscape has room).
        if t == "table":
            if not blk["headers"]:
                continue
            slide = _new_slide("Matriz de decisión")
            rows = len(blk["rows"]) + 1
            cols = len(blk["headers"])
            left, top, width, height = Inches(0.6), Inches(1.2), Inches(12.1), Inches(0.5) * rows
            gtable = slide.shapes.add_table(rows, cols, left, top, width, height).table
            for j, h in enumerate(blk["headers"]):
                gtable.cell(0, j).text = str(h)
            for i, row in enumerate(blk["rows"], start=1):
                for j, c in enumerate(row):
                    gtable.cell(i, j).text = str(c)
            continue

        # Heading level 1 becomes a new slide with a title.
        if t == "heading" and blk["level"] <= 1:
            _new_slide(blk["text"])
            continue
        if t == "heading" and blk["level"] == 2:
            # Secondary heading: append as a slide subtitle on the most recent slide.
            if prs.slides:
                slide = prs.slides[-1]
                tb = slide.shapes.title
                if tb is not None:
                    tb.text = (tb.text + " · " + blk["text"]) if tb.text else blk["text"]
            continue

        # Content goes onto the last non-title slide as bullets.
        if t in ("bullets", "kv"):
            target = None
            if prs.slides:
                # Use the last slide that has a body placeholder.
                for idx in range(len(prs.slides) - 1, -1, -1):
                    for shape in prs.slides[idx].shapes:
                        if shape.has_text_frame and shape == prs.slides[idx].shapes.title:
                            continue
                        if shape.has_text_frame and shape.text_frame.text == "" and shape.has_table is False:
                            target = shape
                            break
                    if target is not None:
                        break
            if target is None:
                slide = _new_slide("Detalle")
                for shape in slide.shapes:
                    if shape.has_text_frame and not shape.has_table:
                        target = shape
                        break
                if target is None:
                    continue
            tf = target.text_frame
            items = []
            if t == "bullets":
                items = blk["items"]
            else:
                items = [f"{k}: {v}" for k, v in blk["items"].items()]
            for it in items:
                para = tf.add_paragraph()
                para.text = it
                para.level = 0
                for run in para.runs:
                    run.font.size = Pt(14)

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


# --------------------------------------------------------------------------- #
# PNG / SVG (image of the ACFL decision surface)
# --------------------------------------------------------------------------- #

def _render_chart(p: Dict[str, Any], fmt: str) -> bytes:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    scores = p["acfl"]["normalized_scores"] or {}
    criteria = p["acfl"]["criteria"] or []
    alternatives = p["acfl"]["alternatives"] or []
    weighted = p["acfl"]["weighted"] or {}
    frontier = p["acfl"]["frontier"] or []

    def _short_label(label: str, n: int = 34) -> str:
        label = str(label)
        return label if len(label) <= n else label[: n - 1] + "…"

    teal = "#0F6E6E"
    sand = "#F5F5F2"

    fig = plt.figure(figsize=(13.5, 6.5), facecolor="white", dpi=140, constrained_layout=True)

    # --- Left: heatmap of the fuzzy satisfaction matrix ---
    ax1 = fig.add_subplot(1, 2, 1)
    if criteria and alternatives:
        M = np.zeros((len(alternatives), len(criteria)))
        for i, a in enumerate(alternatives):
            for j, c in enumerate(criteria):
                M[i, j] = float(scores.get(a, {}).get(c, 0.0))
        im = ax1.imshow(M, cmap="YlGnBu", vmin=0.0, vmax=1.0, aspect="auto")
        ax1.set_title("Matriz de satisfacción difusa (ACFL)", fontsize=12, color=teal, weight="bold")
        ax1.set_xticks(range(len(criteria)))
        ax1.set_xticklabels([c if len(c) <= 16 else c[:14] + "…" for c in criteria],
                            rotation=35, ha="right", fontsize=8)
        ax1.set_yticks(range(len(alternatives)))
        ax1.set_yticklabels([_short_label(best_frontier_label(p, a)) for a in alternatives], fontsize=9)
        for i in range(len(alternatives)):
            for j in range(len(criteria)):
                ax1.text(j, i, f"{M[i, j]:.2f}", ha="center", va="center", fontsize=8,
                         color="white" if M[i, j] > 0.6 else "#14140F")
        for i, a in enumerate(alternatives):
            if a in frontier:
                ax1.get_yticklabels()[i].set_color(teal)
                ax1.get_yticklabels()[i].set_weight("bold")
        fig.colorbar(im, ax=ax1, fraction=0.046, pad=0.04).set_label("membresía 0..1", fontsize=8)
        ax1.set_facecolor(sand)
    else:
        ax1.text(0.5, 0.5, "Sin datos ACFL", ha="center", va="center", fontsize=12, color="#666")
        ax1.axis("off")

    # --- Right: weighted satisfaction + Pareto frontier ---
    ax2 = fig.add_subplot(1, 2, 2)
    if alternatives:
        vals = [weighted.get(a, 0.0) for a in alternatives]
        labels = [_short_label(best_frontier_label(p, a)) for a in alternatives]
        colors = [teal if a in frontier else "#9BB7B7" for a in alternatives]
        bars = ax2.barh(labels, vals, color=colors)
        ax2.set_xlim(0, 1.0)
        ax2.set_title("Satisfacción ponderada y frente de Pareto", fontsize=12, color=teal, weight="bold")
        ax2.set_xlabel("satisfacción agregada (0..1)", fontsize=9)
        for bar, v in zip(bars, vals):
            ax2.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height() / 2,
                     f"{v:.3f}", va="center", fontsize=8)
        # Draw the Pareto frontier line at max weighted satisfaction.
        frontier_vals = [weighted.get(a, 0.0) for a in alternatives if a in frontier]
        if frontier_vals:
            m = max(frontier_vals)
            ax2.axvline(m, color="#D97706", linestyle="--", linewidth=1.4)
            ax2.text(m + 0.01, len(alternatives) - 0.5, f"frontera = {m:.3f}",
                     color="#D97706", fontsize=8, va="center")
        ax2.set_facecolor(sand)
        ax2.grid(axis="x", color="#E0E0DC", linewidth=0.6)
    else:
        ax2.text(0.5, 0.5, "Sin alternativas", ha="center", va="center", fontsize=12, color="#666")
        ax2.axis("off")

    fig.suptitle(f"EUREKA · capa de decisión difusa — {p['work_id']}", fontsize=14, color=teal, weight="bold")

    buf = io.BytesIO()
    fig.savefig(buf, format=fmt, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def render_png(p: Dict[str, Any]) -> bytes:
    return _render_chart(p, "png")


def render_svg(p: Dict[str, Any]) -> bytes:
    return _render_chart(p, "svg")


# --------------------------------------------------------------------------- #
# Public dispatcher
# --------------------------------------------------------------------------- #

_EXPORTERS = {
    "txt": (render_text, "text/plain", "txt"),
    "md": (render_markdown, "text/markdown", "md"),
    "docx": (render_docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx"),
    "pdf": (render_pdf, "application/pdf", "pdf"),
    "pptx": (render_pptx, "application/vnd.openxmlformats-officedocument.presentationml.presentation", "pptx"),
    "png": (render_png, "image/png", "png"),
    "svg": (render_svg, "image/svg+xml", "svg"),
}

SUPPORTED_FORMATS = sorted(_EXPORTERS.keys())


def export_work(canonical: CanonicalWorkState, fmt: str) -> Tuple[bytes, str, str]:
    """Return (payload_bytes, filename, media_type) for the requested format."""
    fmt = (fmt or "txt").lower().lstrip(".")
    if fmt not in _EXPORTERS:
        raise ValueError(
            f"Unsupported export format '{fmt}'. Supported: {', '.join(SUPPORTED_FORMATS)}"
        )
    payload = build_export_payload(canonical)
    render, media_type, ext = _EXPORTERS[fmt]
    data = render(payload)
    if isinstance(data, str):
        # Text-based formats (txt, md) return str; normalize to UTF-8 bytes so callers
        # can write them straight to disk / serve as a stream.
        data = data.encode("utf-8")
    filename = f"EUREKA_{canonical.work.work_id}.{ext}"
    return data, filename, media_type


def write_export(canonical: CanonicalWorkState, fmt: str, out_dir: str = "generated") -> str:
    """Write the artifact to disk (persists across restarts) and return the path."""
    os.makedirs(out_dir, exist_ok=True)
    data, filename, _ = export_work(canonical, fmt)
    path = os.path.join(out_dir, filename)
    with open(path, "wb") as f:
        f.write(data)
    return path
