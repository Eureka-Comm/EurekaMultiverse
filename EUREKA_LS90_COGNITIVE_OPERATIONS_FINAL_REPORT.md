# EUREKA — LS90 · MASTER LARGE CAPABILITY LOOP: COGNITIVE OPERATIONS / DECISION INTELLIGENCE · FINAL REPORT

**Loop:** EUREKA MASTER LS90 — evolve EUREKA from *cognitive presentation* to **cognitive operations**, specifically to **represent and govern an OPEN_RESEARCH cognitive operation** (an open research question that has NOT yet reached a decision) with Decision Intelligence.
**Working dirs:** backend `D:\DS_ARNES\IA Agentes` (`:8000` running — **not** restarted), frontend `D:\DS_ARNES\IA Agentes\eureka-frontend` (`:5173` running).
**Baseline preserved:** LS89 Next-Gen Cognitive UI (visual 8.7/10, cognitive clarity 9.0) — **not** rebuilt or redesigned.

---

## 1. Executive Verdict

**PASS_WITH_FORENSIC_FINDING**

A real, governed, verified and integrated capability was added: EUREKA can now represent and govern an **OPEN cognitive operation** — an open research question that has **not** reached a decision — via a **Python-derived, read-only `open_research` projection** that flows through the **single `CognitiveProjectionDTO`** into the **Chat ("WHAT REMAINS OPEN")** and the **spatial Cognitive Story (chapter 00 · OPEN / leading edge)**.

The principal forensic finding (captured in §4 and §8) is a **semantic collision**: `OPEN_RESEARCH` already exists in this codebase as a **RAFA deferred/not-implemented capability marker** (`EUREKA_MASTER_STATE_LS88.md:32,66` → `DecisionModel`/optimization/Pareto/Level-3 = `OPEN_RESEARCH`/`DEFERRED`). LS90 introduces the **operation-type** sense of `OPEN_RESEARCH` (an open cognitive operation / no-decision-yet). These are **two distinct senses**; LS90 implements the operation-type sense and does **not** implement the deferred capabilities. This is documented prominently and the protected math (ACFL/GCLV/MathEngine), DecisionModel, optimization/Pareto/utility/selector are all **left unimplemented** (deferred) exactly as LS88 intended.

Verdict driver: the capability is **REAL** (deterministic Python, no mock, no fabricated execution), **VERIFIED** (tsc=0, vitest **36/36** ↑, build ok, backend projection pytest **5/5**, real in-process DeepSeek workflow, real browser E2E `console_errors=[]`), **GOVERNED** (Python-derived + provenance-tagged + honest `OPEN/CLOSED` + absence of LLM authority), and **INTEGRATED** (canonical state → server projection → `CognitiveProjectionDTO` → Chat + Cognitive Story, single-source, no parallel DTO).

---

## 2. Baseline

- **LS89 Next-Gen Cognitive UI = PASS** (visual avg 8.7/10, cognitive clarity 9.0, chat-first command center, spatial cognitive instrument). Verified present and untouched in its design language.
- **Backups (untouched):** `_backup_stable_2026-09-01_132120_NEXTGEN_UI` (frontend 136 + backend 143) and `_backup_pre_LS90_2026-09-01_133137` (fresh, 280 files). Both verified present.
- **Baseline gates pre-change (all confirmed before any modification):**
  - `npx tsc --noEmit -p tsconfig.app.json` → **0**
  - `npx vitest run` → **29/29** (4 files)
  - `npm run build` → **ok** (pre-existing "chunks > 500 kB" warning only)
  - Backend `GET /api/health` → `200`; frontend `GET :5173` → `200`
- **Post-change gates:** tsc **0**, vitest **36/36** (↑ 7 tests added, none removed), build **ok**.

---

## 3. Forensic Discovery

**Question:** *What does `OPEN_RESEARCH` currently mean in EUREKA, and can EUREKA represent & govern an open cognitive operation that has no final decision yet?*

