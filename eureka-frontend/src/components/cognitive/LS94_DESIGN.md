# LS94 — COGNITIVE OPERATION MAP · Design before code (FASE 1)

> Role: Senior Cognitive UX Architect + Information Visualization Scientist.
> Goal: a **single-screen comprehension surface** for the 6 cognitive stages so a
> stranger reads the whole operation in ~3 seconds with **no scroll, no Inspector, no legend**.
> Technology is subordinated to comprehension — **SVG/DOM, no GPU/WebGL/Three.js**.

---

## 0. Scope & hard constraints

- Consumes the **same** `CognitiveProjectionDTO` produced by `buildCognitiveProjection`
  and the **same** `buildCognitiveProjectionGraph`. **No new DTO**, no parallel model,
  no duplicated authority logic.
- The 3D Cognitive Field is **SECONDARY = Knowledge Space / Explore**. It is **not**
  rewritten. A PRIMARY/SECONDARY entry toggles UNDERSTAND (Operation Map) vs EXPLORE (3D).
- Not a card wall, not a generic workflow, not a dashboard, not React Flow.
- Result = dominant destination. Human decision = unmistakable, distinct from `recommendedOption`.

---

## 1. The 6 stages (exact real mapping, never invented)

| Stage | DTO source | Real semantics |
|---|---|---|
| **QUESTION** | `dto.problem` (+ `dto.question`) | The ORIGIN. The cognitive opening. |
| **DISCOVERY** | `dto.evidence[]` + `dto.findings[]` | MANY source facts → FEW distilled conclusions (evidence→finding convergence, real `derived_from`). |
| **EVALUATION** | `dto.predictions[]` (ACFL/GCLV/MathEngine) | The MATHEMATICAL state. `NOT_EVALUATED` is honoured — never a fake number. |
| **DECISION** | `dto.humanDecision` (+ `dto.recommendedOption`) | SOVEREIGN **HUMAN** authority, visually distinct from the system recommendation. |
| **ACTION** | `dto.actionPlan.steps[]` (exact N real steps) | The PATH / transformation that carries decision→result. |
| **RESULT** | `dto.result` + `dto.frozenResult` | The DOMINANT destination. `AVAILABLE/FROZEN/SIMULATED/DATA NOT AVAILABLE` honest. |

**Absent stage rule:** an absent stage is rendered as an **explicit** honest marker
(`NOT_EVALUATED` / `DATA NOT AVAILABLE` / `DECISION PENDING`) in its own stage region.
Never silently dropped, never invented to fill space.

---

## 2. Composition scheme — ONE dominant composition

A single **horizontal cognitive axis** (the spine) running **origin → destination** (left → right).
The 6 stages are anchored on that spine as **six distinct visual primitives** — not six cards.
Content blooms **around** the spine (up / down / taller / denser) so the field reads as one
continuous instrument, not a row of boxes.

Geometric canvas (SVG `viewBox="0 0 1240 560"`, `preserveAspectRatio="xMidYMid meet"`):

```
    QUESTION        DISCOVERY            EVALUATION      DECISION         ACTION         RESULT
      o              .·.·.     (a)        ⌚━┳━┳━           ▓▓             ╱▁╲            ▓▓▓▓▓
   (open ring)     dots→nodes  gauge(tick)  AACFL  authority gate   staircase 01..0N   dominant terminal
      │                 │                │                │                │                │
      └─────────────────┴────────────────┴────────┬───────┴────────────────┴────────────────┘
                        (spine + directional flow, origin(left) → destination(right))
```

- **X-positions are content-weighted, not uniform** (Discovery is the widest for the cloud;
  Decision is a narrow vertical gate; the Result is the widest+tallest, the terminal).
- **Vertical extent differs per stage** (cloud blooms up, staircase rises, terminal is heavy).
- A continuous spine hairline + small arrowheads connect the trunks into **one flow**.

### 2.1 Why this is NOT a card wall / generic workflow / dashboard
- No uniform rectangles of equal size in a row. Each stage is a **different primitive**
  (open ring / dot-cloud / tick gauge / vertical authority gate / rising staircase / closed terminal),
  at a different height, width, density and vertical offset.
