# EUREKA LS93 v6 — REMEDIATION LOOP · Report

**Date:** 2026-09-01 · **Scope:** exactly the 5 verified defects below. No architecture change to `CognitiveStoryTab.tsx` / `CognitiveField.tsx`; `CognitiveProjectionDTO` remains the single source; ACFL / GCLV / MathEngine untouched.

**Validation (all green):**
- `npx tsc --noEmit -p tsconfig.app.json` → **0** errors
- `npx vitest run` → **56 passed** (8 files; +4 new Defecto-2 backend-honesty tests)
- `npm run build` → **ok**
- Real browser (Playwright/Chromium via `/__shot`) → `console_errors=[]` **on every capture**

Evidence files live in `D:\DS_ARNES\IA Agentes` (`_ls93v6_*.png` / `_ls93v6_*.json`).

---

## DEFECTO 1 — High-end visual verification (capture + grammar test)

**What changed:** nothing in the renderer geometry — this is a *verification* (the prior PASS was delivered without photographic evidence). Evidence attached: full capture + `?nolabels=1` capture + a new strict `?bare=1` capture (form-only, see Defecto 5).

**Captures** (`?state=completed&m=graph`, real COMPLETED work `WORK-AC272ACA` with human decision `ALT-001`):
- Full path view, no selection: `_ls93v6_D1_full.png` / `_ls93v6_D1_full_field.png`
- Same with `?nolabels=1`: `_ls93v6_D1_nolabels.png` / `_ls93v6_D1_nolabels_field.png`
- Strict form-only `?bare=1`: `_ls93v6_D1_bare.png` / `_ls93v6_D1_bare_field.png`

All captures: `console_errors=[]`, `data-backend=WEBGL2`, camera focus `data-focused=WR-0fde50`.

**Per-class legibility verdict** (form/size/position alone, no node text — from `_ls93v6_D1_bare_field.png` and `_ls93v6_D1_nolabels_field.png`):

| Class | present in capture | form (no text) | size / position | distinguishable? |
|---|---|---|---|---|
| QUESTION | yes | sphere + thin flat ring; **origin (leftmost)** | small; start of axis | ✅ |
| EVIDENCE | yes | **plain** sphere (no ring, no halo) | small | ✅ |
| FINDING | yes | sphere + translucent **wireframe halo** | large | ✅ |
| PREDICTION | yes | **flat wireframe plane** on grid (ghost) | mid | ✅ |
| PRESCRIPTION | yes | sphere + **horizontal collar torus** | small/mid | ✅ (by collar) |
| HUMAN DECISION | yes | sphere + **double heavy ring**, elevated | **largest / highest** | ✅ |
| ACTION | **NOT in fixture** | (renderer: discrete segments) | — | ⚠️ not photographable (see note) |
| RESULT | yes | **large flat hexagonal plate** (terminal) | largest | ✅ |
| FROZEN | yes | **octahedron + cage** ring | small | ✅ |

**Notes (honest, not over-claimed):**
- **ACTION is not present** in this completed work (`action_plan` / `execution_state` are absent from `__shot_completed_state.json` AND `__shot_state.json`). Its glyph (a row of discrete step-cylinders) is unique in the renderer (`cognitiveFieldRenderer.ts` `'action'` case), so it is distinguished *by geometry definition*, but it **cannot be photographed** from the real fixtures. No fix claimed for ACTION.
- **QUESTION ↔ ALTERNATIVE** are form-similar (both sphere + thin ring). ALTERNATIVE is **not** one of the 9 tested classes; the pair is separated by **position** (QUESTION always at the origin, ALTERNATIVES in the field core). No geometry change was required for the 9-class test.

**Result:** the 8 classes the completed work exposes are distinguishable by form/size/position; ACTION is absent from the fixtures (noted). Defecto 1 is closed with attached photographic evidence.

---

## DEFECTO 2 — `detectGpuBackend()` honesty bug

**What changed** (root cause was in `CognitiveField.tsx` + the renderer that feeds the HUD):