**Search method:** grep over `src/` (eureka + universe + contracts), the frontend `src/`, RAFA docs `*.txt`, root `*.md`, and the E2E/report files. Subagents searched docs/`Documentacion`/contracts and the frontend architecture.

**Findings (backed by file:line):**

| Location | Finding |
|---|---|
| `src/eureka/universe/canonical_state.py` (original) | NO `open_research` type. Exists: `status` enum incl. `OPEN/WAITING_FOR_HUMAN_INPUT`, `knowledge.{unknowns,uncertainty,limitations,contradictions}`, `problem.{unknowns,questions}`, `PredictiveUncertainty.status` (`QUANTIFIED/NOT_AVAILABLE/INVALID`), `knowledge_state='INCOMPLETE'`, `ApplicabilityAssessment.INSUFFICIENT_INFORMATION`, `MathematicalRevalidationResult.INSUFFICIENT_DATA`, `human_requests`, `decision_points`, `decision_state='PENDING'`. |
| `src/eureka/universe/server.py` `_project_state` | Projects a **decision-complete** flow (question→evidence→findings→prediction→prescription→human decision→action→execution→result→frozen) + `story_arc` (LS85). No "what remains open." |
| `src/eureka/universe/work_runtime.py` | Forces LS52 Publisher → always a result; Prescriptor → HITL decision gate. Never a "stop at knowledge; no decision" path. |
| `src/eureka/universe/canonical_state.py` `build_core_analysis` (LS83), `story_engine.py` (LS85) | Established pattern: **read-only, Python-derived governed projections**. `open_research` follows this exact pattern. |
| `eureka-frontend/src/domain/cognitiveProjection.ts` `CognitiveProjectionDTO` | Fields for the closed-decision flow. **No "open/unresolved" field.** DTO already encodes honesty via `NOT_EVALUATED` / `UNSUPPORTED` / `DECISION PENDING` / `projects null`. |
| `eureka-frontend/src/domain/cognitiveProjectionGraph.ts` | 11 node kinds (PROBLEM…FROZEN); `uncertainty` string exists per node. No OPEN node kind. |
| `eureka-frontend/src/domain/narrative.ts` / `cognitiveStory.ts` | A **secondary** 13-stage narrative engine with a `LEARNING` stage (`buildLearningView`) that aggregates unknowns/contradictions/gaps/conditions. This is a **legacy presentation** path, **not** the LS89 DTO/instrument and **not** a governed canonical projection. |
| RAFA `Eureka_Multiverse_5_1_Agents_Definitive_Integrated_Draft (1).txt` | Authority supports **honest open/refusal** states: Structurer "identification of structural ambiguity and missing information"; Predictor `INSUFFICIENT_DATA`/`OUT_OF_VALIDITY_DOMAIN`; Prescriptor `HUMAN_DECISION_REQUIRED`; Eureka-0 human authority; Publisher "does not write certainty"; §16 "no single agent … solves … the problem." |
| Root docs (LS88) | `EUREKA_MASTER_STATE_LS88.md:32,66` use `OPEN_RESEARCH` as a **DEFERRED/not-implemented marker** (`DecisionModel`, optimization/Pareto/utility). `EUREKA_LS88_CONSOLIDATION_REPORT.md`, `large_step_80`, `large_step_82` same sense. |
| `REOPENED` | **Zero matches** anywhere — no REOPENED lifecycle exists. |
| `DecisionModel` | **No code class.** Only a documented deferred marker. Not implemented (as confirmed in §8). |

**Classification of OPEN_RESEARCH (runtime operation type):** **E) nonexistent in code** before LS90 — the term existed **D) only documented** as a deferred-capability classifier, and the *runtime* had only the closed decision pipeline. The raw open signals (unknowns/uncertainty/insufficient-information) were **C) present but scattered** and never surfaced as a governed operation-type projection.

---

## 4. Authority Evidence

