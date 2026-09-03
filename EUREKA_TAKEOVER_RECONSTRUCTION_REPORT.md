# EUREKA_TAKEOVER_RECONSTRUCTION_REPORT

Date: 2026-08-29
Agent: continuation harness (DeepSeek Harness)
Working root: `D:\DS_ARNES\IA Agentes` (byte-for-byte copy of `D:\IA Agentes` created this session; original left untouched as backup)
Method: read-only reconstruction pass over backend, frontend, runtime, reports; zero code modifications performed.

---

## REPOSITORY_IDENTITY

- Project: EUREKA — "El Orquestador de la Evolución Cognitiva Dirigida"
- Backend: `src/eureka/universe/` — FastAPI + uvicorn (server.py), pydantic state models, in-memory `works_db` / `evidence_store`.
- Frontend: `eureka-frontend/` — React 19 + TypeScript + Vite 8 + Zustand 5 + Tailwind 4 (NOT `src/eureka-frontend` as older docs claim).
- Toolchain verified: Python 3.12.6 (global; fastapi 0.110, uvicorn 0.30.1, openai 2.21, playwright 1.61, httpx, pydantic 2.13). Node v24.11.0, npm 11.6.1.
- Config: `.env` contains `DEEPSEEK_API_KEY` and `COGNITIVE_ENGINE=deepseek`. DeepSeek API verified reachable (200 OK); default model `deepseek-chat` resolves (aliased to `deepseek-v4-flash`). Local Ollama 0.33.2 running with `deepseek-r1:14b`, `qwen3:8b` (fallback only — see OPEN_GAPS #10).
- Size: the tree contains ~2.66M files (~50 GB) including multiple subprojects (`eureka_mvp`, `eureka-platform`, `airl-compiler`, `packages`, `studio`, `workbench`, `Loop Ralph *`, historical artifacts).
- **GIT_STATE: NO git repository exists.** Verified: no `.git` at root or any candidate dir; recursive search up to depth 4 found none; the original `D:\IA Agentes` also has no `.git` at root. Git discipline (handoff §53) is therefore N/A for the working copy; all modifications are tracked by this report instead.

## ARCHITECTURE

- 8-EM canonical chain: EM Core → EM Structurer → EM Descriptor → EM Predictor → EM Prescriptor → EM Actioner → EM Installer → EM Publisher.
- `WorkOrchestrator.orchestrate(intent)` builds `CanonicalWorkState` from an LLM task proposal; maps tasks to capabilities by `task.owner == cap.canonical_em` (orchestrator.py L191), `step_id = task.task_id` (L247), `work_id = WORK-<8 hex upper>` (L278).
- `WorkRuntime.advance(canonical)` executes at most ONE step per call; `run_work_background` loops while status ∈ {RUNNING, READY} with 0.5 s sleeps and a 50-iteration cap (server.py L419–435).
- `_process_state` (server.py L67–157): repopulates evidence, calls `runtime.advance()` (L82), computes `em_pipeline`, serializes with `work.status = canonical.status` (L131–136).
- Capability registry defaults confirm: `install_action` → canonical_em `"EM Installer"` (capability_fabric.py L84–89); `execute_action` → `"EM Actioner"` (L39–44); `generate_summary`/`generate_report` → `"EM Publisher"` (L120–135); `evaluate_alternatives` → `"EM Prescriptor"` (L155–166).

## CURRENT_RUNTIME (PROVEN)

- `work_runtime.py`:
  - LS41 guard — present: L127/L131–132 `if step.status == "WAITING_FOR_HUMAN_INPUT": return canonical`.
  - LS42 lock — present: L37 `_execution_locks = set()` (module-level **set**, not dict — container type differs from handoff wording), lock key `f"{work_id}_{step_id}"` (L134), re-entry check L135–136, acquire L164, release in `finally` L237–239.
  - Step dispatch: Prescriptor (L591), Actioner (L609), Installer (L619), Publisher (L661–666, only for `generate_summary`/`generate_report` AND `task.owner == "EM Publisher"`).
  - Completion gate: a `produces_result` step that finishes without `canonical.result.status == "AVAILABLE"` becomes GAP `RESULT_UNAVAILABLE` (L179–186, L280–287).
  - Frozen-knowledge branches hardcode `DeepSeekAdapter()` regardless of `COGNITIVE_ENGINE` (L304–306, 334–336, 371–373, 489–490, 568–570).
- `server.py`:
  - Endpoints: `POST /api/evidence`, `POST /api/evidence/{id}/extract`, `POST /api/work/intake`, `POST /api/work/{id}/execute`, `POST /api/work/{id}/human_input`, `POST /api/work/{id}/tool_call`, `POST /api/work/{id}/evidence`, `GET /api/work/{id}/state`, `GET /api/health`.
  - `GET /state` calls `_process_state` → `runtime.advance()` — **still a state-mutating read** (historical re-entry risk), but now guarded by LS41/LS42 so polling is safe during WAITING_FOR_HUMAN_INPUT and cannot double-execute a RUNNING step.
  - `POST /execute` re-orchestrates and REPLACES the canonical state (destructive re-create, not a resume) — server.py L560–566.
  - Dead code: server.py L226 compares an `ExecutionState` object to the string `"WAITING_FOR_EVIDENCE"` (always False).
- `human_input` (server.py L272–397): `HumanInputRequest{request_id?, decision_id?, type, value, rationale}`; types = INFORMATION | SELECTION | PARAMETER (comment L275). **No APPROVAL type.**
  - INFORMATION: answers `human_requests`, appends a VALIDATED finding, sets ALL `WAITING_FOR_HUMAN_INPUT` steps → READY (L319–322).
  - SELECTION: marks matching `decision_points` ANSWERED + `human_selection`; re-arms steps **only for `canonical_em == "EM Prescriptor"` or `"EM Core"`** (L346–356); then `canonical.status = "READY"` + background resume (L395–396).
  - PARAMETER: merges dict into `human_decision.parameters_modified`.
  - Response: `{"status":"RESUMED","contribution_id":...}`.

## CURRENT_FRONTEND (PROVEN)

- Root `eureka-frontend/`; scripts: `dev` (vite), `build` (tsc -b && vite build), `lint` (oxlint). **No `test` script; no vitest/jest installed.**
- `vite.config.ts`: default port 5173; the ONLY proxy is `/api/copilot` → `https://api.deepseek.com`; the EUREKA backend is reached by absolute URL `VITE_EUREKA_API_URL || http://localhost:8000` (no env file sets it → localhost:8000).
- `src/store/workStore.ts`: Zustand store (`activeWork`, `appState`); `startWork` POSTs `/api/work/intake`; `pollState` GETs `/api/work/{id}/state` (guard: only when status RUNNING/READY); polling `setInterval` (500 ms) lives in `DynamicWorkspace.tsx` L19–29.
- `src/domain/canonicalSchema.ts`: `decision_points: z.array(z.any())` (L152) — **no DecisionPoint / HumanInteractionRequest type exists**; `work.status` is `z.string()` (L73); no `canonical` object on the wire (status travels as `work.status`).

## CURRENT_CANONICAL_SCHEMA (PROVEN)

- `CanonicalWorkState` (canonical_state.py L340–419) = Single Source of Truth (`EUREKA_CANONICAL_WORK_STATE_V2`). Status enum comment: OPEN, READY, RUNNING, COMPLETED, PARTIAL, GAP, BLOCKED, FAILED, WAITING_FOR_EVIDENCE, WAITING_FOR_HUMAN_INPUT (L390).
- Key fields: `work`, `execution_plan`, `knowledge`, `predictive_knowledge`, `prescriptive_knowledge`, `action_plan` (L364), `execution_state` (L365), `publication_state` (L366), `frozen_result` (L367), `result` (L371), `active_em` (L374), `active_step_id` (L375), `execution_events` (L381), `human_requests` (L394), `decision_points` (L395), `human_decision` (L397).
- `HumanDecisionPoint` (L72–95): `decision_id` default `DEC-<6hex>`; `status` default `PENDING`; **no `type` field**; `options` list of dicts, `recommended_option`, `human_authority`, `human_selection`.
- `HumanInteractionRequest` (L60–69): `request_id` default `REQ-<6hex>`, `status` default `PENDING`, `type` field exists here.

## CURRENT_HITL_CONTRACT (PROVEN)

- ACTIVE_NOW(decision) ≡ canonical.status == WAITING_FOR_HUMAN_INPUT ∧ decision.status == PENDING ∧ decision.task_id == canonical.active_step_id ∧ active_step_id != null. Serialized as `work.status` in the wire format.
- Prescriptor: creates `HumanDecisionPoint` with alternatives (no `type` field; "SELECTION" is the *answer* type, not an output type).
- Actioner (actioner.py): gates R6.1 relevance, R6.2 prescription, R6.3 selection, R6.4/R6.5 owner/resources, R6.6 DAG/cycles, R6.7 acceptance criteria, R6.8 risk, R6.9 temporal, R6.10 boundary. `_request_human_input` (L135–144, LS44 fix) appends a `HumanInteractionRequest(type="MISSING_INFORMATION")` to `human_requests` and fails the task with WAITING_FOR_HUMAN_INPUT. Produces `ValidatedActionPlan(validation_status="VALIDATED")` with **`acceptance_criteria=[]` hardcoded** (L112).
- Installer (installer.py): gates R7.1–R7.13; consumes `action_plan`; builds `ExecutionRequest`/`ExecutionState`; on SUCCEEDED/PARTIALLY_SUCCEEDED/FAILED creates the freeze (L143–161):
  - `HumanDecisionPoint(decision_id="APPROVAL_FREEZE", originating_em="EM Installer", task_id=task.task_id, question="Freeze this solution as a reusable cognitive asset?", context="Execution completed. The canonical solution is ready to be assembled and frozen.", options=[{APPROVE},{REJECT}], recommended_option="APPROVE")` → status defaults PENDING → step WAITING_FOR_HUMAN_INPUT.
  - If ANSWERED + human_selection == APPROVE → sha256 signature → `FrozenResult(status="FROZEN")` → `canonical_state.frozen_result` → **writes hardcoded path `D:/IA Agentes/R8.8.7.5-FROZEN-SOLUTION-001.json`** (L200–201). If REJECT → no freeze, continues.
- human_input SELECTION resume: re-arms only EM Prescriptor / EM Core steps (server.py L346–356). **No branch for EM Installer.**

## CURRENT_SELECTOR (PROVEN)

- `eureka-frontend/src/selectors/decisionSelectors.ts` L16–41 implements the exact ACTIVE_NOW contract; 0 matches → undefined; 1 → decision; >1 → `console.warn('MULTIPLE_ACTIVE_DECISIONS')` + undefined (safe failure).
- `decisionSelectors.test.ts` is the manual self-executing verification script (8 cases, `console.log` PASS/FAIL) — consistent with handoff §33; nothing runs it.

## CURRENT_WIDGET (PROVEN)

- `HITLDecisionWidget.tsx`: renders only when exactly one ACTIVE_NOW decision (L8–11); radio options from `options[].id/desc`; Confirm `disabled={submitting || !selected}` (L88); no auto-select, no auto-submit; POST body `{type:'SELECTION', decision_id, value, rationale:'Human selected alternative from UI'}` (L37–42); HTTP error keeps context and shows message; success → status SUBMITTED → widget unmounts → `pollState()`.
- **Mounted TWICE**: `DynamicWorkspace.tsx` L97 (main content) AND `DeepSeekCopilot.tsx` L341 (left panel, which DynamicWorkspace renders at L38). Duplicate decision UI when the workspace is active.

## CURRENT_EM_CHAIN / CURRENT_PUBLISHER_CHAIN (PROVEN)

- Publisher (publisher.py) gates: R8.1 relevance; R8.3 requires `knowledge.findings`; anti-hallucination content rules; R8.13 **requires `frozen_result`** else `WAITING_FOR_EVIDENCE "No Frozen Solution available to publish"` (L112–115); produces `PublishedResult(PUB-<6hex>)` appended to `publication_state.publications`, `PublicationInput`, and `WorkResult(status="AVAILABLE")` into `canonical_state.result` (L119–154).
- Consequence: Publisher can only succeed AFTER a successful Installer freeze; without freeze it stalls at WAITING_FOR_EVIDENCE.

## HISTORICAL_FIXES_RECONCILED

| Claim | Code evidence | Verdict |
|---|---|---|
| LS41 WAITING_FOR_HUMAN_INPUT guard in work_runtime | L131–132 | PROVEN |
| LS42 execution lock keyed work_id+step_id | `set()` L37, key L134, acquire L164, release L237–239 | PROVEN (container is a `set`, not a dict) |
| LS43 Actioner WAITING without HumanRequest (historical) | fixed by LS44 code below | SUPERSEDED |
| LS44 `_request_human_input()` in actioner | actioner.py L135–144 | PROVEN |
| LS38 single widget mounted in Work UI | DynamicWorkspace L97 AND DeepSeekCopilot L341 | PARTIAL — mounted, but twice now |
| LS40 GET /state triggers execution | server.py L581 → `_process_state` L82 → `advance()` | PROVEN (mitigated, not removed) |
| No Jest/Vitest; manual selector verification script | package.json; decisionSelectors.test.ts | PROVEN |
| CanonicalWorkState as primary state source | canonical_state.py L340–419 | PROVEN |
| Decision ids auto DEC-xxxxxx | default `DEC-<6hex>` (L73) | PROVEN generally; Installer freeze overrides with literal `"APPROVAL_FREEZE"` |
| Actioner gates (owner/criteria/deadline) | actioner.py L42–49, 68–77, 84–94 | PROVEN |
| Installer freeze PENDING decision with APPROVE/REJECT | installer.py L143–161 | PROVEN |

## KNOWN_CONTAMINATED_WORKS / CURRENT_CLEAN_WORKS

- From handoff (code-level confirmation pending runtime inspection): WORK-6E03FAAF = contaminated (duplicated decisions/prescriptions/events). WORK-13AAF5E4 (LS42), WORK-7D3119A4 (LS44) = clean verification works. Runtime store is in-memory per process, so historical works do not persist into a fresh server run; LS45 will create a fresh Work.

## OPEN_GAPS

1. **Installer resume deadlock (RUNTIME-PROVEN in LS45 as FRONTEND_POLLING_LIFECYCLE_GAP — see large_step_45_installer_hitl_verification_report.md):** the freeze IS reached server-side (WORK-3DFF7C24, WORK-D5CE2DE1: exactly one PENDING APPROVAL_FREEZE, ACTIVE_NOW valid), but the UI never displays it because polling stops after the mandatory Prescriptor HITL answer. Separately (still static): after approval, no code path re-arms the EM Installer step (server.py L346–356 handles only Prescriptor/Core), and the LS41 guard returns `advance()` early while the step is WAITING_FOR_HUMAN_INPUT. Predicted: decision → ANSWERED, step stays WAITING, status sticks at READY, Installer never resumes, freeze never applied, Publisher unreachable.
2. **Resume re-execution risk:** if the step were re-armed, `EMInstaller.execute_task` restarts from Gate R7.1 (new REQ/EXEC ids, re-executes all actions, overwrites `execution_state`) — duplicate execution rather than a true resume.
3. **Hardcoded output path:** Installer writes `D:/IA Agentes/R8.8.7.5-FROZEN-SOLUTION-001.json` — the original folder, not the workspace copy (portability + cross-folder write).
4. **Widget double-mount** (DynamicWorkspace + DeepSeekCopilot) → duplicate HITL UI; two independent Confirm buttons for the same decision.
5. **GET /state mutates state** (advance under guard) — safe now, but violates read semantics.
6. Actioner hardcodes `acceptance_criteria=[]` in the frozen plan.
7. server.py L226 dead resume branch (`execution_state` object vs string).
8. Prescriptor marks `prescriptive_knowledge.status="FROZEN"` even when HUMAN_DECISION_REQUIRED (prescriptor.py L148).
9. Publisher path requires freeze → default pipeline without `install_action` can never publish.
10. `ProviderBackedCognitiveEngine` (Ollama) raises NotImplementedError for predictions/prescription/action_plan/publication → Ollama fallback cannot finish the full chain; DeepSeek API is the only viable provider for LS45.
11. Frontend schema `decision_points: z.array(z.any())` — no structural typing for the HITL contract.

## CONTRADICTIONS (handoff vs actual code)

1. Handoff frontend path `src/eureka-frontend/` — actual: `eureka-frontend/` (top level). Also `stores/workStore.ts` → actual `store/workStore.ts`.
2. Handoff `_execution_locks` "dict" — actual `set` of `"workid_stepid"` strings.
3. Handoff "Prescriptor uses decision selection / SELECTION type" — SELECTION is the client answer type; Prescriptor emits `HumanDecisionPoint` (no `type` field).
4. Handoff "Decision IDs generated automatically (DEC-xxxxxx)" — true by default, but Installer freeze uses literal `decision_id="APPROVAL_FREEZE"`.
5. Handoff "single widget mounted (LS38)" — widget is now mounted twice.
6. Handoff §53 git discipline — no git repository exists in either the copy or the original.
7. Handoff "canonical.status" — frontend reads `work.status` (wire mapping, semantically identical).

## CONFIDENCE

- HIGH (code-verified with line references) for: selector contract, widget no-auto-submit/Confirm-disabled contract, LS41/LS42/LS44 code presence, Installer freeze creation, Publisher freeze requirement, provider wiring.
- HIGH (static prediction, pending runtime proof) for: Installer resume deadlock (OPEN_GAPS #1) — this is the prime candidate for LS45's FIRST_REAL_GAP.
- MEDIUM for historical-works claims (not yet runtime-verified; in-memory store resets anyway).

## CURRENT_FRONTIER

- LARGE STEP 45 — INSTALLER_HITL_VERIFICATION — EXECUTED (2026-08-29) and STOPPED AT FIRST_REAL_GAP: FRONTEND_POLLING_LIFECYCLE_GAP (freeze reached in backend, never displayed in UI). Details: `large_step_45_installer_hitl_verification_report.md`; updated state: `EUREKA_MASTER_HANDOFF_CURRENT_STATE.md`.
- NEXT_FRONTIER: LS46 — minimal frontend polling fix → freeze display verification → (LS47) Installer resume path → Publisher.
- Environment used: backend uvicorn on 127.0.0.1:8000, frontend Vite on 127.0.0.1:5173, DeepSeek API verified, Playwright 1.61 + Chromium.
