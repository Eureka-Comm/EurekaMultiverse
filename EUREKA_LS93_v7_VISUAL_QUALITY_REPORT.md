# EUREKA · LS93 v7 — VISUAL QUALITY REMEDIATION REPORT

**Work:** `WORK-9AAFCC50` · **Fixture:** `__shot_completed_state.json` (OUTCOME chapter) · **Frontend:** `D:\DS_ARNES\IA Agentes\eureka-frontend` (:5173) · **Backend:** `D:\DS_ARNES\IA Agentes` (:8000, **not modified**)
**Scope:** ONE remediation loop — Defecto 5-bis (GATE) → Defecto 6 (visual quality). **Stops here.** Only render/material/palette/background/first-render-flag were touched. Layout (PATH axis + converging FIELD), all node **positions**, the 9-form per-class geometry, `CognitiveStoryTab.tsx` and `CognitiveProjectionDTO`/ACFL/GCLV/MathEngine are untouched.

---

## PART A — DEFECTO 5-BIS Verified (first-render flag; no code bug)

**Verdict: PASS.** `?nolabels=1` (and `?bare=1`) is read at render time, propagated at the renderer **construction**, and honored from the **very first painted frame**. It is NOT applied in a follow-up effect after a labelled first paint.

### Code proof of first-render propagation (exact lines)

`src/components/cognitive/CognitiveField.tsx`
- L89–90 — the flag is read in the **component body** (`bareMode`, `hideLabels = …get('nolabels')==='1' || bareMode`), so it has its value at the *first* render. This is not inside a later effect.
- L125–131 — the renderer is created and the layout handed to it **in the same statement block** (`const renderer = new CognitiveFieldRenderer(container, cb, { preferWebgpu, hideLabels })` → `if (layoutRef.current) renderer.setLayout(layoutRef.current)`). `hideLabels` is captured in the constructor options.
- L195/204/223/259 — `bareMode` additionally suppresses the HUD/toolbar/legend/sr in the JSX at the same render.

`src/components/cognitive/cognitiveFieldRenderer.ts`
- L135 — `this.hideLabels = options.hideLabels === true;` set in the **constructor**.
- L840 — `labelPolicy(): if (this.hideLabels) return false;`
- L291 — `setLayout(...)` calls `this.applyFocus(layout)`, and L808 applies the policy (`spr.visible = labelPolicy(e)`) **during the same synchronous call, before the first `requestAnimationFrame` draws the scene**. There is no later effect that re-enables labels.
- L929–932 — deterministic ready signal `data-cog-ready="1"` is set only after the first flag-applied frame actually renders.

**Conclusion:** the label policy runs inside `setLayout`→`applyFocus`, which executes before the first drawn frame, so the first paint already honours the flag. **No fix required.**

### Deterministic wait (not `setTimeout`)
Added `data-cog-ready="1"` to the stage container (set after the first rendered frame with a layout). The capture harness waits on `[data-cog-ready="1"]` instead of an arbitrary timer. Fix/harness files: `_ls93v7_capture.py`.

### RÉAL side-by-side zoom crop — RESULT label beside the highest-authority terminal
Same work, same camera, same region, drawn with the delivered dark renderer:
**`_ls93v7_5bis_final_sidebyside.png`** (top = labels, bottom = `?nolabels=1`).
Labels crop also produced on the pre-render change (`_ls93v7_5bis_sidebyside.png`). In both, the `RESULT` (and `FROZEN`) label is present with labels enabled and **absent** with `?nolabels=1` — confirmed visually; the geometry is identical.

---

## PART B — DEFECTO 6: VISUAL QUALITY UPGRADE (render/material) — PASS

Same work (`WORK-9AAFCC50`), **same camera** (deterministic `data-cog-ready` framing), direct side-by-side:
**`_ls93v7_6_before_after.png`** (top = BEFORE white CAD-grid clip-art, bottom = AFTER dark instrument).

### 6.1 Background & depth
- Canvas now clears to a **deep instrument surface** `#0a0e14` (renderer `setClearColor(SURFACE_BG,1)`) + `scene.background` + a **linear Z-fog** (`Fog(0x0a0e14, 1500, 4600)`) so far field artifacts recede into depth, never vanish. The stage CSS is a matching dark radial surface (only the 3D canvas; the app theme, HUD, legend, chapter chrome are unchanged).
- Reference grid reduced to **opacity 0.012** (was 0.035) and darkened to near-background registration lines so it cannot read as a CAD grid.
- Files: `cognitiveFieldRenderer.ts` (constructor, `configureRenderer`, `buildGrid`, `setupPost`), `cognitiveField.css` (`.ci-field-stage`).