Priority used: **RAFA docs > contracts/schemas > governed architecture > real implementation > test/runtime > agent inference.**

| Authority | Supports | Source |
|---|---|---|
| EM 5.1 agents doc (RAFA) | Honest refusal / open states: Structurer ambiguity & missing-info identification; Predictor `INSUFFICIENT_DATA`/`OUT_OF_VALIDITY_DOMAIN`; Prescriptor `HUMAN_DECISION_REQUIRED`; Publisher must not remove uncertainty; Eureka-0 = human authority. | `Documentos Proyecto\RAFA\Eureka_Multiverse_5_1_Agents_Definitive_Integrated_Draft (1).txt` (§4.2, §6.3, §7.2-7.3, §10.2, §13.3, §16) |
| Governed architecture | Read-only Python-derived projections are an established pattern (`build_core_analysis` LS83, `story_arc` LS85). LS90 `build_open_research_state` mirrors it. | `canonical_state.py`, `story_engine.py` |
| Contracts/schemas | `CanonicalWorkState` already models the open signals; `open_research` added as an **additive optional** field (non-breaking). | `canonical_state.py`, `server.py`, `canonicalSchema.ts` |
| LS88 master state | **No contradiction:** `DecisionModel`/optimization/Pareto/utility = DEFERRED (not invented here). Confirms `OPEN_RESEARCH` deferred-marker sense. | `EUREKA_MASTER_STATE_LS88.md:32,66` |

**AUTHORITY CONFLICT / GAP:** none that blocks implementation. The only conflict is the **two senses of `OPEN_RESEARCH`** (operation-type vs deferred-marker), which is **documented** (§8, §20) and not a blocker — the LS90 operation-type is Python-governed and does **not** claim the deferred capabilities as implemented.

**Protected math untouched:** ACFL/GCLV/MathEngine (`acfl_engine.py`, `mathematical_engine.py`, `Meaning(T(R)) ⊇ Meaning(R)`) — **not modified**. The only `Pareto` reference is the pre-existing `artifact_exporter.pareto_frontier` (LS72 ACFL artifact export) — not a selector/optimizer, and not modified.

---

## 5. Capability Matrix

Consistent with the strict definitions (PRESENT=field/type exists; IMPLEMENTED=code does it; INVOKABLE=callable at runtime; EXECUTABLE=actually run; VERIFIED=proven by a real gate/test; INTEGRATED=end-to-end path), tagged per item:

| Capability | PRESENT | IMPLEMENTED | INVOKABLE | EXECUTABLE | VERIFIED | INTEGRATED |
|---|---|---|---|---|---|---|
| `OpenResearchState`/`OpenResearchItem` models (backend) | ✅ | ✅ | ✅ | ✅ | ✅ (pytest) | ✅ |
| `build_open_research_state` deterministic projection | ✅ | ✅ | ✅ | ✅ (real run) | ✅ (pytest + runtime) | ✅ |
| `open_research` exposed in server `_project_state` | ✅ | ✅ | ✅ | ✅ | ✅ (real state shows it) | ✅ |
| `CognitiveProjectionDTO.whatRemainsOpen` (single-source) | ✅ | ✅ | ✅ | ✅ | ✅ (DTO tests) | ✅ |
| Chat "WHAT REMAINS OPEN" (`ExecutiveCognitiveAnswer` Axis 09) | ✅ | ✅ | ✅ | ✅ | ✅ (render smoke + browser E2E) | ✅ |
| Chat "never present open as closed" (Axis 01 OPEN notice; Axis 05 DECISION PENDING) | ✅ | ✅ | ✅ | ✅ | ✅ (render test + browser E2E) | ✅ |
| Chat honest per-stage `DATA NOT AVAILABLE` (no forced Predictor/Prescriptor/Actioner/Installer) | ✅ | ✅ | ✅ | ✅ | ✅ (browser E2E text) | ✅ |
| Cognitive Story chapter `00 · OPEN` (leading edge) | ✅ | ✅ | ✅ | ✅ | ✅ (render smoke + browser E2E) | ✅ |
| `CanonicalWorkStateSchema` retains `open_research` (live path) | ✅ | ✅ | ✅ | ✅ | ✅ (Zod test) | ✅ |
| Backend pytest for `build_open_research_state` | ✅ | ✅ | ✅ | ✅ (5/5) | ✅ | — |
| `DecisionModel` (multi-criteria/preference) | ❌ absent | ❌ | ❌ | ❌ | ❌ | ❌ (deliberately deferred, not invented) |
| Optimizer / selector / Pareto / utility / preference-inference / ranking-authority / autonomous-decision | ❌ absent | ❌ | ❌ | ❌ | ❌ | ❌ (deliberately deferred) |
| Level 3 / external execution | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ (deferred) |
| MONITOR | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ (next frontier, not this loop) |