- The **spine is continuous** — the stages are stations on one cognitive flow, not tiles.
- Distinct **direction grammar**: origin is a point, discovery converges, evaluation measures,
  decision is a sovereign gate, action ascends, result closes. Form + motion of composition, not color-only.
- There is **no React Flow / node-editor chrome**, no pareto, no utility, no selector, no monitoring.

---

## 3. Visual grammar per stage + WHY each form communicates its stage

Form **precedes** label; the geometry must be legible even with text hidden (§39).

### QUESTION — ORIGIN · singular open ring, small but focal
- **Form:** a single hollow circle (open ring, empty centre) resting on the spine at far left.
  Nothing enters it — it is the point of departure.
- **Why:** an open ring is an uncrossed opening — the cognitive *question* begins empty.
  Singular + small + crisp reads as "the start", not "a tile". Colour = PROBLEM steel-blue.

### DISCOVERY — MANY→FEW convergence · source cloud → distilled nodes
- **Form:** a dense point-cloud (evidence) on the outer/upper side of the region converging,
  via **real `derived_from` links**, into fewer, larger finding nodes that settle toward the spine.
  Density **decreases** inward; pointer/anchor points converge inward.
- **Why:** the literal act of discovery is *many raw facts compressed into few conclusions*.
  Reading density drop left→in reads as distillation. Counters (`N evidence → M findings`) are real.