1. **`src/components/cognitive/CognitiveField.tsx`** — `detectGpuBackend()` now returns the REAL backend instead of falsely labeling a WebGL1-only browser:
   - `c.getContext('webgl2')` → `'webgl2'`
   - else `c.getContext('webgl')` → `'webgl1'` (was `'webgl2'` — the bug)
   - else → `'none'` (DOM/SVG fallback)
   - Return type is the new exported `DetectedBackend = 'webgl2' | 'webgl1' | 'none'`.
   - Mode decision made honest: `webgl2 → 'gpu'`, else `'dom'` (three.js r185 renders GPU only on WebGL2, so a WebGL1-only / no-GL browser falls back to the DOM/SVG projection instead of crashing; `detectGpuBackend` still reports the true capability).
2. **`src/components/cognitive/cognitiveFieldRenderer.ts`** — the HUD value comes from the renderer's `onBackend` callback. It now detects the **actual** context version it created: `isWebGL2Context(renderer.getContext()) ? 'WEBGL2' : 'WEBGL1'` (added `'WEBGL1'` to `RendererBackend`). The HUD can therefore never claim a backend that is not rendering.

**Evidence:**
- Real browser (WebGL2): HUD reads **`renderer · WEBGL2`**, `data-backend="WEBGL2"` — matches the actual three.js WebGL2 renderer. (`_ls93v6_D1_full.json`)
- WebGL1-only context (Playwright stub: `getContext('webgl2')`→null, `getContext('webgl')`→truthy; probe log `["webgl2","webgl",…]`): the app does **not** crash, renders the DOM/SVG fallback, and the HUD honestly reports **`renderer · DOM/SVG`** (the actual renderer path). (`_ls93v6_D2_webgl1.json`, `_ls93v6_D2_webgl1_field.png`)
- Unit test `cognitiveField.backend.test.ts` (equivalent evidence): `detectGpuBackend()` returns `'webgl1'` for a WebGL1-only browser, `'webgl2'` for WebGL2, `'none'` for neither. **4 tests pass.**

The HUD in the real browser (`WEBGL2`) and in the WebGL1-only simulation (`DOM/SVG`) each show a backend that **actually renders**, and `detectGpuBackend` never labels WebGL1 as webgl2.

---

## DEFECTO 3 — Scores with measurable rubric

Each score now has ≥3 **measurable** sub-criteria with real measured values (from captures / renderer constants), not prose.

**Cognitive Clarity**
| sub-criterion | measured value |
|---|---|
| classes distinguishable by form alone (bare capture) | 8 of 9 exposed classes (7 clearly + PRESCRIPTION by collar); ACTION absent from fixture |
| camera-focus correctness (targets RESULT) | `data-focused=WR-0fde50` = `result.result_id` → **RESULT** ✅ |
| console errors on capture | **0** |
| governed artifacts surfaced | **17** (SR block: "17 governed artifacts · decision reached") |

**Visual Hierarchy**
| sub-criterion | measured value |
|---|---|
| legend label-overlap count | **0** (13 items, 3 grouped rows, no overlapping boxes measured in browser) |
| grid / axis / layer opacity | grid **0.035**, axis tube **0.5**, layer base `{L1:1.0, L2:0.8}` (renderer constants) |
| authority height elevation | DECISION elevated highest (y ∝ authority; largest in re, double ring) |
| legend rows | 3 (COGNITIVE AXIS / FIELD / STATE) |

**Spatiality**
| sub-criterion | measured value |
|---|---|
| grid opacity measured | **0.035** (`GridHelper` material, transparent) |
| axis continuity (thread) | continuous CatmullRom axis **QUESTION→RESULT**, 17 artifacts, start+end framed (`frameAxis`) |
| 3D depth separation | path raised at y=0 along z=0.9 camera depth; field entities recede (authority height vs field depth) |
| camera framing | `frameAxis` keeps QUESTION & RESULT both visible |

**Information Density**
| sub-criterion | measured value |
|---|---|
| % viewport real content vs empty (graph field, bare capture) | **6.27% content / 93.73% near-white empty** (`_ls93v6_pixels.py`) |
| % viewport content vs empty (full capture) | **8.15% content / 91.85% empty** |
| Question-chapter card occupancy (before → after) | **2.96% → ~44%** (area 202886 → 13767) |
| artifacts per field | 17 nodes along the axis |

---

## DEFECTO 4 — Empty cards (fix + per-card audit)

**Root cause:** the reusable `.ci-field` micro-cell class collided with the Cognitive Field *surface* `.ci-field` rule (`min-height:560px; height:100%; border; background`), making every micro-card a 560px fixed-height box with one line of content.

