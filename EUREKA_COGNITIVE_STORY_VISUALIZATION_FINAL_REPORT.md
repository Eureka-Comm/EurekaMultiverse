# EUREKA COGNITIVE STORY · VISUALIZATION — FINAL REPORT

**Mission:** Master Large Capability Build — EUREKA COGNITIVE STORY (secondary cognitive surface: Storytelling + Governed Visualization)
**Working dir:** `D:\DS_ARNES\IA Agentes\eureka-frontend`
**Surface:** Tab `cognition` ("EUREKA COGNITIVE STORY"); Chat stays the primary/default surface.
**Single source:** `CognitiveProjectionDTO` (LS86) — the only frontend projection of meaning.

---

## 1. Executive summary

A complete, coherent, connected **COGNITIVE STORY** surface was delivered as a secondary tab inside the
existing `DynamicWorkspace`. Every piece of it (Storytelling, Knowledge Map, Provenance/Lineage, Inspector,
Decision visualization, 8-EM rail affordances, Chat deep-link) reads from **one** immutable projection —
`buildCognitiveProjection(activeWork)` (LS86) — memoized through a new `useCognitiveProjection` hook. No
parallel projection was created; no mock data was introduced (the only added fixture is a **real** backend
state captured from a live run).

The surface honours the hard rules:
- `DECISION` reads **only** `human_decision` (`selectedAlternativeId` + `decisionId` + `HUMAN_AUTHORIZED`), never `recommendedOption`.
- `RECOMMENDED` (recommended_option) and `SELECTED (HUMAN)` are rendered as **separate** surfaces and are impossible to confuse.
- `NOT_EVALUATED` stays NOT_EVALUATED; `SIMULATED` stays SIMULATED; `FROZEN` shows its real `freeze_signature`.
- Missing artifacts render `DATA NOT AVAILABLE` / `No governed graph` — never fabricated.
- Graph edges use **only** real semantics (`derived_from | supports | produced_by | selected_by | authorized_by | executed_as | frozen_as`); the word **`causes`** never appears.

**Regression gates:** `tsc --noEmit` = **0 errors**; `vitest run src/domain/cognitiveProjection.test.ts` = **11/11 pass**
(the LS86 gate, unbroken); full vitest suite = **29/29 pass**; `npm run build` succeeds. A real backend work was
run end-to-end (`intake → 8-EM rail → HITL decision → COMPLETED`) and its final state was used to drive the
projection, graph, and render-smoke tests, proving the Decision surface shows **ALT-001 = the human selection**.

---

## 2. Architecture — before / after

### Before
- `cognition` tab rendered `CognitiveNarrativeConsole` (13-chapter narrative using `buildNarrativeStages` + `buildCognitiveStory` reading many raw `state.*` fields directly).
- `IntelligenceNetwork` (surfaces tab) read raw `state.knowledge.findings`, `state.human_decision`, etc.
- `EMOperationalPipeline` / `NeuralPipelineRail` were a pure passive SVG rail with **no** inspect affordance.
- No single projection was shared by Storytelling + Visualization + Map + Inspector.

### After
```
 CANONICAL STATE  (truth)
        │  buildCognitiveProjection (LS86, unchanged semantics)
        ▼
 CognitiveProjectionDTO  (meaning)  ←─ useCognitiveProjection(activeWork)  [single source]
        │
        ├─► buildCognitiveProjectionGraph()  ──► KnowledgeMap (React Flow)
        │        └─ relatedArtifactsForEM() / emRoleLabel() ──► 8-EM rail inspect
        ├─► StorytellingPanel  (exec summary + WHY/WHAT/EVIDENCE/DECISION/ACTION/RESULT)
        ├─► DecisionView  (ALTERNATIVES vs HUMAN DECISION)
        ├─► ProvenanceChain  (EVI→…→FROZEN, real IDs, DATA NOT AVAILABLE)
        └─► Inspector / AuthorityChip / SourceTag  (artifact · authority · provenance · EM · source field)
```