---

## 6. OPEN_RESEARCH status (before / after)

**Before LS90:** E) nonexistent as a runtime operation type. The term existed only as a **RAFA deferred-capability marker** in docs. The runtime pushed every work through the closed decision chain (Descriptor→Predictor→Prescriptor→HITL decision→Actioner→Installer→Publisher→result), always producing a result, with no way to represent "this is an open research question; no decision yet; here is what remains open." The open signals (unknowns, uncertainty, insufficient information) existed in raw fields but were never surfaced as a **governed operation-type projection** and never shown as "WHAT REMAINS OPEN."

**After LS90:** an OPEN cognitive operation is **representable + governable**. The governed `open_research` projection is computed deterministically by Python on every work, aggregates the real open signals, and reports the honest `operation_kind` (`OPEN_RESEARCH` when no human decision, `DECISION` when reached), `status` (`OPEN` / `OPEN_INSUFFICIENT_INFORMATION` / `CLOSED`), the open items (with provenance `source_ref`), and the `decision_relevant_knowledge` (real artifact ids). It flows through the single `CognitiveProjectionDTO` and is surfaced in the **Chat** ("WHAT REMAINS OPEN", never presenting an open research as a closed decision) and the **Cognitive Story** (an explicit OPEN leading-edge chapter). It does **not** force Predictor/Prescriptor/Actioner/Installer: the surface honestly renders `DATA NOT AVAILABLE` for the stages the open operation genuinely did not reach.

**Demonstrated end-to-end** on a REAL work, `WORK-DB6BCEE8` (see §12): `status=COMPLETED`, `prescriptive_knowledge.prescriptions=0` (no prescription → no forced decision), `open_research.operation_kind=OPEN_RESEARCH`, `is_open=True`, `status=OPEN_INSUFFICIENT_INFORMATION`, **10 open items**, 9 decision-relevant findings.

---

## 7. DecisionModel status (before / after)

**Before & after: does not exist as a code class.** `DecisionModel` is a **documented deferred item** (`EUREKA_MASTER_STATE_LS88.md:66` → "DecisionModel prescriptivo (multi-criterio, preferencias/riesgo) = OPEN_RESEARCH"). LS90 does **not** invent it. It is a listed **deferred item** (§17). Confirmed via code search (`DecisionModel` → 0 class hits; only a `task_fabric.py` string "risk and utility" and pre-existing `pareto_frontier` in `artifact_exporter.py`).

**What LS90 added instead:** an **`OpenResearchState`** projection — which is **not** a DecisionModel/optimizer/selector. It is a read-only derived view (like `build_core_analysis`/`story_arc`) that surfaces the honest leading edge. It performs **no** utility/preference/ranking/optimization and issues **no** decision authority.

---

## 8. Human Authority

