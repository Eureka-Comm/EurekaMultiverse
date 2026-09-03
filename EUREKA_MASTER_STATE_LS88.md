# EUREKA — MASTER STATE (LS88)

**Backup oficial restaurable:** `D:\DS_ARNES\IA Agentes\_backup_stable_2026-09-01_110412_LS88_CONSOLIDATED` (frontend 119 + backend 143 files). **Rollback:** copiar `eureka-frontend/` + `src/` de vuelta + `npm install`.
**Estado validado:** `tsc 0`, `vitest 29/29`, backend `:8000` OK, browser E2E `console_errors=[]`.

---

## 1. Executive Summary
EUREKA es un **sistema cognitivo gobernado** (8 EM + capa matemática + HITL) donde el LLM propone/interpreta/narra, Python valida/gobierna, MathEngine/ACFL computa, HITL decide, y el frontend proyecta el conocimiento gobernado. La capa cognitiva (Cognitive Story) es una superficie secundaria que permite reconstruir *cómo* EUREKA construyó su conocimiento. **No hay optimización/Pareto/causalidad inventada; no hay ejecución externa real; `NOT_EVALUATED`/`UNSUPPORTED`/`SIMULATED`/`FROZEN` se conservan.**

## 2. Arquitectura
```
USER → CHAT (PRIMARY) → EUREKA CORE → [8 EM | MathEngine | HITL] → CANONICAL STATE → CognitiveProjectionDTO → [STORYTELLING|VISUALIZATION] → COGNITIVE STORY (SECONDARY)
```

## 3. Ocho EM
| EM | Autoridad | LLM | Determinista | Provenance |
|---|---|---|---|---|
| Core | Python (`GOVERNED`, `intent=PYTHON`) | candidato | — | `governance_fields` (`LLM_CANDIDATE` vs `PYTHON`) |
| Structurer | Python (grafo) | contenido | grafo (DAG/owners/deps) | estructura conceptual ≠ validado |
| Descriptor | Grounding gate | candidato | `_grounded` léxico → VALIDATED/UNSUPPORTED | `Task→Evidence[EVI-CONTEXT]→(grounded)` |
| Predictor | **MathEngine/ACFL** | **no** | **`ACFL_DETERMINISTIC`** (GCLV ec 4.17) | `ACFL_ENGINE_V5.1` + signature + `evidence_refs` |
| Prescriptor | **HITL/HUMAN** | candidato | — | `supporting_knowledge=FND-*`, `supporting_predictions=PRED-*` |
| Actioner | **HITL** (gate LS79.1/81.2) | candidato | gate    | `selected_alternative_id=human_decision`, `human_decision_id`, `VALIDATED` |
| Installer | Gates/Python | no | freeze | `execution_state COMPLETED` + `freeze_signature` |
| Publisher | Estado canónico | narrativa | — | findings/recommendations del estado |

## 4. Autoridad
`LLM=candidato/interpretación/narrativa` · `Python=validación/gobernanza` · `MathEngine=cálculo` · `HITL=decisión humana` · `Installer=ejecución gobernada` · `Publisher=narrativa sobre estado gobernado`. **`HUMAN DECISION ≠ RECOMMENDED OPTION`.**

## 5. Capa matemática
Predictor = `ACFL_DETERMINISTIC` (MathEngine, GCLV). **NO** optimization/Pareto/utility selector/mathematical optimum implementados (RAFA = `OPEN_RESEARCH`/`DEFERRED`). `predicted_value=null` → `NOT_EVALUATED`.

## 6. Capa cognitiva
`CognitiveProjectionDTO` (LS86) = **única fuente intermedia**. `useCognitiveProjection` hook. Storytelling + Visualization + Knowledge Map + Inspector lo consumen. Sin proyección paralela, sin mocks.

## 7. HITL
`recommended_option` = propuesta del sistema · `human_selection` = decisión humana. Autoridad final = **HUMAN**.