Chat (DeepSeekCopilot) remains the **primary** surface; the Cognitive Story tab is the **secondary** surface.

---

## 3. CognitiveProjection flow (single source, §3/§30)

New hook: `src/hooks/useCognitiveProjection.ts`

```ts
export function useCognitiveProjection(state: CanonicalWorkState | null): CognitiveProjectionDTO {
  return useMemo(() => buildCognitiveProjection(state), [state]);
}
```

`CognitiveProjectionDTO` (LS86) is the **only** source of cognitive meaning. All new components consume it.
`IntelligenceNetwork` was rewritten to consume the DTO + graph (it previously read raw state fields) so the
surfaces tab obeys the same single-source rule. No `CognitiveProjectionV2` / `StoryProjection` was created.

---

## 4. Storytelling + visualization architecture (§6/§7/§31)

`src/components/cognitive/StorytellingPanel.tsx` — progressive-disclosure narrative.

- **EXECUTIVE SUMMARY** (always open): question, `What EUREKA proposed (recommendation)` vs
  `What the human decided`, execution/frozen status, and a `⚠ PROJECTION CONFLICT` banner when
  ActionPlan ≠ human decision (never autocorrected).
- Collapsible sections (Framer-Motion `AnimatePresence` height transitions):
  - **WHY — EUREKA proposed**: rationale + criteria + alternatives (with `RECOMMENDED` / `HUMAN` tags).
  - **WHAT — discovered & predicted**: findings (with authority chips) + predictions
    (`NOT EVALUATED` when `value == null`).
  - **EVIDENCE**: evidence ids + grounded status.
  - **DECISION — what the human decided**: `selectedAlternativeId` + `decisionId` + `HUMAN_AUTHORIZED`
    (never `recommendedOption`).
  - **ACTION**: action plan details + explicit conflict when it diverges from the human decision.
  - **RESULT**: result id/status/summary + execution + frozen (`freeze_signature`).

Every value is a real DTO field; absent fields render `DATA NOT AVAILABLE` / `—`.

### Authority semantics (§25)
`src/components/cognitive/AuthorityChip.tsx` — text-labeled chips (color + label, never color-only):
`CANDIDATE` (blue) · `VALIDATED` (green) · `UNSUPPORTED` (red) · `NOT_EVALUATED` (amber) ·
`HUMAN_AUTHORIZED` (violet) · `SIMULATED` (teal) · `FROZEN` (amber) · `PENDING` (gray) · `GAP`/missing (red).
`PYTHON_GOVERNED`/`PUBLISHED` map to `VALIDATED`; `LLM_CANDIDATE` maps to `CANDIDATE`.
Predictor role label = **`ACFL_DETERMINISTIC · MathEngine · GCLV`**.

### Connectivity / source annotation (§30)
`src/components/cognitive/SourceTag.tsx` — per-artifact chain `(canonical field → artifact id → EM → authority)`.
If a component cannot identify its source field it labels **`DATA_SOURCE_NOT_IDENTIFIED`** (never a fabricated one).

---

## 5. Knowledge Map (§9/§10)

`src/components/cognitive/KnowledgeMap.tsx` (React Flow, `@xyflow/react`).

- Nodes = every **real** artifact emitted by the backend (problem/evidence/finding/prediction/prescription/
  alternative/decision/action/execution/result/frozen). Each node carries `id`, `kind`, `label`, `status`,
  `authority`, `provenance`, `evidence`, `uncertainty`, producing `em`, and a `SourceTag`.
- Edges use **ONLY** real semantics; **`causes` never appears**. Edge set:
  - finding `→` evidence `derived_from`
  - prediction `→` finding `derived_from`
  - alternative `→` prescription `produced_by`
  - alternative `→` decision `selected_by`
  - prescription `→` decision `supports`
  - action plan `→` decision `authorized_by`
  - action plan `→` its selected alternative `selected_by` (this **surfaces** a projection conflict as two
    different `selected_by` edges — never corrects it)
  - execution `→` action plan `executed_as`; execution `→` result `supports`
  - frozen `→` result `frozen_as`