- **Unchanged and authoritative:** `LLM=candidato/interpretación/hipótesis/narrativa` (never authority); `Python=govern/validate/persist`; `MathEngine/ACFL=mathematical authority`; `HITL=human authority`; `Canonical State=source of truth`; `CognitiveProjectionDTO=single frontend projection source`.
- `recommended_option ≠ human_decision`; `human_decision → HUMAN_AUTHORIZED → ActionPlan`. Untouched.
- **LS90 does not weaken human authority.** For an open operation it reports **`human_decision=null`, `decision_state=PENDING`, `open_research.decision_reached=False`** — i.e., it **does not** let the system or LLM decide for the human. The Chat's Axis 05 renders **"DECISION PENDING — No human selection recorded (authority PENDING)"** and Axis 01 renders **"OPEN RESEARCH OPERATION · NO DECISION YET — EUREKA has not concluded; the human decision is still pending."**
- **Key detail:** LS90 *detects and surfaces* the absence of a decision (which is the honest truth) rather than inventing one. It never converts an LLM/recommendation into a decision.

---

## 9. Provenance

- Every `OpenResearchItem` carries a **`source_ref`** (e.g. `knowledge.unknowns[0]`, `problem.questions[0]`, `predictive_knowledge.predictions[2].uncertainty`, `human_decision`, `state.result.status`) and a provenance list. The projection carries a top-level `provenance` (["LS90 Python-derived open-research projection", "governed read-only view; no LLM output, no decision authority, no re-router of execution"]).
- `decision_relevant_knowledge` = **real** artifact ids only (FND-*/PRED-*/PRESC-*), never synthesized.
- The items are **not orphaned**: they are derived directly from the canonical state's existing fields with a ref back to the source field.
- `open_research` is computed **inside `_project_state`** (a pure read — `GET /state` remains a **pure read**, F-1 preserved; no advance on read).

---

## 10. Runtime Flow (open operation, as built)

`/api/work/intake` → EM Core (propose problem, CANDIDATE→GOVERNED) → EM Structurer (task network) → [Descriptor → (Predictor ony if in plan)] → if the plan has no Prescriptor/decision, no HITL decision gate is forced → Publisher (LS52) compiles a published result → **status=COMPLETED** with **no human decision**. `_project_state` then computes `build_open_research_state(canonical)` → `open_research`:
- `decision_reached = bool(human_decision.selected_alternative_id)` (the single OPEN/CLOSED signal, Python).
- Aggregates: `problem.unknowns/questions`, `knowledge.unknowns/uncertainty/limitations/contradictions`, `knowledge_state=INCOMPLETE`, `predictive_knowledge.status=UNAVAILABLE` / NOT_EVALUATED predictions / uncertainty NOT_AVAILABLE, `execution_phase=WAITING_FOR_EVIDENCE`, `waiting_for_evidence_ids`, `human_requests` PENDING, `result` PARTIAL/UNAVAILABLE, and `PENDING_HUMAN_DECISION` when none.
- `operation_kind = OPEN_RESEARCH` if `not decision_reached`, else `DECISION`. `status = OPEN | OPEN_INSUFFICIENT_INFORMATION | CLOSED`. This is a **descriptor** of current completion state — it does **not** re-route execution and is **not** an authority judgment.

This is `OPEN` (no decision) → the work stays open as a research operation. There is **no forced** `Predictor/Prescriptor/Actioner/Installer` in the representation: what did not run renders as `DATA NOT AVAILABLE` honestly.

---

## 11. Frontend — what really changed (preserving LS89)

