# EUREKA — LS94 · REQUEST MISSING DATA (HITL information gathering)

**Frontier:** “When the system detects it lacks the data to answer a natural question substantively, ask the user for the SPECIFIC missing data (HITL / information request), pausing the operation and surfacing a clear question in the chat — instead of publishing a thin ‘no es posible analizar’ result.” — EUREKA Multiverse 5.1.

**State:** PASS. Backend `:8000` restarted with the LS94 code; frontend `:5173` unchanged. Real browser E2E → `console_errors=[]`, request card shows for the no-data question and the governed answer shows for the with-data question.

---

## 1 · The gap

For a generic / natural question that asks for a **descriptive analysis of a specific system** (e.g. *“identificar las capacidades/limitaciones de EUREKA para hacerla más inteligente”*) with **no concrete data** about that system, the pipeline:

- routed `KNOWLEDGE_ANSWER`/`OPEN_RESEARCH`, let the Descriptor produce findings that were mostly `UNSUPPORTED` (“the evidence doesn’t describe EUREKA’s capabilities”), `prescriptions=0`, `decision_points=0`, and
- published a thin result whose summary said *“no es posible realizar un análisis fundamentado”* — **without ever asking the user for the specific data it needed**.

The user was left with an honest-but-dead-end “insufficient” answer instead of a request they could act on.

## 2 · What changed

**Backend** (the engine/pipeline — the single place the behaviour was wrong):

| File | Change |
|------|--------|
| `src/eureka/universe/cognitive_engine.py` | New **`MissingDataProposal`** model (LLM **candidate** for what data is missing). Added `propose_missing_data(problem, findings)` to the `CognitiveEngine` interface + `DeepSeekAdapter` (real LLM, retries, fail-closed to `data_needed=False`) + `TestDoubleCognitiveEngine` (deterministic, never asks by default). |
| `src/eureka/universe/work_runtime.py` | New **`_maybe_request_missing_data(canonical)`** hook + `_set_next_step_waiting(canonical)`, called right after `EM Descriptor` runs. It detects the insufficient case, asks the LLM for the specific missing data (**candidate**), then **Python** validates and persists a blocking `HumanInteractionRequest` and pauses the workflow on `WAITING_FOR_HUMAN_INPUT`. |

Primary code path: `work_runtime._execute_step` → after `self.descriptor.execute(...)` → `_maybe_request_missing_data(canonical)`. When it creates the request it also marks the next executable step (the Publisher) as `WAITING_FOR_HUMAN_INPUT`, so the run halts **before** publishing a thin/unsupported answer.

**Frontend** — **no change required.** The existing UI already surfaces an `INFORMATION` request in the chat (the `HITLDecisionWidget` → `InformationItem` card, “EUREKA necesita tu información” + the question + an input + “Enviar información”), and the `open_research` projection surfaces `PENDING_HUMAN_INPUT`. The `ExecutiveCognitiveAnswer` “WHAT REMAINS OPEN” section reads the same projection. Only the backend was emitting the wrong signal; the frontend already knew how to render it.

## 3 · How the request is generated (LLM proposes → Python decides → chat surfaces)

1. **Python detects the situation** (authority, deterministic): after the Descriptor, the operation is a natural-question / knowledge / open-research operation (`KNOWLEDGE_ANSWER` or a still-open `DECISION`), it is **not** a selection/decision-selection question, **no** finding is grounded in real uploaded evidence, and the user has **not** already provided data.
2. **LLM proposes WHAT is missing (candidate only):** `propose_missing_data` returns `data_needed`, a **clear natural question** (*“Para hacer un análisis fundamentado de las capacidades… necesito que me indiques: 1) sus capacidades actuales, 2) sus limitaciones conocidas, 3) métricas o benchmarks de rendimiento, 4) los objetivos de mejora”*) and the list of **specific data dimensions** (`required_information`). The LLM never becomes authority.
3. **Python validates + persists (authority):** if `data_needed` is true and the proposal is coherent (non-empty question + non-empty `required_information`), Python creates a real `HumanInteractionRequest(type="INFORMATION", blocking=True, decision_required=False)` and appends it to `canonical.human_requests`, records a `WAITING_FOR_HUMAN_INPUT` condition (`MISSING_DATA_REQUESTED`), and pauses the workflow.
4. **Chat + projection surface it:** the work goes `WAITING_FOR_HUMAN_INPUT`; the chat renders the “EUREKA necesita tu información” card; `build_open_research_state` adds a `PENDING_HUMAN_INPUT` item (so the Executive Cognitive Answer “WHAT REMAINS OPEN” / open-research view shows it). Honest tokens are kept: `OPEN_INSUFFICIENT_INFORMATION`, `DATA_NOT_AVAILABLE`, `NOT_EVALUATED`, `UNSUPPORTED`.

**No fabrication:** the system does **not** invent data, conclusions, metrics, or findings. When data is missing it asks; the chat explicitly says there is no published result / recommendation yet.