- **Honesty:** the geometry reflects the **real** cardinality. If a work has 1 evidence and 7 findings
  (this project's fixtures), it renders as a source→conclusion transform with the real numbers — the
  map never pretends the cardinality is many→few when the DTO says otherwise (see §5).

### EVALUATION — MATHEMATICAL STATE · measurement gauge, no fake number
- **Form:** a thin measuring instrument (tick-rail) with mono engine identity
  (`ACFL_DETERMINISTIC · MathEngine · GCLV`). A needle/reading only if a **real** numeric value exists.
- **Why:** ticks read as *measurement*; the instrument reads as "numbers are computed here".
  When all predictions are `NOT_EVALUATED` (value `null`, real in both fixtures), the gauge shows an
  **explicit `NOT_EVALUATED`** band — **no needle, no fake R², no fake forecast**. The empty measurement
  instrument, plus amber state, never impersonates a real prediction.
- **Colour:** PREDICTION teal.

### DECISION — SOVEREIGN HUMAN AUTHORITY · vertical gate breaking the flow
- **Form:** a **tall, bold vertical gate** (colonnade) that deliberately interrupts the horizontal
  rhythm. Two clearly separated tracks inside it:
  - `EUREKA RECOMMENDED` ← `dto.recommendedOption` (small, cognitive-blue CANDIDATE)
  - `HUMAN DECIDED` ← `dto.humanDecision.selectedAlternativeId` (large, violet **AuthorityChip**)
- **Why:** authority must be *unmistakable* and must break monotony — the human decision is the one
  place autonomy lives, so it gets a completely different weight/geometry. Reuses the **AuthorityChip**
  visual language (violet `HUMAN_AUTHORIZED`) and the existing `.ci-human-decision` look. The two tracks
  are rendered **side by side, never merged**: `recommended_option` is never shown as "selected".
- **Honesty:** if `humanDecision` is `PENDING`, the HUMAN DECIDED track is an **empty outlined** lane
  with `DECISION PENDING · human authority`. If `recommendedOption === humanDecision`, two tracks still
  render and the divergence/agreement is explicit. If they **differ** (`projectionConflict`), a conflict
  marker is shown — never auto-corrected.

### ACTION — PATH/TRANSFORMATION · rising N-step staircase
- **Form:** a **rising staircase** (a connected polyline climbing left→right) with a numbered step
  node (`01..0N`) at each vertex. Reads as "carry the decision toward the result".
- **Why:** an ascending ordered turnstile *inherently* means "this carries from A to B". The **N is exact**
  (`dto.actionPlan.steps.length`) — never hardcoded. Steps carry their real status
  (PENDING/RUNNING/COMPLETED) and short description.
- **Honesty:** if `actionPlan` is `null` (real in both fixtures) the staircase lane is an **empty dashed**
  path with `DATA NOT AVAILABLE — no action plan emitted`.

### RESULT — DOMINANT DESTINATION · heavy closed terminal
- **Form:** the **largest, boldest, highest-contrast** element in the whole map — a closed,
  filled/shaded terminal block at the far-right end of the spine, with strong weight and closure.
- **Why:** the eye must **end** here. Position (right/destination) + scale (largest) + contrast +
  closure = the resolution. Shows the real `result.status` (`AVAILABLE`→PUBLISHED) and the
  `frozenResult` (`FROZEN` + signature), plus a truncated real summary.
- **Honesty:** if `result` is absent, an **empty but dominant** terminal reads `DATA NOT AVAILABLE`.
  `frozenResult` keeps its `FROZEN` marker (amber) and `freeze_signature`. `SIMULATED` stays SIMULATED.

---

## 4. Honesty layer (never invents)

| Case | How the map renders it |
|---|---|
| Prediction `NOT_EVALUATED` (value null) | Empty measurement gauge + `NOT_EVALUATED` amber band. No needle/number. |
| ActionPlan `null` | Empty dashed staircase + `DATA NOT AVAILABLE — no action plan emitted`. |
| Result absent | Dominant empty terminal + `DATA NOT AVAILABLE`. |
| Execution `simulated` | Result shows `SIMULATED` (never EXECUTED). |
| `frozenResult` present | Terminal shows `FROZEN` + real signature. |
| Human decision `PENDING` | `DECISION PENDING · human authority`; the HUMAN DECIDED track is empty-outlined. |
| `recommendedOption` present | Always a separate `EUREKA RECOMMENDED` track, never "selected". |
| `recommendedOption != humanDecision` | Both tracks diverge; conflict marker; never auto-corrected. |

---

## 5. Real data coverage (the two project shot fixtures)

This matters for honesty — the design must match what the real data contains, and show honest
markers where it does not:

| Field | `__shot_state.json` (open research work) | `__shot_completed_state.json` (completed) |
|---|---|---|
| `problem` | ✅ objective present | ✅ objective present |
| `evidence[]` | 1 (`EVI-CONTEXT`) | 1 (`EVI-CONTEXT`) |
| `findings[]` | 7 (3 VALIDATED, 4 UNSUPPORTED) | 2 (VALIDATED) |
| `predictions[]` | 0 | 6, **all `NOT_EVALUATED`** (value null) |
| `prescription` | none | 1 (3 alternatives ALT-001/2/3) |
| `humanDecision` | none → PENDING | `DEC-8b8482`, selected `ALT-001` (`HUMAN_AUTHORIZED`) |
| `recommendedOption` | null | null (this fixture) |
| `actionPlan` | **null** | **null** |
| `execution` | null | null |
| `result` | AVAILABLE (summary) | AVAILABLE (summary) |
| `frozenResult` | FROZEN (+signature) | FROZEN (+signature) |

Consequence: in BOTH real fixtures the ACTION stage is **honestly DATA NOT AVAILABLE** and the
EVALUATION gauge is **honestly NOT_EVALUATED**. The map must render those as explicit honest markers,
not fill them. The `recommendedOption ≠ humanDecision` and `recommendation present` branches do not
occur in these two fixtures; they are exercised by a **derived** state (a clone of the completed fixture
with `decision_points[0].recommended_option` set to a different alternative and an `action_plan` added)
that still runs through the **real `buildCognitiveProjection`** — so the verification is of the real
pipeline, and the capture is clearly labelled as a synthetic state.

---

## 6. Single-screen / no-scroll / SSR

- The map is a **fixed-height** self-contained container (`height: clamp(500px,62vh,560px)`,
  `overflow: hidden`) with the SVG using `preserveAspectRatio="xMidYMid meet"` → the whole composition
  always fits inside its box, no mandatory scroll. It is the **first** surface of the Cognitive Story.
- The rendering is **pure SVG + DOM**; no `window`/`document` reads at render time (guarded with
  `typeof window !== 'undefined'`), so it mounts over `react-dom/server` `renderToString` in the
  render-smoke test suite without throwing.