- **`src/domain/cognitiveProjection.ts`** — added `OpenItemKind`, `WhatRemainsOpenItemDTO`, `WhatRemainsOpenDTO`, and the **`whatRemainsOpen`** field on `CognitiveProjectionDTO` + mapping in `buildCognitiveProjection` (reads only the backend `open_research`; never recomputes/invents). **Single-source preserved — no parallel DTO.**
- **`src/domain/canonicalSchema.ts`** — added `open_research: z.any().optional().nullable()` so the **live` workStore` Zod parse retains it** (otherwise it would be stripped).
- **`src/components/cognitive/ExecutiveCognitiveAnswer.tsx`** (Chat — primary) — added **Axis 09 "WHAT REMAINS OPEN"** + `OpenRemainder` component, and an **OPEN RESEARCH OPERATION · NO DECISION YET** notice on Axis 01. Existing Axes 01–08 and the LS89 spatial language are untouched.
- **`src/components/cognitive/chapters/OpenChapter.tsx`** (new) — chapter **00 · OPEN** (the leading edge), in the LS89 spatial language (Kicker, MicroField, Honest, status dot, hairline rails, provenance line). Reads only `dto.whatRemainsOpen`.
- **`src/components/cognitive/chapters/registry.tsx`** — `ChapterId` now includes `open`; `CHAPTERS` has the `00 · OPEN` chapter first; `chapterCount` returns open-item count.
- **`src/components/cognitive/CognitiveStoryTab.tsx`** — `CHAPTER_KINDS.open` added (knowledge-space focus for the OPEN chapter).
- **`src/pages/ShotHarness.tsx`** — dev `/__shot` chapter list includes `open`.

**No visual redesign.** The composition stays a spatial cognitive instrument (axis / trajectory / hero / thread / inspector / knowledge space). The OPEN chapter extends the trajectory (00…08) rather than adding a dashboard of cards. No card-grid surface was introduced.

---

## 12. Browser Evidence (real state, real UI, honest method)

**Method:** the **dev-only `/__shot` screenshot harness** (`src/pages/ShotHarness.tsx`, registered only when `import.meta.env.DEV`) renders over a **real governed state** produced by a **real DeepSeek orchestrator/runtime run** (`WORK-DB6BCEE8`) on which `build_open_research_state` was computed. Playwright + Chromium (headless) captured BEFORE and AFTER. `CONSOLE_ERRORS=[]` in both.

- **BEFORE** (`_ls90_BEFORE_chat.png`, `_ls90_BEFORE_open_chapter.png`) — over the LS89 completed-decision fixture (no `open_research`): the new surfaces exist but show the honest empty state; `console_errors=[]`.
- **AFTER** (`_ls90_AFTER_chat.png`, `_ls90_AFTER_open_chapter.png`) — over the real open-research state `WORK-DB6BCEE8`.
  - Chat: `WHAT REMAINS OPEN` present · `OPEN RESEARCH OPERATION` notice present · `DECISION PENDING` present · open items present.
  - Story (00 · OPEN): `What remains open` present · `OPEN_RESEARCH` present · open items (`UNRESOLVED_QUESTION` / `UNCERTAINTY` / `LIMITATION` / `INSUFFICIENT_INFORMATION` / `DATA_NOT_AVAILABLE` / `PENDING_HUMAN_DECISION`) present · decision-relevant knowledge (`FND-*`) present.
  - `console_error_count = 0`.

