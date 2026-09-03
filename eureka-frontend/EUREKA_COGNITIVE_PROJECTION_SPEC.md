# EUREKA — COGNITIVE PROJECTION SPEC (CognitiveProjectionDTO)

**Fuente única de significado cognitivo del frontend.** `CANONICAL STATE = TRUTH · PROJECTION = MEANING · PRESENTATION = RENDER`.

```
CANONICAL STATE  →  buildCognitiveProjection(state)  →  CognitiveProjectionDTO  →  VisualModel / StoryModel
```

## El DTO
`src/domain/cognitiveProjection.ts` — tipado, puro, sin side-effects. Define `CognitiveProjectionDTO` + `buildCognitiveProjection(state)` + `buildProvenanceNodes(dto)`.

## Campos → origen canónico → EM → autoridad
| DTO field | canonical field | artifact | EM | authority |
|---|---|---|---|---|
| `question` | `problem.objective` | ProblemModel | Core | LLM_CANDIDATE |
| `problem.authority` | `problem.governance_status` | ProblemModel | Core | PYTHON_GOVERNED |
| `evidence[].sourceText` | `extracted_evidence[EVI-*].text_blocks` | ExtractedEvidence | Descriptor | grounded |
| `findings[].status` | `knowledge.findings[].validation_status` | Finding | Descriptor+gate | VALIDATED/UNSUPPORTED |
| `predictions[].status` | `predictive_knowledge.predictions[].validation_status` | PredictionKnowledge | Predictor | NOT_EVALUATED/VALIDATED |
| `predictions[].modelType` | `predictive_knowledge.predictions[].model_type` | PredictionKnowledge | Predictor | MATH_ENGINE (ACFL_ENGINE) |
| `prescription.alternatives` | `prescriptive_knowledge.prescriptions[].alternatives` | Prescription | Prescriptor | LLM_CANDIDATE / HUMAN |
| **`humanDecision`** | **`human_decision`** | HumanDecision | HITL | **HUMAN_AUTHORIZED** / PENDING |
| `recommendedOption` | `decision_points[].recommended_option` | DecisionPoint | Prescriptor | LLM_CANDIDATE (never decision) |
| `actionPlan.selectedAlternativeId` | `action_plan.selected_alternative_id` | ValidatedActionPlan | Actioner | HUMAN_AUTHORIZED |
| `execution.simulated` | `execution_state` | ExecutionState | Installer | SIMULATED |
| `frozenResult.signature` | `frozen_result.freeze_signature` | FrozenResult | Installer | FROZEN |
| `result.id` | `state.result.result_id` | WorkResult | Publisher | PUBLISHED |
| `lineage[]` | ids reales enlazados | — | — | — |
| `projectionConflict` | `actionPlan.selectedAlternativeId != humanDecision.selectedAlternativeId` | — | — | true = nunca autocorregir |

## Reglas (inmutables)
- `null` ≠ valor · `NOT_EVALUATED` ≠ evaluado · `UNSUPPORTED` ≠ `VALIDATED` · `LLM_CANDIDATE` ≠ hecho.
- **`humanDecision` solo de `human_decision`** (nunca de `recommendedOption`). Si no hay → `{authority:'PENDING', preserved:false}`.
- `recommendedOption` (sistema) se conserva separado de `humanDecision` (humano).
- `predicted_value=null` → `value:null` + `status:NOT_EVALUATED` (nunca 0/number).
- `execution` → `simulated:true` (nunca "externally executed").
- `projectionConflict=true` cuando ActionPlan ≠ human decision → **reportar, no autocorregir**.
- `buildProvenanceNodes` genera la cadena `EVI→FND→PRED→PRESC→DEC→ACT→EXEC→FROZEN` con IDs reales (o `NOT_AVAILABLE`).

## Consumidores (objetivo)
Visualization (React Flow/D3/ECharts), Storytelling (React+Motion), EM rail interactivo, Inspector. Todos leen de `CognitiveProjectionDTO`.

*Especificación del modelo intermedio (LS86). SIN instalar librerías, SIN rediseño.*