**What changed:**
1. **`src/components/cognitive/cognitiveField.css`** — scoped the field-surface rule to `.ci-field[data-cognitive-field]` so it no longer leaks onto micro-cells → cards are now content-linked (auto) height.
2. **`src/components/cognitive/StorytellingPanel.tsx`** — summary grid `items-start`, so the "What EUREKA proposed (recommendation)" card collapses to a single-phrase height instead of reserving room to match its content-rich sibling.

**Per-card audit (real area measurement, px):**

| card (file) | BEFORE `content_area` | BEFORE occupied | AFTER `content_area` | AFTER occupied | verdict |
|---|---|---|---|---|---|
| PROBLEM ID (`QuestionChapter.tsx` MicroField) | **202,886** (560px) | ≈6,007 (2.96%) | **13,767** (38px) | ≈6,040 (44%) | fixed ✅ |
| AUTHORITY | **202,895** | ≈7,386 (3.6%) | **13,768** | ≈7,427 (54%) | fixed ✅ |
| EVIDENCE | **202,886** | ≈6,007 (3.0%) | **13,767** | ≈6,040 (44%) | fixed ✅ |
| FINDINGS | **202,895** | ≈6,007 (3.0%) | **13,768** | ≈6,040 (44%) | fixed ✅ |
| "What EUREKA proposed (recommendation)" (`StorytellingPanel.tsx` SummaryField) | **243,040** (560px) | ≈7,830 (3.2%) | **15,461** (36px) | ≈7,866 (51%) | fixed ✅ |
| "What the human decided" (same panel) | **243,040** | ≈33,048 (13.6%) | **40,796** (94px) | ≈33,201 (81%) | fixed ✅ |

After the fix no flagged card has a majority-empty area. AFTER visual: `_ls93v6_D4_question_AFTER.png` (micro-row collapaps to a single line; recommendation shows "No explicit recommendation" collapsed next to the multi-line human decision).

**`ExecutiveCognitiveAnswer.tsx` (chat view) audit:** it does **not** use `.ci-field` micro-cells (sections use `.ci-sect`/`.ci-command`/`.ci-moment`); probed sections are 117–216px with real content, `ciFields=[]`. The "recommendation" it renders ("WHAT EUREKA PROPOSED · system candidates") shows the real alternatives list, not a reserved empty area.

**"Repeats in 6 chapters" evaluation:** the "No explicit recommendation" text appears **once**, in the StorytellingPanel LAYER-0 summary (`_ls93v6` probe `recCard`). `ContextChapter` shows "System recommendation: NONE" as an inline label:value row (compact, not a reserved card). There is **no identical card duplicated across Question/Context/Discovery/Decision/Action**. The card is a single shared-narrative summary, so "show only in DECISION chapter" is moot — I kept it (it now collapses). This is reported exactly as found, not as a correction of a stated behavior.

---

## DEFECTO 5 — Inaccurate `?nolabels=1` claim

**What the flag does today (exactly):** `?nolabels=1` sets `hideLabels=true`, which is passed **only** to `CognitiveFieldRenderer` → `labelPolicy()` returns false → the **3D node label sprites are hidden**. The HUD (`ci-field-hud`), toolbar (`ci-field-toolbar`), legend (`ci-field-legend`) and accessible block (`ci-field-sr`) are **NOT** hidden and their text remains. Measured (`_ls93v6_D1_nolabels.json`): `hud.visible=true`, `toolbar.visible=true`, `legend.visible=true`, `sr.visible=true` with text; only node labels gone (`_ls93v6_D1_nolabels_field.png`).

**New improvement (not a correction of the old claim):** added `?bare=1` in `src/components/cognitive/CognitiveField.tsx` — a stricter readability mode that hides **HUD + toolbar + legend + sr** *and* the node labels, so geometry is judged with **no text at all**. Measured (`_ls93v6_D1_bare.json`): hud/toolbar/legend/sr all `null` (hidden); captures `_ls93v6_D1_bare*.png`.

**Files touched:** `src/components/cognitive/CognitiveField.tsx`, `src/components/cognitive/cognitiveFieldRenderer.ts`, `src/components/cognitive/cognitiveField.css`, `src/components/cognitive/StorytellingPanel.tsx`; new test `src/components/cognitive/cognitiveField.backend.test.ts`.

---

## Stable backup

Create `_backup_stable_<timestamp>_LS93_v6_REMEDIATED` (front + back) once the report is accepted.