## 4 · Real verification (backend `:8000` + frontend `:5173`, live DeepSeek LLM)

**1. No-data question now ASKS** — `¿Cómo puedo hacer a EUREKA más inteligente y aumentar su rendimiento?`:

```
status: WAITING_FOR_HUMAN_INPUT
human_requests: [{ type: INFORMATION, blocking: true, decision_required: false, status: PENDING,
   question: "Para hacer un análisis fundamentado de las estrategias para hacer a EUREKA más inteligente y
               mejorar su rendimiento, necesito que me indiques: 1) sus capacidades actuales, 2) sus
               limitaciones conocidas, 3) métricas o benchmarks de rendimiento, 4) los objetivos de mejora…" }]
open_research: status OPEN_INSUFFICIENT_INFORMATION · kinds contain PENDING_HUMAN_INPUT
```
The exact mission example *“Identificar las capacidades, limitaciones y oportunidades de mejora de EUREKA para aumentar su inteligencia y rendimiento”* (currently routed `DECISION`) also produces the same blocking `INFORMATION` request + `WAITING_FOR_HUMAN_INPUT` + `PENDING_HUMAN_INPUT`.

**2. With-data question still ANSWERS** — `¿Qué es el aprendizaje activo?`:
```
status: COMPLETED · human_requests: [] · result status: AVAILABLE
```
(no false ask; correct governed semantic answer preserved).

**3. Provide data → resume → grounded answer** — `POST /api/work/{id}/human_input` with the requested EUREKA data:
```
resume response: { status: RESUMED }
final status: COMPLETED · result status: AVAILABLE
RESULT summary (grounded on the user's data): "…EUREKA es un sistema de razonamiento cognitivo que orquesta
8 EM, realiza análisis ACFL, genera respuestas gobernadas por el LLM… Sus limitaciones actuales incluyen…"
```

**4. LS92 HITL decision preserved** — *“¿Cuál de estas alternativas debería elegir?”* still gets a `HumanDecisionPoint` (PENDING) + the pipeline HITL decision gate, **not** an LS94 information ask (selection guard).

## 5 · Validation

- Backend: `python -m py_compile` on `cognitive_engine.py` + `work_runtime.py` → OK. Module import sanity → OK. Backend `:8000` restarted once.
- Frontend: `npx tsc --noEmit -p tsconfig.app.json` → **0 errors**; `npx vitest run` → **56 passed / 56**; `npm run build` → **ok** (dist built).
- **Browser E2E (real):** `playwright` (real Chrome headless) driving `http://127.0.0.1:5173` (Vite dev) → `http://localhost:8000` (LS94 backend), real intake + real DeepSeek. **`console_errors=[]`.** The **request card shows** for the no-data question (`info_widget_present=true`, “EUREKA necesita tu información” card with the question + “Enviar información”) and the **Executive Cognitive Answer** shows for the with-data question (`exec_card_present=true`, no ask).

## 6 · Honest limitations

- **LLM-determinism:** `propose_missing_data` is the content source; its judgement (specifically `data_needed`) drives whether/when to ask. It is reliable for the tested cases (self-answerable general questions → `False`; specific-entity data questions → `True`), but like any LLM probe it is not 100% deterministic across runs. Python guards it (selection guard + real-evidence guard + ask-once guard + fail-closed to `data_needed=False` on LLM error) so an unreachable/incoherent LLM never fabricates a request.
- **Second descriptor pass:** LLM plans sometimes contain two Descriptor tasks (e.g. `T1`, `T2`). The ask fires after the first one and pauses the Publisher; on resume the remaining Descriptor task re-runs and then the Publisher synthesises the grounded answer from the user data. This is correct behaviour but produces a small number of extra `UNSUPPORTED` findings beside the user’s grounded one.
- **Executive Cognitive Answer timing:** while the work is `WAITING_FOR_HUMAN_INPUT` the Executive Cognitive Answer card itself is not yet rendered (it renders at `COMPLETED`); the request is surfaced in the **chat** via the HITL widget (primary), and the `open_research`/`PENDING_HUMAN_INPUT` projection is what the “WHAT REMAINS OPEN” Executive section reads once the work completes. No fabricate, no parallel DTO — `CognitiveProjectionDTO` remains the single source.
- **Scope:** the ask is for natural-question / knowledge / **open-research** operations. Explicit selection/decision-selection questions keep their own 8-EM + HITL decision gate (LS92 unchanged), and findings grounded in real uploaded evidence never trigger the ask.

## 7 · Rollback

Pre-change snapshot: `_backup_pre_LS94_impl_2026-09-01_200506` (cognitive_engine.py, work_runtime.py, orchestrator.py). Earlier `_backup_pre_LS94_2026-09-01_195036` and `_backup_stable_2026-09-01_192707_LS93_v7_VISUAL_QUALITY` retained.