- **No artifacts →** honest “**Data pending / No governed graph**” panel.
- Graph model is pure & testable: `src/domain/cognitiveProjectionGraph.ts` (`buildCognitiveProjectionGraph`,
  `relatedArtifactsForEM`, `emRoleLabel`, `ALLOWED_EDGE_SEMANTICS`).

---

## 6. Provenance / Lineage (§11)

`src/components/cognitive/ProvenanceChain.tsx` — navigable chain `EVI→FND→PRED→PRESC→DEC→ACT→EXEC→RESULT→FROZEN`
using **real** artifact ids. A step the backend did not emit renders **`DATA NOT AVAILABLE`** (never invented).
Clicking a real step opens the inspector. (Real ids come from `buildProvenanceNodes`/DTD `lineage`.)

---

## 7. Inspector (§23/§24)

`src/components/cognitive/Inspector.tsx` — reusable, driven only by `GraphArtifact`s from the DTO graph.
Opens on node/EM click showing: artifact **id/kind/status**, authority chip, description, **provenance**,
**evidence**, **uncertainty**, **producing EM**, and a `SourceTag`. Missing fields → `DATA NOT AVAILABLE`.
Used inside the Cognitive Story tab, the EM rail, and the Intelligence Network.

---

## 8. Decision visualization (§12)

`src/components/cognitive/DecisionView.tsx` — two clearly separated panels:

- **ALTERNATIVES · system candidates**: each alternative from the prescription; `RECOMMENDED` (blue) iff it is
  `recommended_option`. It is never labelled “selected”.
- **HUMAN DECISION**: `selectedAlternativeId` + `decisionId` + `HUMAN_AUTHORIZED` (violet), read **only** from
  `human_decision`. A `⚠ PROJECTION CONFLICT` banner appears when ActionPlan ≠ human decision.

Proposed / recommended / selected are therefore impossible to confuse.

---

## 9. 8-EM rail integration (§5)

`EMOperationalPipeline` stays at the top of the workspace (unchanged role). Each EM stage is now **clickable**
(`NeuralPipelineRail` gained `onStageClick`):
- Predictor → `ACFL_DETERMINISTIC · MathEngine · GCLV` + prediction/finding/evidence artifacts.
- Prescriptor → alternatives → HITL decision artifacts.
- Installer → ActionPlan → Execution → FrozenResult.
- Descriptor / Structurer / Publisher → their artifacts.

Clicking an EM opens an inline compact `Inspector` (authority + provenance + related artifacts) and dispatches
`eureka:inspect-em` so the Cognitive Story tab can focus the same selection. It reads **only** the DTO/graph,
never raw state. Kept minimal — no dashboard look.

The tab also has an in-tab `8-EM · inspect producing engine` strip.

---

## 10. Chat integration (§20)

`DeepSeekCopilot` gains an `onExploreCognitiveStory` callback. When the work is **COMPLETED** (and no follow-up
message), the completion card shows an **`[EXPLORE COGNITIVE STORY]`** button. Clicking it:
1. sets `uiStore.requestCognitiveFocus('DECISION')` (deep-link), and
2. `DynamicWorkspace.openCognitiveStory()` switches the tab to `cognition`.

`CognitiveStoryTab` consumes the focus on mount and scrolls to the **DECISION** chapter (not the start).

---

## 11. Technology decisions

| Concern | Choice | Rationale |
|---|---|---|
| Graph / lineage | `@xyflow/react` (React Flow v12) | Correct tool for governed artifact graph with real edge semantics; already installed. Cytoscape not needed. |
| Transitions | `framer-motion` | Progressive-disclosure expand/collapse. |
| Quantitative surfaces | `echarts` + `d3` | Already installed and available; the governed graph uses React Flow (more faithful for non-causal semantics); decision surface is a semantic panel, not a chart. |
| Single source | `useCognitiveProjection` + `CognitiveProjectionDTO` | One immutable meaning; no parallel projection. |
| Testing | `vitest` (dev-only) | Needed to keep LS86 tests green + add forensic/e2e tests. |
| Style | `var(--eureka-*)` CSS vars, thin borders, teal/blue/green/violet accents | Preserves the approved minimalist/white/scientific style. |