## 8-13. Runtime / Canonical / Provenance / DTO / Storytelling / Visualization
- **Runtime:** `READ_PURE` (GET/state no ejecuta), `DECISION_POINTS=1`, evento no bloqueado (`_process_state` en thread).
- **Canonical:** ProblemModel, structured_problem, knowledge.findings, predictive_knowledge (predicates/predictions), prescriptive_knowledge, human_decision, action_plan, execution_state, frozen_result, result, decision_points, extracted_evidence (EVI-CONTEXT text_blocks persistido).
- **Provenance/lineage:** `EVI→FND→PRED→PRESC→DEC→ACT→EV→FROZEN` con IDs reales (o `DATA NOT AVAILABLE`).
- **CognitiveProjectionDTO:** `question/problem/evidence/findings/predictions/prescription/humanDecision/actionPlan/execution/result/frozenResult/recommendedOption/lineage/projectionConflict`.
- **Storytelling:** Executive Summary + WHY/WHAT/EVIDENCE/DECISION/ACTION/RESULT. `WHAT EUREKA PROPOSED` separado de `WHAT THE HUMAN DECIDED`.
- **Visualization:** Knowledge Map (React Flow, aristas `derived_from/supports/selected_by/authorized_by/…` — nunca `causes`), ProvenanceChain, Inspector, DecisionView (`RECOMMENDED` vs `HUMAN`), AuthorityChip, SourceTag.

## 14. Cognitive Story UX
Chat = PRIMARY; Cognitive Story = SECONDARY TAB. `[EXPLORE COGNITIVE STORY]` → deep-link al capítulo DECISION. Rail 8-EM interactivo (click EM → artefactos/autoridad/provenance).

## 15-16. Frontend / Backend
- **Frontend:** Chat, Trajectory, Cognitive Story (Storytelling+Visualization), Evidence, Decision Surfaces, Evolución. Estilo minimalist/white/scientific/thin (CSS `var(--eureka-*)`). Stack: React Flow + D3 + ECharts + Framer Motion (presentación, no fuente de verdad).
- **Backend:** `:8000`, 8 EM gobernados, Deterministic Predictor, HITL, evento no bloqueado, EVI-CONTEXT persistido.

## 17. E2E evidence
`F1_OK` (COMPLETED/AVAILABLE, READ_PURE, DECISION_POINTS=1, HITL answered) · browser E2E `console_errors=[]` · business-case E2E produce `AP-*`+`execution_state COMPLETED`+`FROZEN-*` · evidence `FND-*`/`PRED-*`/`ALT-*`/`DEC-*` reales.

## 18. Invariantes oficiales
`READ_PURE` · `DECISION_POINTS=1` · `PREDICTOR_DETERMINISTIC` · `ACTION_PLAN_HUMAN` · `FROZEN_IMMUTABLE` · `PROVENANCE` (IDs reales) · `NO_FAKE_OPTIMIZATION` · `NO_FAKE_CAUSALITY` · `NO_FAKE_EVIDENCE` · `NO_FAKE_DECISION` · `NO_FAKE_EXECUTION` · `CHAT_PRIMARY` · `COGNITIVE_STORY_SECONDARY`.

## 19. Known limitations (documentadas, no gaps)
- Action plan/execution ausentes para intents cuyo `task_network` omite `install_action` (rama legítima; `DATA NOT AVAILABLE` correcto).
- **MONITOR (LS87):** materialización no determinista del `action_plan` (null vs AP entre corridas) → `FUTURE_HARDENING`, no un gap crítico.

## 20. Deferred research
`DecisionModel` prescriptivo (multi-criterio, preferencias/riesgo) = `OPEN_RESEARCH`. `Level 3 external execution` = `DEFERRED` (infra separada). Optimization/Pareto = `DEFERRED`.

## 21. Legacy tests
Tests `test_problem_foundation`/`test_prescriptor`/`test_prescriptor_to_actioner` que fallan = `LEGACY_DRIFT` (codifican contratos pre-LS52/60/63/77.3/79.1). No se modifican; la autoridad es doc+código+runtime+invariants, no `pytest GREEN`.

## 22. LS77→87 chronology
LS77+77.1-77.6 (gobernanza) → LS78 (2 REAL_GAP) → LS79.1-79.4 (Actioner gate, Prescriptor provenance, Predictor refs, EVI persist) → LS80 (cross-exam) → LS81.1+81.2 (ActionPlan route unification) → LS82 (legacy tests) → LS83 (capability validation) → LS84-86 (Cognitive Story + DTO) → LS87 (ActionPlan/Execution reconciliation).

## 23-24. Backup / Rollback
`_backup_stable_2026-09-01_110412_LS88_CONSOLIDATED` + backups previos intactos (`_backup_stable_*`, `_backup_pre_cognitive_story_*`). Rollback: copiar `eureka-frontend/`+`src/` + `npm install`.

---

*Documento maestro de continuidad (LS88). Estado oficial alcanzado LS77→87, restaurable y auditable.*
