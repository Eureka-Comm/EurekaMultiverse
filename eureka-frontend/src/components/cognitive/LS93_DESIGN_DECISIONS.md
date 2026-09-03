# LS93 v5 — COGNITIVE VISUAL COMPUTING SURFACE · Design Decision Record

## §1 CRITICAL ORDER OF DECISION (per surface — answered BEFORE any shader)

The surface is ONE cognitive surface whose job is to make the real EUREKA cognitive
operation legible and navigable, not to look like a generic graph.

### (1) What cognitive information must be visible?
On one screen, in 3 seconds: **what is it, where does it start+end, what was the
decision, what actually happened.** Beyond the 3-second read, on demand:
- the **PATH** = authority/decision progression QUESTION → DISCOVERY → EVALUATION →
  DECISION → ACTION → EXECUTION → RESULT (sequential, with origin + terminal markers);
- the **FIELD** = non-sequential context converging INTO path nodes: EVIDENCE → FINDING,
  FINDING → (PREDICTION and PRESCRIPTION in parallel), ALTERNATIVES → DECISION;
- the real **STATE / authority** of each artifact (validated / unsupported /
  not-evaluated / simulated / human / frozen), as a spatial height + tone, never a fake score;
- the real **semantic weight** (evidence count, finding confidence, alternative count,
  decision authority, result terminality) as size;
- the real **relationships** (derived_from / supports / produced_by / selected_by /
  authorized_by / executed_as / frozen_as), subtle, always present.
Nothing invented: NOT_EVALUATED stays ghost; absent ACTION/EXECUTION stays absent.

### (2) What representation communicates it best?
A single dominant **COGNITIVE AXIS** (the PATH) — a left→right spline through the real,
present path stages, carrying the walkthrough QUESTION → … → RESULT. The axis is the
ONE dominant composition. **FIELD** geometry (evidence, prescription+alternatives) is
secondary structure that converges INTO the axis node it feeds, never floating without an
edge. Authority height = real validity/authority; size = real weight; tone = real
status. This is 3D because authority height + depth convergence carry real meaning.

### (3) What tech renders it with quality?
- **WebGL2 via three.js** (guaranteed, hardware — verified as the ACTUAL backend).
- Three.js primitives (Torus/Sphere/Ring/Cylinder/Plane/Box/Tube/Line/Point/Sprite/InstancedMesh).
- DOM/SVG fallback for no-GPU (same pure layout, honest states).
- WebGPU stays an OPT-IN upgrade; never required, reported honestly.

### (4) GPU technique — chosen only AFTER (1)-(3). Justification:
The 3D spatial field + depth cues (authority height, front→back convergence) is what
communicates the cognitive operation best. Standard geometry/transparency/instancing
cheaply render the real glyphs; a bespoke fragment shader adds NO information that the
pure layout + primitives already carry. So geometry (not a shader) is the technique, and
the renderer honestly reports WEBGL2. No GPU technique is implemented for decoration.

### (5) Experience
- Camera starts at **RESULT if it exists, else the highest-authority pending artifact**
  (never a free orbital view).
- FAR/MEDIUM/CLOSE semantic zoom: labels appear by zoom/selection; never all at once.
- Focus = highlight the direct chain + dim the rest to 0.15–0.25 (spatial salience, never
  hiding structure).
- Inspector is an explanation surface on demand; the PATH+FIELD is understood WITHOUT it.