---

## 12. Files

### Created
| File | Purpose |
|---|---|
| `src/hooks/useCognitiveProjection.ts` | Single-source hook. |
| `src/domain/cognitiveProjectionGraph.ts` | Pure graph/node/edge/EM-role model. |
| `src/components/cognitive/AuthorityChip.tsx` | Text-labeled authority chips. |
| `src/components/cognitive/SourceTag.tsx` | Connectivity/source annotation. |
| `src/components/cognitive/Inspector.tsx` | Reusable artifact inspector. |
| `src/components/cognitive/StorytellingPanel.tsx` | Progressive-disclosure narrative. |
| `src/components/cognitive/KnowledgeMap.tsx` | React Flow governed graph. |
| `src/components/cognitive/ProvenanceChain.tsx` | Lineage chain. |
| `src/components/cognitive/DecisionView.tsx` | ALTERNATIVES vs HUMAN DECISION. |
| `src/components/cognitive/CognitiveStoryTab.tsx` | Tab container (wires all). |
| `src/domain/cognitiveProjection.forensic.test.ts` | Forensic tests A–J. |
| `src/domain/cognitiveProjection.e2e.test.ts` | E2E over real backend state. |
| `src/components/cognitive/renderSmoke.test.tsx` | Render smoke over real DTO. |
| `src/fixtures/eureka_completed_state.json` | Real captured backend state (test fixture). |
| `vitest.config.ts` | Vitest config (excludes backups / legacy script). |

### Modified
| File | Change |
|---|---|
| `src/pages/DynamicWorkspace.tsx` | Tab label + `CognitiveStoryTab` mount + `openCognitiveStory` deep-link + `useUIStore`; removed `CognitiveNarrativeConsole` import. |
| `src/components/DeepSeekCopilot.tsx` | `onExploreCognitiveStory` prop + `[EXPLORE COGNITIVE STORY]` button. |
| `src/components/runtime/NeuralPipelineRail.tsx` | `onStageClick` + clickable stage groups. |
| `src/components/runtime/EMOperationalPipeline.tsx` | DTO+graph + click-to-inspect + inline inspector. |
| `src/components/visualizations/IntelligenceNetwork.tsx` | Now consumes DTO+graph (single source), authority chips + source tags + inspector. |
| `src/store/uiStore.ts` | `cognitiveFocusChapter` + request/consume. |
| `src/domain/cognitiveProjection.ts` | Presentation-only criteria formatting (objects → readable label); no semantic change. |
| `tsconfig.app.json` | Exclude `src/**/*.test.tsx` (consistent with `.test.ts`). |
| `package.json` | Added `vitest` devDependency. |

### Removed
None. (The legacy `CognitiveNarrativeConsole` component file is kept, just no longer mounted in the tab.)

---

## 13. Tests

- `src/domain/cognitiveProjection.test.ts` (LS86) — **11/11 pass** (regression gate, unbroken).
- `src/domain/cognitiveProjection.forensic.test.ts` — **11/11 pass** (A–J):
  - **A** LLM “ALT-02 best” → `humanDecision` stays **ALT-01**; `recommendedOption`=ALT-02 kept distinct.
  - **B** `recommended_option=ALT-02` + `human_selection=ALT-01` → `RECOMMENDED`=ALT-02 / `HUMAN DECISION`=ALT-01 (graph flags).
  - **C** prediction value `null` → `NOT_EVALUATED` preserved.
  - **D** finding `UNSUPPORTED` → `UNSUPPORTED`.
  - **E** execution → `SIMULATED`.
  - **F** ActionPlan ALT-01 vs human ALT-02 → `projectionConflict=true`, **never autocorrected**.
  - **G** no evidence → no `EVIDENCE`/`FINDING`/`PREDICTION` nodes (DATA NOT AVAILABLE downstream).
  - **H** changing Publisher narrative → canonical truth (decision/authority/conflict) intact.
  - **I** click Predictor → `ACFL_DETERMINISTIC · MathEngine · GCLV` + prediction artifacts.
  - **J** click HITL → `HUMAN_AUTHORIZED` decision + HITL role.
  - Edges never use `causes`.