### 6.2 Materials + selective bloom
- All solid node surfaces now use `luminousMat` — a lit `MeshStandardMaterial` with a near-shadow base colour and the **class colour as EMISSIVE** (metalness 0.22, roughness 0.58), lit by a hemisphere + key + rim light. Nodes read computational/luminous, not flat matte. Per-class **geometry unchanged**.
- **Selective, low-intensity post-processing bloom:** `EffectComposer` + `UnrealBloomPass` (strength 0.22, radius 0.62, threshold 0.72) + `OutputPass`. Only QUESTION (`PROBLEM`), HUMAN DECISION (`DECISION`) and RESULT get an emissive boost (`topAuthorityBoost`, 1.7 vs 1.05) so **only they cross the threshold** — not uniform bloom. WebGPU is opt-in only (`?webgpu=1`); on that path the WebGL composer is skipped and the renderer falls back to a direct render.
- Files: `cognitiveFieldRenderer.ts` (`luminousMat`, `entityObject`, `applyFocus`, `setupPost`, render loop, `dispose`, `swapRenderer`).

### 6.3 Relation lines (hierarchy + detangling)
- `buildLinks` now computes a real **importance** per edge: role base (selection `selected_by`/`authorized_by` 0.90 > `produced_by` 0.62 > `supports` 0.48 > other 0.36) **+ fan-in** (`min(1, fanIn/4)*0.28`). Line radius (`0.5 + imp*1.5`) and opacity (`0.10 + imp*0.30`) scale with it — no more uniform gray mesh.
- Edges that travel off the axis (evidence/finding/prescription tributaries) are drawn as **gentle arcs** (`linkPath`, stable perpendicular bow) so the crossing reads as a swept bundle, not a tangle. **Node positions are NOT moved** — only the line geometry bows.
- Files: `cognitiveFieldRenderer.ts` (`buildLinks`, `linkPath`, `stableSign`).

### 6.4 Palette
- `NODE_KIND_COLOR` lowered to a coherent muted "scientific instrument" set (steel-blue, desaturated violet/green/amber) **keeping the same class→colour-family mapping** (blue=QUESTION, violet=EVIDENCE, green=FINDING/RESULT, teal=PREDICTION/ACTION/EXECUTION, amber=DECISION/FROZEN, etc.). These also serve as the 3D emissive tones and the legend glyphs.
- Files: `cognitiveColors.ts` (`NODE_KIND_COLOR`).

---

## Validation (all green)
- `npx tsc --noEmit -p tsconfig.app.json` → **0 errors**.
- `npx vitest run` → **56/56 passing** (8 files).
- `npm run build` → **OK** (vite 8.2.1).
- Real browser (Playwright/Chromium WebGL2 via `/__shot`) → `console_errors: []` and `ready: 1` on **every** capture (labels, `?nolabels=1`, BEFORE, AFTER, final).

## Evidence files (in `D:\DS_ARNES\IA Agentes`)
- `_ls93v7_5bis_final_sidebyside.png` — Part A zoom crop (labels vs `?nolabels=1`), delivered dark renderer.
- `_ls93v7_5bis_sidebyside.png` — Part A zoom crop on the verified state.
- `_ls93v7_6_before_after.png` — Part B BEFORE/AFTER full field, same work + same camera.
- `_ls93v7_final_completed_field.png` / `_ls93v7_final_nolabels_field.png` — final captures.
- `_ls93v7_after_center_crop.png` (detangled arcs), `_ls93v7_after_decision_crop.png`, `_ls93v7_after_result_region.png` — quality crops.
- Helper scripts: `_ls93v7_capture.py`, `_ls93v7_5bis_sidebyside.py`, `_ls93v7_5bis_final.py`, `_ls93v7_before_after.py`.

## Backup
`_backup_stable_2026-09-01_192707_LS93_v7_VISUAL_QUALITY` (front + back; prior backups retained; backend unchanged by this loop).

## Honest notes
- The DECISION authority node retains its validated double-ring geometry (unmistakable authority glyph); on the dark surface it now reads luminous, not clip-art. Its bloom was tuned down (2.35→1.7, strength 0.32→0.22, threshold 0.62→0.72) because the first pass blew it out to a yellow "sun".
- The centre relation density is **real** graph complexity (many evidence/finding/prediction→path edges); it is now presented as curved, thickness-weighted tributary arcs rather than hidden or fabricated.
