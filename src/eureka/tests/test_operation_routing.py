"""Python-authority operation routing (orchestrator._detect_operation_mode).

Forensic fix: a declarative analysis / derivation / discovery / evaluation request
("analizar / detectar patrones / identificar factores / evaluar segmentos / investigar
variables / encontrar relaciones o anomalías / descubrir insights / derivar hallazgos /
explicar los factores") MUST route to DECISION (full 8-EM + HITL), even when the LLM proposes
a REPORT / SUMMARY / QUESTION category. Python is the authority; the LLM candidate cannot
override it.

Genuine descriptive summary/report requests ("resume / genera un reporte / ¿cuál fue el
total? / muéstrame un resumen") stay KNOWLEDGE_ANSWER (publish a governed LLM answer).
"""
import pytest

from src.eureka.universe.orchestrator import _detect_operation_mode


@pytest.mark.parametrize(
    "intent,category,expected",
    [
        # --- DECLARATIVE ANALYSIS -> DECISION (the bug being fixed) ---
        ("Analizar el comportamiento de ventas y detectar los principales patrones.", "REPORT", "DECISION"),
        ("Detecta anomalías en las ventas.", "REPORT", "DECISION"),
        ("Evalúa qué segmentos tienen mayor potencial.", "REPORT", "DECISION"),
        ("Identifica los factores asociados a la caída de ventas.", "REPORT", "DECISION"),
        ("Investiga qué variables están asociadas con la pérdida de clientes.", "SUMMARY", "DECISION"),
        ("Determina qué productos presentan mayor riesgo.", "REPORT", "DECISION"),
        ("Encuentra relaciones entre las variables de ventas.", "REPORT", "DECISION"),
        ("Descubre insights sobre el comportamiento de clientes.", "SUMMARY", "DECISION"),
        ("Explica los factores de la caída de ventas.", "REPORT", "DECISION"),
        # A REPORT/SUMMARY/QUESTION category must NOT be able to override the analysis intent.
        ("Analiza el comportamiento de ventas y detecta patrones.", "SUMMARY", "DECISION"),
        ("Identifica los factores que explican la caída de ventas.", "QUESTION", "DECISION"),
        # --- DESCRIPTIVE SUMMARY / REPORT -> KNOWLEDGE_ANSWER (must NOT regress) ---
        ("Resume el comportamiento de ventas.", "SUMMARY", "KNOWLEDGE_ANSWER"),
        ("Genera un reporte de ventas.", "REPORT", "KNOWLEDGE_ANSWER"),
        ("¿Cuál fue el total de ventas?", "QUESTION", "KNOWLEDGE_ANSWER"),
        ("Muéstrame un resumen de los resultados.", "SUMMARY", "KNOWLEDGE_ANSWER"),
        ("¿Cuáles son las ventajas de invertir?", "QUESTION", "KNOWLEDGE_ANSWER"),
        ("¿Qué es el aprendizaje activo?", "QUESTION", "KNOWLEDGE_ANSWER"),
        ("¿Cómo hacer un pastel?", "QUESTION", "KNOWLEDGE_ANSWER"),
    ],
)
def test_detect_operation_mode(intent, category, expected):
    assert _detect_operation_mode(intent, category) == expected