- `src/domain/cognitiveProjection.e2e.test.ts` — **2/2 pass** over a real backend COMPLETED state.
- `src/components/cognitive/renderSmoke.test.tsx` — **5/5 pass** (react-dom/server over real DTO; authority chips,
  DecisionView ALT-001/HUMAN_AUTHORIZED, StorytellingPanel, ProvenanceChain DEC-8b8482 + DATA NOT AVAILABLE,
  Inspector DECISION authority).
- **Full suite: 29/29 pass.**

---

## 14. E2E evidence (real flow)

A live backend run was executed from the running `:8000` server (no server was started by me — it was already up):

1. `POST /api/work/intake` → `WORK-AC272ACA` (RUNNING).
2. Polled `/state`: progressed through `EM Descriptor → EM Predictor → EM Prescriptor`.
3. Reached `WAITING_FOR_HUMAN_INPUT` (Prescriptor decision gate `DEC-8b8482`, options ALT-001/2/3,
   `recommended_option = null`).
4. `POST /api/work/{id}/human_input` `type=SELECTION value=ALT-001`.
5. Polled → **`COMPLETED`** (Actioner → Installer → Publisher).

Final canonical state: `human_decision.selected_alternative_id = ALT-001`, `decision_authority = HUMAN_OPERATOR`,
`frozen_result = FROZEN-a1cbbf` with `freeze_signature = 9a93…`, `state.result = WR-0fde50 AVAILABLE`,
6 predictions all `predicted_value=null` / `NOT_EVALUATED`, 2 findings `VALIDATED`.
`action_plan = null`, `execution_state = null` for this workload.

This real state was captured to `src/fixtures/eureka_completed_state.json` and used to drive the E2E projection,
graph, and render-smoke tests. The **Decision surface renders ALT-001 = the human selection (HUMAN_AUTHORIZED)**,
and the Knowledge Map / Provenance honestly show **no** ACTION/EXECUTION nodes (because the backend produced none).

**Honest limitation:** Playwright is **not** installed in this environment, so a true in-browser E2E
(click the tab, click nodes, click the EM rail) was **not** executed. Instead it was substituted with:
`vite build` (compile), per-module Vite transform checks (dev server serves the new components with HTTP 200),
`tsc` (types), the vitest suite (logic + `react-dom/server` render smoke over the real DTO), and the real backend
flow above. A real browser E2E remains the strongest possible follow-up and is noted as a deferred capability.

---

## 15. Known limitations

- **Action plan / execution were not emitted** by the backend at `COMPLETED` for this demo workload
  (`action_plan`, `execution_state` are null). The frontend **correctly** renders them absent (`DATA NOT AVAILABLE`
  / no ACTION/EXECUTION nodes / `No action plan produced`). It does not fabricate an action plan.
- `recommended_option` was `null` for this run, so the `RECOMMENDED` vs `SELECTED` contrast is demonstrated by
  the synthetic forensic tests (B/F), not this live run.
- No browser/E2E automation (Playwright) available → substituted verification (see §14).
- Batch build chunk-size warning (pre-existing, not an error) — code-splitting is a deferred optimization.
- `src/selectors/decisionSelectors.test.ts` is a legacy script-style file (runs at module load, no vitest suite)
  and is excluded from the vitest runner; it was never runnable under vitest before this mission.

---

## 16. Deferred capabilities (explicitly NOT implemented, per MUST-NOT)

- Mathematical optimization / Pareto selector / autonomous decision / causal inference / Level 3 execution.
- Any change to backend semantics (MathEngine, ACFL/GCLV, Predictor, HITL, canonical state, execution/freeze).
- Any parallel projection or mock data (only the real captured fixture is used, as an explicit test fixture).