**E2E runner:** `python _ls90_browser_e2e.py BEFORE|AFTER` (this session's E2E over the harness) — `console_errors=[]`. Also ran the mandated `python _e2e_chat_answer.py` against the live app (results below). **Honest statement:** the running `:8000` server was started **without `--reload`** and serves the pre-LS90 code (verified: its projection returns `open_research=null`); per the hard "do NOT start/stop it" rule it was **not** restarted. Therefore the **live HTTP chat path through :8000 does not serve `open_research`**; the LS90 backend was verified via the **real code path in-process** (real DeepSeek orchestrator/runtime — see §14) and the UI via the **dev `/__shot` harness + render tests** over a real captured state. To exercise `open_research` through the live `:8000` HTTP chat, a backend-restart is required (documented as the honest limitation).

**Live chat baseline E2E (mandated, honest result):** `python _e2e_chat_answer.py` ran against the live app (`:5173` + `:8000`). Result: **`answer card shown = False`** (the live work paused at a HITL/decision point — the completion card renders only on `COMPLETED`, so it was not reached within the wait window; this is existing live-pipeline behavior and not an LS90 change) **and `console_errors=[]`** (my additive frontend change introduces **zero** console errors, confirming no regression). The authoritative browser E2E for the LS90 capability itself is `_ls90_browser_e2e.py` (above), which rendered the reply card over the real open-research state with `console_errors=[]` and all expected content present.

---

## 13. Validation

| Gate | Result |
|---|---|
| `npx tsc --noEmit -p tsconfig.app.json` | **0 errors** |
| `npx vitest run` | **36/36** (4 files; was 29/29 → +7 tests added, none removed/lowered) |
| `npm run build` | **ok** (only the pre-existing "chunks > 500 kB" warning) |
| Backend `pytest` (new `src/eureka/tests/test_open_research.py`) | **5/5 passed** |
| Real workflow (in-process real DeepSeek pipeline) | **WORK-DB6BCEE8** COMPLETED, no prescription, `open_research=OPEN_RESEARCH / OPEN_INSUFFICIENT_INFORMATION / 10 items` |
| Browser E2E (`_ls90_browser_e2e.py` BEFORE+AFTER) | `console_errors=[]` |
| Live-chat baseline E2E (`_e2e_chat_answer.py`) | `console_errors=[]` (no regression); `answer card shown=False` (work paused at a HITL/decision point — completion card renders only on `COMPLETED`; not an LS90 regression) |
| Backend full-suite collection | `test_cognitive_provider.py` has a **pre-existing** relative-import drift in `fake_provider.py` (`from ..universe.cognitive_provider` → `src.eureka.tests.universe`), documented in LS88 as **LEGACY_DRIFT**; unrelated to LS90 (those files were not touched). |

**Honest note on "verified":** `build_open_research_state` is **VERIFIED** by (a) 5 unit tests on real state shapes and (b) a **real** in-process run (real LLM + real runtime). The **UI surface** is **VERIFIED** by (a) react-dom/server render smoke tests over a real DTO and (b) a real Playwright browser capture over a real state with `console_errors=[]`. Not claimed as "executable through the live :8000 HTTP server" (that path is stale, documented above).

---

## 14. Data Governance (no fabricated data / fake results / authority leakage)

- `open_research` is **Python-derived and deterministic** — it never invents a decision, ranking, utility, preference, or optimizer. It only aggregates real canonical fields.
- **No LLM authority:** the projection's provenance explicitly states "no LLM output, no decision authority." The LLM stays candidate/interpretation/narrative.
- **Honest statuses preserved:** the real open work exposes `human_decision=null`, `decision_state=PENDING`, `decision_reached=False`, and renders `DECISION PENDING` / `DATA NOT AVAILABLE` on the stages it genuinely did not reach. Nothing is `null→0`, `UNKNOWN→known`, `DECISION PENDING→DECIDED`, or `NOT RUN→RUN`.
- **No fabricated execution/result:** the chat shows `RESULT MOMENT · AVAILABLE` only because the pipeline genuinely produced a published literature summary; the decision/action/execution stages show honest `DATA NOT AVAILABLE` (they were never forced).
- **No parallel projection DTO:** `whatRemainsOpen` lives **inside** `CognitiveProjectionDTO` (no `ResearchProjectionDTO`/`DecisionProjectionDTO`/`MonitorProjectionDTO`).
- **No orphan items:** every open item carries a `source_ref` back to the canonical field it was derived from.

---

## 15. Mathematical Integrity (ACFL / GCLV / MathEngine intact)

- **Not modified.** `acfl_engine.py`, `mathematical_engine.py`, GCLV, and `Meaning(T(R)) ⊇ Meaning(R)` are untouched. `git`-level verification: no edits to any math file.
- Predictor remains **ACFL_DETERMINISTIC** (MathEngine, GCLV Eq 4.17). No optimizer/selector/utility was introduced.
- The pre-existing `artifact_exporter.pareto_frontier` (LS72) is an ACFL artifact export helper, not an optimizer — untouched.
- My new code references no ACFL/GCLV/MathEngine internals; it only reads the canonical projection fields.

---

## 16. Remaining Frontier

- **MONITOR** (LS87 noted it as `FUTURE_HARDENING`): deterministic materialization of `action_plan` across runs. Not this loop.
- **Prescriptive DecisionModel** (multi-criteria / preferences / risk / utility): **deferred** (documented `OPEN_RESEARCH` marker sense), not invented.
- **True optimization / Pareto / utility selection / ranking-authority / autonomous-decision:** **deferred**, not invented.
- **Level 3 external execution:** **deferred** (separate infra).
- **Live `:8000` serving `open_research` end-to-end via HTTP:** requires a backend reload/restart (the running process lacks `--reload`). A follow-up could restart it and re-run the HTTP E2E; no code change needed.

---

## 17. Deferred Items (explicitly NOT implemented)

| Item | Status | Reason |
|---|---|---|
| `DecisionModel` (multi-criteria/preference/risk) | DEFERRED | Documented deferred (LS88); needs preference/utility authority not present; would violate "no invented optimizer." |
| Optimizer / selector / Pareto / utility / preference-inference / ranking-authority / autonomous-decision | DEFERRED | Explicitly forbidden by task hard rules + RAFA authority (no invented authority). |
| Level 3 external execution | DEFERRED | Separate infra; forbidden this loop. |
| MONITOR determinism | DEFERRED | LS87 `FUTURE_HARDENING`; not this loop. |
| "What remains open" auto-closing / auto-decision | NOT ADDED | The projection deliberately keeps `decision_reached` human-driven; it never auto-closes an open operation. |

---

## 18. Backup Location

- **Post-LS90 stable backup:** `D:\DS_ARNES\IA Agentes\_backup_stable_2026-09-01_135005_LS90_COGNITIVE_OPERATIONS` (frontend 137 + backend 143 files; excludes `node_modules`/`dist`/`__pycache__`).
- **Prior backups preserved (not deleted):** `_backup_stable_2026-09-01_132120_NEXTGEN_UI` (LS89), `_backup_pre_LS90_2026-09-01_133137` (pre-LS90), and all earlier `_backup_*`.
- **Rollback:** restore `eureka-frontend/` + `src/` from the pre-LS90 or LS89 backup; my changes are additive and isolated to the files listed in §11 + §19.

---

## 19. Changed files (for review)

**Backend:** `src/eureka/universe/canonical_state.py` (added `OPEN_ITEM_KINDS`, `OpenResearchItem`, `OpenResearchState`, `build_open_research_state`); `src/eureka/universe/server.py` (expose `open_research` in `_project_state`); `src/eureka/tests/test_open_research.py` (new, 5 tests).
**Frontend:** `src/domain/cognitiveProjection.ts`; `src/domain/canonicalSchema.ts`; `src/components/cognitive/ExecutiveCognitiveAnswer.tsx`; `src/components/cognitive/chapters/OpenChapter.tsx` (new); `src/components/cognitive/chapters/registry.tsx`; `src/components/cognitive/CognitiveStoryTab.tsx`; `src/pages/ShotHarness.tsx`; `src/domain/cognitiveProjection.forensic.test.ts`; `src/components/cognitive/renderSmoke.test.tsx`; `eureka-frontend/public/__shot_state.json` (now the real open-research state; original preserved at `_ls90_before_shot_state.json`).

**Helper/evidence files (repo root):** `_ls90_inprocess.py`, `_ls90_e2e_runtime.py`, `_ls90_browser_e2e.py`, `_ls90_real_state.json`, `_ls90_before_shot_state.json`, `_ls90_BEFORE_chat.png`, `_ls90_BEFORE_open_chapter.png`, `_ls90_AFTER_chat.png`, `_ls90_AFTER_open_chapter.png`.
