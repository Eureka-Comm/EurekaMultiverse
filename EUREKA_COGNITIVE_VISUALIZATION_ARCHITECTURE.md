# EUREKA — COGNITIVE VISUALIZATION & STORYTELLING ARCHITECTURE (destino)

**Principio:** `STATE DEFINES TRUTH · PROJECTION DEFINES MEANING · LIBRARIES RENDER · LLM NARRATES · HUMAN AUTHORIZES`.

```
                    CANONICAL STATE
                          │
                          ▼
                 COGNITIVE PROJECTION        ← único modelo intermedio (fuente de verdad de la UI)
                          │
          ┌───────────────┴───────────────┐
          ▼                               ▼
    VISUAL MODEL                     STORY MODEL
     nodes[] edges[]                   question/context/evidence/findings/
     authority provenance             computations/limitations/alternatives/
     surfaces timeline                human_decision/action/execution/frozen
          │                               │
   ┌──────┼──────┐                        │
   ▼      ▼      ▼                        ▼
 ReactFlash D3  ECharts                  React + Motion
          │                               │
          └───────────────┬───────────────┘
                          ▼
                    EUREKA UI (tabs existentes)
```

---

## 1. CognitProjection (nuevo, unificado) — CLAVE
**Una sola capa** que transforma `CanonicalState` → `VisualModel` + `StoryModel`. Reemplaza la duplicación actual (`cognitiveStory.ts` ↔ `story.arc`).

```ts
interface CognitiveProjectionDTO {
  question: string;                 // ← problem.objective / intent (LLM_CANDIDATE)
  problem: { id; objective; authority }[];
  structure: { entities; variables; relationships; governed: boolean };  // conceptual ≠ validado
  evidence: { id; source; text; grounded }[];              // ← EVI-CONTEXT / extracted_evidence
  findings: { id; statement; status; evidenceRefs; provenance }[];      // FND-*, grounding gate
  predictions: { id; modelType; status; value; provenance }[];          // PRED-*, ACFL_ENGINE/GCLV
  prescriptions: { id; alternatives[]; criteria[]; authority }[];       // PRESC-*
  humanDecision: { id; selection; authority; status } | null;           // DEC-* / HUMAN_AUTHORIZED / PENDING
  actionPlan: { id; selectedAlternative; humanDecisionId; status } | null; // AP-*
  execution: { id; status; level; simulated: boolean } | null;          // SIMULATED
  result: { id; summary; status } | null;                               // WR-*
  frozen: { id; signature; status } | null;                             // FROZEN-*
  provenanceChain: Edge[];   // EVI→FND→PRED→PRESC→DEC→ACT→EXEC→FROZEN (relaciones REALES)
  authorityByArtifact: Record<string, Authority>;  // LLM_CANDIDATE/PYTHON_GOVERNED/MATH_ENGINE/HUMAN_AUTHORIZED/SIMULATED/FROZEN
}
```

**Reglas de mapeo (nunca inventar):**
- `null` ≠ valor · `NOT_EVALUATED` ≠ evaluado · `UNSUPPORTED` ≠ `VALIDATED` · `LLM_CANDIDATE` ≠ hecho · `recommendation` ≠ `human_decision` · `alternative` ≠ `optimal` · `simulated` ≠ external.
- `humanDecision = human_decision` (si existe); si no → `{status:'PENDING'}`.
- `provenanceChain` usa solo relaciones REALES (`derived_from`/`informs`/`supports`/`selected_by`/`authorizes`/`produces`/`precedes`) — nunca `causes`/`influences` si el estado no afirma causalidad.
- Fuente única (dedupe): `cognitiveStory.ts` se conviertE en la implementación del `CognitiveProjection`; `story.arc` solo alimenta al `StoryModel` (narrativa), no es otra fuente.

## 2. Visual Model → librerías
| Capa | Librería | Qué renderiza |
|---|---|---|
| **Cognitive Knowledge Map** | **React Flow** | grafo de artefactos (nodo=artefacto, edge=relación `provenanceChain`, color=authority) |
| **Provenance graph** | **React Flow + D3** | lineage `EVI→FND→PRED→PRESC→DEC→ACT→EXEC→FROZEN` |
| **Superficies analíticas** | **ECharts 6 / D3** | ACFL surface, GCLV membership, frontier real, comparison, uncertainty, timeline |
| **Story Mode animado** | **Motion** | recorrido por capítulos (transformación de conocimiento) |
| **Grafos avanzados** | **Cytoscape** (opcional) | solo si análisis de grafo > React Flow |

## 3. Rail de los 8 EM (interactivo)
`EMOperationalPipeline` conserva nodos/líneas/COMPLETED/minimalismo. **Se hace interactivo:** al seleccionar un EM se resalta → sus artefactos (Predictor → `PredictiveKnowledge`+`ACFL_DETERMINISTIC`+GCLV; Prescriptor → findings+predictions→alternatives→HITL; Installer → ActionPlan→Execution→FrozenResult).

## 4. Storytelling (unificado, gobernado)
`StoryModel` alimenta la narrativa (React+Motion). Secciones: WHAT YOU ASKED / WHAT EUREKA KNEW / WHAT EUREKA FOUND / WHAT EUREKA COMPUTED / WHAT EUREKA COULD NOT COMPUTE / WHAT EUREKA PROPOSED / WHAT YOU DECIDED / WHAT EUREKA DID / WHAT HAPPENED / WHAT WAS FROZEN. (Usa `humanDecision` real; `NOT_EVALUATED`/`SIMULATED` se mantienen).

## 5. Autoridad visible (codificación consistente)
`LLM_CANDIDATE` (azul) · `PYTHON_GOVERNED` (teal) · `MATH_ENGINE` (teal) · `HUMAN_AUTHORIZED` (violeta) · `SIMULATED` (ciano) · `FROZEN` (verde). El usuario identifica de un vistazo: qué generó el LLM, qué validó Python, qué calculó MathEngine, qué decidió el humano.

## 6. Proceso (ONE STEP AT A TIME)
1. **LS86**: implementar `CognitiveProjection` unificado (dedupe `cognitiveStory.ts` ↔ `story.arc`) — sin cambiar visual todavía.
2. **LS87**: Cognitive Knowledge Map (React Flow) sobre el projection.
3. **LS88**: Provenance graph + EM rail interactivo.
4. **LS89**: Superficies ECharts/D3 + Story Mode animado (Motion).
5. **LS90**: E2E + adversarial + comparación canonical↔visual↔story (sin información inventada).

## 7. NO hacer
`optimization`/`Pareto selector`/`autonomous decision`/`causal inference`/`autonomous execution`/`LLM-driven visualization semantics`/`Level 3 external execution`.

## 8. Regla de rechazo
Si una implementación viola `STATE DEFINES TRUTH · PROJECTION DEFINES MEANING · LIBRARIES RENDER · LLM NARRATES · HUMAN AUTHORIZES` → **REJECT**.

---

*Arquitectura objetivo. FASE 0 (audit) completada; sin cambios de código.*