When the projection is unsupported it reports `NOT_EVALUATED` / `SELECTION NOT EVALUATED` / `DATA NOT AVAILABLE`
instead of inventing an answer.

---

## 17. Authority + anti-hallucination + performance + regression verification

### Authority
Every artifact surfaces `AuthorityChip` (text + color). Decision authority is always `HUMAN_AUTHORIZED` (from
`human_decision`); predictions stay `NOT_EVALUATED`; execution stays `SIMULATED`; frozen shows the real signature.

### Anti-hallucination
- Single source only (DTO + graph); no raw-state reads in the new surfaces.
- Edges restricted to the 7 real semantics; `causes` prohibited by an explicit allow-list + test.
- Missing artifacts → `DATA NOT AVAILABLE` / `No governed graph` (no invented ids/values).
- `projectionConflict` surfaced, never autocorrected.
- Dev source annotation per artifact (`SourceTag`); fallback `DATA_SOURCE_NOT_IDENTIFIED`.

### Performance
- `useCognitiveProjection` memoizes the DTO; `buildCognitiveProjectionGraph` memoized on DTO change;
  knowledge-map nodes/edges memoized on graph change. No polling added beyond the existing 500 ms work poll.
- React Flow `fitView` + bounded zoom; no heavy per-frame work.

### Regression
- `npx tsc --noEmit -p tsconfig.app.json` → **0 errors**.
- `npx vitest run src/domain/cognitiveProjection.test.ts` → **11 pass** (LS86 unbroken).
- `npm run build` → **succeeds** (one pre-existing chunk-size warning only).
- Dev server (`:5173`) transforms all new modules (HTTP 200) → no Vite compile/overlay error.
- Backend (`:8000`) was already running; I did not start/stop any server.

---

## 18. Backup identifier / path + rollback

- **Backup dir:** `D:\DS_ARNES\IA Agentes\eureka-frontend\_backup_pre_cognitive_story_2026-09-01_102450`
  (contains a full copy of `src\` + `package.json`; created **before** any changes; prior backups were **not** deleted).
  Additional pre-existing backups at the parent `D:\DS_ARNES\IA Agentes\` remain untouched.

**Rollback procedure**
1. Stop the frontend dev server on `:5173`.
2. Copy the pristine `src` + `package.json` back from the backup dir over the working tree, e.g.
   `Copy-Item -Recurse -Force "<backup>\src" .` and `Copy-Item "<backup>\package.json" .`.
   (Manually revert `vitest.config.ts`, the `tsconfig.app.json` exclude, and `package.json`/`npm install` of vitest,
   or `git` the tree if a repo is initialized — the dir is not currently a git repo.)
3. Reinstall if needed: `npm install` (or `npm ci`).
4. Restart `npm run dev` and verify `npx tsc --noEmit` = 0 errors and the `cognition` tab shows the pre-change state.

---

## 19. Final verdict

### **PASS_WITH_FORENSIC_FINDING**

All build/regression gates pass and the complete, coherent COGNITIVE STORY surface is delivered with correct
authority semantics and no fabricated data. The forensic audit surfaced real, documented observations —
none of which block the mission and all of which are reported (not faked):

1. **Backend emits no action_plan/execution_state at COMPLETED** for this demo workload; the frontend
   correctly and honestly renders them as absent (no invented plan/execution; lineage shows `DATA NOT AVAILABLE`).
2. **Criteria objects were leaking as `[object Object]`** in the raw projection display — fixed with a
   presentation-only criteria formatter (no semantic change).
3. **Legacy `decisionSelectors.test.ts`** is a script (no vitest suite) and is excluded from the vitest runner;
   it was never runnable under vitest before this mission.
4. **True browser E2E was not run** (Playwright unavailable); substituted with build + Vite module transforms +
   `react-dom/server` render smoke over the **real** COMPLETED backend state + the live API flow (§14).

These findings do not fail the delivery. Recommend running a Playwright E2E (submit → 8-EM rail → HITL →
COMPLETED → EXPLORE COGNITIVE STORY → DECISION = human selection) as the strongest follow-up.
