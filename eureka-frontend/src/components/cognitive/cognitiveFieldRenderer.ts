import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import type {
  CognitiveFieldLayout,
  FieldEntity,
  FieldGap,
} from '../../domain/cognitiveFieldLayout';
import { kindColor } from './cognitiveColors';

/**
 * LS91 → LS93 v5 — COGNITIVE FIELD RENDERER (imperative, GPU-backed, lifecycle-owned).
 *
 * This class is the ONLY owner of the WebGL render loop and scene graph. React owns
 * state / controls / inspector / lifecycle; the renderer owns the continuous
 * rendering, the semantic camera, the raycast interaction, the field layers
 * (L1 structure / L2 artifact / L3 edge / L4 label) and the spatial focus. It never
 * mutates the canonical state — it only draws the pure layout it is handed.
 *
 * Backend policy (architecture supports WebGPU -> WebGL2 -> non-GPU):
 *   · Default = three's WebGLRenderer, which creates a hardware WebGL2 context on all
 *     modern browsers. This is the guaranteed path and is reported honestly.
 *   · WebGPU is an OPT-IN upgrade (`preferWebgpu`) that is properly awaited & gated.
 *   · If no GPU context can be created at all, React mounts the DOM/SVG fallback.
 *
 * Visual-grammar rule (§5): no two cognitive classes are confusable by shape+size:
 *   QUESTION=ring · EVIDENCE=small sphere · FINDING=concentrated sphere+halo ·
 *   PREDICTION=plane (GHOST wireframe if NOT_EVALUATED) · PRESCRIPTION=branch fan ·
 *   ALTERNATIVE=candidate · DECISION=double-ring authority (largest here) ·
 *   ACTION=discrete segments · EXECUTION=state segment · RESULT=terminal plate (largest) ·
 *   FROZEN=sealed octahedron.
 */

export type RendererBackend = 'WEBGPU' | 'WEBGL2' | 'WEBGL1' | 'NONE';

export interface CognitiveFieldRendererCallbacks {
  onEntitySelect?: (id: string) => void;
  onEntityHover?: (id: string | null) => void;
  /** Fired with the DEFINITIVE backend once it is known (for honest reporting). */
  onBackend?: (backend: RendererBackend) => void;
}

const FOCUS_SALIENCE = {
  FULL: 1.0,
  DIRECT: 0.85,
  MEDIUM: 0.55,
  ATTENUATED: 0.15,
};

/** Layer base intensity (L1 structure bright, L2 artifact medium, never equal). */
const LAYER_BASE = { 1: 1.0, 2: 0.8 };

// ---- LS93 v7 instrument surface (render/material only; positions untouched) ----
/** Deep instrument-surface background for the 3D canvas (NOT a theme change). */
const SURFACE_BG = new THREE.Color(0x0a0e14);
/** Fog colour = background so distant field artifacts recede into depth, never vanish. */
const FOG_COLOR = new THREE.Color(0x0a0e14);
/** Faint registration grid, further reduced so it can never compete with the data. */
const GRID_COLOR_A = 0x16202b;
const GRID_COLOR_B = 0x101821;
/** Authority boost so only QUESTION / DECISION / RESULT cross the bloom threshold. */
function topAuthorityBoost(kind: string): number {
  return kind === 'PROBLEM' || kind === 'DECISION' || kind === 'RESULT' ? 1 : 0;
}

/** Parse a hex color string ('#rrggbb') to a number, for three.js materials. */
function colNum(hex: string): number {
  const n = parseInt(hex.replace('#', ''), 16);
  return Number.isFinite(n) ? n : 0x9aa2ab;
}

/** True when a WebGL context is a genuine WebGL2 context (not WebGL1). */
function isWebGL2Context(ctx: unknown): boolean {
  return typeof WebGL2RenderingContext !== 'undefined' && ctx instanceof WebGL2RenderingContext;
}

/** Emphasise a colour by a salience amount and desaturate it when attenuated. */
function toneColor(hex: string, salience: number): string {
  const c = new THREE.Color(hex);
  const s = salience;
  const mix = new THREE.Color(0xffffff); // near-white, for the "receding" blend
  c.lerp(mix, 1 - s);
  return c.getStyle();
}

export class CognitiveFieldRenderer {
  private container: HTMLElement;
  private scene: THREE.Scene;
  /** LS93 v7 fix: label sprites live in a separate scene rendered on top WITHOUT bloom. */
  private labelScene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private renderer: THREE.WebGLRenderer;
  private controls: OrbitControls;
  private raycaster = new THREE.Raycaster();
  private pointer = new THREE.Vector2();
  private clock = new THREE.Clock();
  private raf = 0;
  private needsRender = true;
  private animating = false;
  private disposed = false;
  private resizeObserver?: ResizeObserver;
  private entities: FieldEntity[] = [];
  private layout: CognitiveFieldLayout | null = null;
  private pickables: THREE.Object3D[] = [];
  private entityPicks = new Map<THREE.Object3D, string>();
  private hoverId: string | null = null;
  private focusTarget = new THREE.Vector3();
  private focusId: string | null = null;
  private provenanceVisible = false;
  private labelsByEntity = new Map<string, THREE.Sprite>();
  private stageSprites: THREE.Sprite[] = [];
  private callbacks: CognitiveFieldRendererCallbacks;
  private themeRoot: HTMLElement;
  private options: { preferWebgpu?: boolean; hideLabels?: boolean };
  private hideLabels = false;
  private backendReady = true;
  backend: RendererBackend = 'WEBGL2';
  private webgpuUsed = false;
  private hasFramed = false;
  private semanticZoom = 0;
  private zoomCur = 0;
  private neighbours = new Map<string, { direct: Set<string>; second: Set<string> }>();
  private focusRing: THREE.Mesh | null = null;
  /** Deterministic "first flag-applied frame drawn" signal for the capture harness. */
  private readySignalled = false;
  /** LS93 v7: selective post-processing bloom (RenderPass + UnrealBloomPass). */
  private composer: EffectComposer | null = null;
  private bloomPass: UnrealBloomPass | null = null;

  constructor(container: HTMLElement, callbacks: CognitiveFieldRendererCallbacks, options: { preferWebgpu?: boolean; hideLabels?: boolean } = {}) {
    this.container = container;
    this.callbacks = callbacks;
    this.options = options;
    this.hideLabels = options.hideLabels === true;
    this.scene = new THREE.Scene();
    this.labelScene = new THREE.Scene();
    // LS93 v7 — deep instrument surface (render/material only). Scene + fog share
    // the background colour so distant field artifacts recede into depth, never
    // vanish into a hard edge.
    this.scene.background = SURFACE_BG.clone();
    this.scene.fog = new THREE.Fog(FOG_COLOR.clone(), 1500, 4600);
    this.camera = new THREE.PerspectiveCamera(48, 1, 0.1, 9000);

    this.renderer = this.createDefaultRenderer();
    // Honest backend: report the context version the renderer ACTUALLY created
    // (WebGL2 on every modern three/r185 browser, WebGL1 otherwise). Never claim
    // 'WEBGL2' when the context is WebGL1.
    this.backend = isWebGL2Context(this.renderer.getContext()) ? 'WEBGL2' : 'WEBGL1';
    this.backendReady = true;
    this.configureRenderer(this.renderer);
    this.setupPost();
    this.camera.aspect = Math.max(0.2, (container.clientWidth || 1) / (container.clientHeight || 1));
    this.camera.updateProjectionMatrix();
    container.appendChild(this.renderer.domElement);
    this.callbacks.onBackend?.(this.backend);

    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.07;
    this.controls.enablePan = true;
    this.controls.maxPolarAngle = Math.PI * 0.5;
    this.controls.minPolarAngle = Math.PI * 0.08;
    this.controls.minDistance = 12;
    this.controls.maxDistance = 4200;
    this.controls.addEventListener('change', () => { this.needsRender = true; });

    this.themeRoot = container.ownerDocument.documentElement;
    this.bindEvents();
    this.resizeObserver = new ResizeObserver(() => this.onResize());
    this.resizeObserver.observe(container);
    this.themeRoot.classList.add('ci-field-gpu');
    if (this.options.preferWebgpu) void this.upgradeToWebGpu();
    this.loop();
  }

  private createDefaultRenderer(): THREE.WebGLRenderer {
    return new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
  }

  private configureRenderer(renderer: THREE.WebGLRenderer) {
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(this.container.clientWidth, this.container.clientHeight);
    renderer.setClearColor(SURFACE_BG, 1);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    const cvs = renderer.domElement;
    cvs.style.width = '100%';
    cvs.style.height = '100%';
    cvs.style.display = 'block';
    cvs.style.position = 'absolute';
    cvs.style.inset = '0';
    cvs.style.background = `#${SURFACE_BG.getHexString()}`;
  }

  /**
   * LS93 v7 — selective, low-intensity post-processing bloom. UnrealBloomPass
   * blooms only the pixels above `threshold`; the top-authority nodes
   * (QUESTION / DECISION / RESULT) carry a boosted emissive so THEY cross it while
   * the rest of the field (grid, axis, lines, ordinary nodes) stays below it.
   * This is WebGL2-only: on the opt-in WebGPU path bloom is skipped (it is a
   * WebGL EffectComposer), and the renderer falls back to a direct render.
   */
  private setupPost() {
    if (this.webgpuUsed || !(this.renderer as THREE.WebGLRenderer).getContext) return;
    try {
      this.composer = new EffectComposer(this.renderer);
      this.composer.addPass(new RenderPass(this.scene, this.camera));
      this.bloomPass = new UnrealBloomPass(
        new THREE.Vector2(this.container.clientWidth || 1, this.container.clientHeight || 1),
        0.22,   // strength — low, so it reads as glow, not a blur
        0.62,   // radius
        0.72,   // threshold — only the brightest emissive authority nodes bloom
      );
      this.composer.addPass(this.bloomPass);
      this.composer.addPass(new OutputPass());
    } catch {
      this.composer = null;
      this.bloomPass = null;
    }
  }

  private async upgradeToWebGpu() {
    const gpu = (navigator as any).gpu;
    if (!gpu || typeof gpu.requestAdapter !== 'function') return;
    try {
      const adapter = await gpu.requestAdapter();
      if (this.disposed || !adapter) return;
      const mod = await import('three/webgpu');
      if (this.disposed) return;
      const canvas = this.container.ownerDocument.createElement('canvas');
      const wg = new mod.WebGPURenderer({ canvas, antialias: true });
      this.backendReady = false;
      await wg.init();
      if (this.disposed) return;
      this.swapRenderer(wg as unknown as THREE.WebGLRenderer, true);
      this.backendReady = true;
      this.needsRender = true;
      this.callbacks.onBackend?.('WEBGPU');
    } catch {
      this.webgpuUsed = false;
      this.backend = 'WEBGL2';
      this.backendReady = true;
      this.callbacks.onBackend?.('WEBGL2');
    }
  }

  private swapRenderer(renderer: THREE.WebGLRenderer, webgpu: boolean) {
    const oldCanvas = this.renderer.domElement;
    this.controls.dispose();
    oldCanvas.remove();
    this.renderer = renderer;
    this.webgpuUsed = webgpu;
    this.backend = webgpu ? 'WEBGPU' : 'WEBGL2';
    const canvas = this.renderer.domElement;
    canvas.style.width = '100%';
    canvas.style.height = '100%';
    canvas.style.display = 'block';
    this.container.appendChild(canvas);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
    this.renderer.setClearColor(SURFACE_BG, 1);
    // WebGPU path: the WebGL EffectComposer does not apply, so bloom is disabled.
    if (webgpu) {
      this.composer = null;
      this.bloomPass = null;
    } else {
      this.setupPost();
    }
    this.controls = new OrbitControls(this.camera, canvas);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.07;
    this.controls.enablePan = true;
    this.controls.maxPolarAngle = Math.PI * 0.5;
    this.controls.minPolarAngle = Math.PI * 0.08;
    this.controls.minDistance = 12;
    this.controls.maxDistance = 4200;
    this.controls.addEventListener('change', () => { this.needsRender = true; });
    this.needsRender = true;
  }

  // ---------- public API ----------

  setLayout(layout: CognitiveFieldLayout) {
    this.layout = layout;
    this.entities = layout.entities;
    this.rebuildScene(layout);
    // The default focus is the semantic-camera start (RESULT if it exists, else the
    // highest-authority pending artifact) — never a free orbital view.
    this.focusId = layout.focusedId ?? layout.cameraStartId ?? null;
    this.needsRender = true;
    this.present(0);
    this.applyFocus(layout);
  }

  /** Keep the current salience focus but re-frame the whole axis (start+end visible). */
  present(duration = 520) {
    if (!this.layout) return;
    this.animateTo(this.frameAxis(), duration);
  }

  setFocused(id: string | null) {
    this.focusId = id;
    if (this.layout) {
      this.applyFocus(this.layout);
      this.positionFocusRing();
    }
  }

  /** Animate the semantic camera toward one entity (mid/near semantic zoom). */
  focusEntity(id: string | null, duration = 620) {
    if (!id || !this.layout) { this.present(duration); return; }
    const e = this.entities.find((x) => x.id === id);
    if (!e) return;
    const pos = new THREE.Vector3(e.position.x, e.position.y, e.position.z);
    const dir = new THREE.Vector3().subVectors(this.camera.position, pos).normalize();
    // Keep adjacency visible: frame ~8 node-radii around the entity, not a tight close-up.
    const targetPos = pos.clone().add(dir.multiplyScalar(Math.max(120, e.radius * 9)));
    this.animateTo({ position: targetPos, target: pos }, duration);
  }

  setProvenanceVisible(v: boolean) {
    this.provenanceVisible = v;
    this.needsRender = true;
    if (this.layout) this.applyFocus(this.layout);
  }

  fit(duration = 520) { this.present(duration); }

  highlight(id: string | null) {
    this.hoverId = id;
    this.needsRender = true;
    this.callbacks.onEntityHover?.(id);
  }

  dispose() {
    this.disposed = true;
    this.resizeObserver?.disconnect();
    if (this.raf) cancelAnimationFrame(this.raf);
    this.controls?.dispose();
    this.scene.traverse((o) => {
      const mesh = o as THREE.Mesh;
      if (mesh.geometry) mesh.geometry.dispose();
      const mat = mesh.material as THREE.Material | THREE.Material[] | undefined;
      if (Array.isArray(mat)) mat.forEach((m) => m.dispose());
      else if (mat) mat.dispose();
    });
    this.renderer?.dispose();
    this.composer?.dispose();
    this.composer = null;
    this.renderer.domElement.remove();
    this.themeRoot.classList.remove('ci-field-gpu');
  }

  // ---------- scene ----------

  private rebuildScene(layout: CognitiveFieldLayout) {
    while (this.scene.children.length) {
      const child = this.scene.children[0];
      this.scene.remove(child);
      child.traverse((o) => {
        const mesh = o as THREE.Mesh;
        if (mesh.geometry) mesh.geometry.dispose();
      });
    }
    // LS93 v7 fix — also drop the label sprites from the separate label scene.
    while (this.labelScene.children.length) this.labelScene.remove(this.labelScene.children[0]);
    this.pickables = [];
    this.entityPicks.clear();
    this.labelsByEntity.clear();
    this.stageSprites = [];

    // LS93 v7 — instrument lighting: a soft ambient/hemisphere fill + a key + rim
    // so the luminous (emissive) node surfaces read dimensional, not flat-clip-art.
    const hemi = new THREE.HemisphereLight(0x223044, 0x05070b, 0.5);
    this.scene.add(hemi);
    const key = new THREE.DirectionalLight(0x9fb4cf, 0.55);
    key.position.set(320, 520, 260);
    this.scene.add(key);
    const fill = new THREE.DirectionalLight(0x2b3a4d, 0.35);
    fill.position.set(-260, -120, -340);
    this.scene.add(fill);

    // Focus highlight ring (marks the semantic-focus outcome without dimming the rest).
    this.focusRing = new THREE.Mesh(
      new THREE.TorusGeometry(1, 0.9, 8, 48),
      new THREE.MeshBasicMaterial({ color: 0x8250df, transparent: true, opacity: 0.7, depthWrite: false }),
    );
    this.focusRing.rotation.x = Math.PI / 2;
    this.focusRing.visible = false;
    this.focusRing.userData.isFocusRing = true;
    this.scene.add(this.focusRing);

    this.buildGrid(layout);
    this.buildAxis(layout);
    this.buildGapMarkers(layout);
    this.buildLinks(layout);
    this.buildEntities(layout);
    this.computeNeighbours(layout);
  }

  private computeNeighbours(layout: CognitiveFieldLayout) {
    this.neighbours.clear();
    const byId = new Set(this.entities.map((e) => e.id));
    const direct = new Map<string, Set<string>>();
    const second = new Map<string, Set<string>>();
    this.entities.forEach((e) => {
      const d = new Set<string>();
      const s = new Set<string>();
      layout.links.forEach((l) => {
        if (l.source === e.id && byId.has(l.target)) { d.add(l.target); }
        if (l.target === e.id && byId.has(l.source)) { d.add(l.source); }
      });
      direct.set(e.id, d);
      d.forEach((nid) => {
        layout.links.forEach((l) => {
          if (l.source === nid && byId.has(l.target) && l.target !== e.id) s.add(l.target);
          if (l.target === nid && byId.has(l.source) && l.source !== e.id) s.add(l.source);
        });
      });
      second.set(e.id, s);
    });
    this.entities.forEach((e) => this.neighbours.set(e.id, { direct: direct.get(e.id) ?? new Set(), second: second.get(e.id) ?? new Set() }));
  }

  /** Faint spatial grid — opacity ~0.012 on a dark surface so it is a registration
   *  aid only; it can never read as a CAD grid competing with the data (6.1). */
  private buildGrid(layout: CognitiveFieldLayout) {
    const { minX, maxX, minZ, maxZ } = this.axisBounds();
    const w = (maxX - minX) + 260;
    const h = (maxZ - minZ) + 180;
    const grid = new THREE.GridHelper(Math.max(w, h), 24, GRID_COLOR_A, GRID_COLOR_B);
    grid.position.set((minX + maxX) / 2, -12, (minZ + maxZ) / 2);
    (grid.material as THREE.Material).transparent = true;
    (grid.material as THREE.Material).opacity = 0.012;
    this.scene.add(grid);
  }

  /** The DOMINANT cognitive axis (the PATH) — raised, continuous, start→end. It is
   *  the spine of the instrument: a faint luminous teal rather than a flat gray. */
  private buildAxis(layout: CognitiveFieldLayout) {
    if (layout.thread.length < 2) return;
    const pts = layout.thread.map((p) => new THREE.Vector3(p.x, 0, p.z));
    const curve = new THREE.CatmullRomCurve3(pts);
    const tube = new THREE.Mesh(
      new THREE.TubeGeometry(curve, 260, 2.0, 8, false),
      new THREE.MeshBasicMaterial({ color: 0x2a6e73, transparent: true, opacity: 0.34, depthWrite: false }),
    );
    tube.userData.isAxis = true;
    this.scene.add(tube);
  }

  /** Collapsed empty stages: a subtle notch on the axis, never a fake node. */
  private buildGapMarkers(layout: CognitiveFieldLayout) {
    layout.gaps.forEach((g: FieldGap) => {
      const dot = new THREE.Mesh(
        new THREE.SphereGeometry(0.6, 10, 10),
        new THREE.MeshBasicMaterial({ color: 0x2d3a46, transparent: true, opacity: 0.5 }),
      );
      dot.position.set(g.anchor.x, 0, g.anchor.z);
      dot.userData.isGap = true;
      dot.userData.gapNote = g.note;
      this.scene.add(dot);
    });
  }

  /** Deterministic +1/-1 sign for a stable per-link bow direction. */
  private stableSign(id: string): number {
    let h = 2166136261;
    for (let i = 0; i < id.length; i++) { h ^= id.charCodeAt(i); h = Math.imul(h, 16777619); }
    return (h >>> 31) === 1 ? 1 : -1;
  }

  /**
   * LS93 v7 — relation lines with REAL importance (6.3). Every link's radius and
   * opacity scale with how much it aggregates (fan-in) + its semantic role, so the
   * hierarchy is legible in the line weight, never a uniform gray mesh. Links that
   * travel off the cognitive axis (evidence/finding/prescription tributaries) are
   * drawn as gentle arcs so the crossing reads as a swept bundle rather than a tangle
   * — semantic NODE positions are untouched (only the line geometry bows).
   */
  private buildLinks(layout: CognitiveFieldLayout) {
    const byId = new Map<string, FieldEntity>();
    this.entities.forEach((e) => byId.set(e.id, e));
    const toV = (id: string) => {
      const e = byId.get(id);
      return e ? new THREE.Vector3(e.position.x, e.position.y, e.position.z) : null;
    };
    // Fan-in: how many real edges converge into each node (the aggregate weight).
    const fanIn = new Map<string, number>();
    layout.links.forEach((l) => fanIn.set(l.target, (fanIn.get(l.target) ?? 0) + 1));

    layout.links.forEach((l) => {
      const a = toV(l.source);
      const b = toV(l.target);
      if (!a || !b) return;
      const from = byId.get(l.source);
      const to = byId.get(l.target);
      const fanned = fanIn.get(l.target) ?? 1;
      const isSelection = l.kind === 'selection';
      // base by semantic role; selection (into the DECISION) is always the strongest.
      let imp = isSelection ? 0.9 : l.label === 'produced_by' ? 0.62 : l.label === 'supports' ? 0.48 : 0.36;
      // aggregate importance: the more artifacts feed a node, the thicker the line.
      imp = Math.min(1, imp + Math.min(1, fanned / 4) * 0.28);
      const color = isSelection ? 0x7d64c9 : 0x50606d;
      const opacity = 0.10 + imp * 0.30;
      const radius = 0.5 + imp * 1.5;
      const pts = this.linkPath(a, b, l.id);
      const curve = new THREE.CatmullRomCurve3(pts);
      const line = new THREE.Mesh(
        new THREE.TubeGeometry(curve, 28, radius, 6, false),
        new THREE.MeshBasicMaterial({ color, transparent: true, opacity, depthWrite: false }),
      );
      line.userData.linkId = l.id;
      line.userData.semantic = l.label;
      line.userData.isLink = true;
      this.scene.add(line);
      // provenance label (L4, on demand only, never all at once)
      if (isSelection || this.provenanceVisible) {
        const spr = this.makeLabel(l.label, color, 0.72);
        spr.position.copy(a.clone().lerp(b, 0.5));
        spr.position.y += 2;
        spr.scale.setScalar(0.7);
        spr.userData.isLinkLabel = true;
        spr.visible = false;
        this.labelScene.add(spr);        this.stageSprites.push(spr);
      }
      void from;
      void to;
    });
  }

  /** Straight or gently-arced path between two node positions (never moves nodes). */
  private linkPath(a: THREE.Vector3, b: THREE.Vector3, id: string): THREE.Vector3[] {
    const dir = new THREE.Vector3().subVectors(b, a);
    const len = dir.length();
    if (len < 2) return [a.clone(), b.clone()];
    // Arcs are the detangler: bow the midpoint along a stable perpendicular so
    // adjacent tributaries separate into a clean swept bundle instead of a mesh.
    const n = dir.clone().normalize();
    const perp = new THREE.Vector3(-n.z, 0, n.x);
    if (perp.lengthSq() < 1e-6) perp.set(1, 0, 0);
    const bow = this.stableSign(id) * Math.min(30, len * 0.14);
    const mid = a.clone().lerp(b, 0.5).add(perp.multiplyScalar(bow));
    mid.y += Math.min(8, 3 + len * 0.02);
    return [a.clone(), mid, b.clone()];
  }

  private buildEntities(layout: CognitiveFieldLayout) {
    this.entities.forEach((e) => {
      const group = this.entityObject(e);
      group.position.set(e.position.x, e.position.y, e.position.z);
      this.scene.add(group);
      group.traverse((o) => {
        const m = o as THREE.Mesh;
        if ((m as any).isMesh || (m as any).isPoints || (m as any).isLine || (m as any).isSprite) {
          m.userData.semanticEntityId = e.id;
          if (!(m as any).isSprite) { this.pickables.push(o as any); this.entityPicks.set(o, e.id); }
        }
      });
      const spr = this.makeLabel(this.labelFor(e), colNum(kindColor(e.kind)), 0.95);
      spr.position.set(e.position.x, e.position.y + e.radius + 4.5, e.position.z);
      // World-space label proportional to the node, so structure labels read clearly
      // at FAR zoom yet stay compact; never overlapping because the label POLICY
      // only shows a handful at a time.
      const lw = THREE.MathUtils.clamp(e.radius * 3.0, 26, 126);
      spr.scale.set(lw, lw * 0.22, 1);
      this.labelsByEntity.set(e.id, spr);
      this.labelScene.add(spr);
    });
  }

  private labelFor(e: FieldEntity): string {
    if (e.kind === 'DECISION') return 'DECISION';
    if (e.kind === 'RESULT') return 'RESULT';
    if (e.kind === 'FROZEN') return 'FROZEN';
    if (e.kind === 'PROBLEM') return 'QUESTION';
    return e.id;
  }

  private labelScale(e: FieldEntity): number {
    const base = Math.min(1.3, Math.max(0.5, e.radius / 6));
    // Field artifacts get the smallest scale so labels never collide; structure is larger.
    return e.layer === 1 ? base : base * 0.78;
  }

  /**
   * LS93 v7 — luminous instrument material (6.2). A lit MeshStandardMaterial whose
   * surface is a near-shadow version of the class colour with the class colour as
   * EMISSIVE, so a node reads "computational / luminous" against the dark surface
   * rather than a flat clip-art swatch. `emissiveIntensity` is raised on the
   * top-authority classes (QUESTION / DECISION / RESULT) so only those cross the
   * selective bloom threshold. Geometry (the validated per-class grammar) is unchanged.
   */
  private luminousMat(col: number, opts: { opacity?: number; depthWrite?: boolean; wireframe?: boolean; side?: THREE.Side; emissiveIntensity?: number } = {}): THREE.MeshStandardMaterial {
    const base = new THREE.Color(col);
    const dark = base.clone().multiplyScalar(0.10).lerp(SURFACE_BG, 0.45);
    return new THREE.MeshStandardMaterial({
      color: dark,
      emissive: base,
      emissiveIntensity: opts.emissiveIntensity ?? 0.9,
      metalness: 0.22,
      roughness: 0.58,
      transparent: (opts.opacity ?? 1) < 1,
      opacity: opts.opacity ?? 1,
      depthWrite: opts.depthWrite ?? false,
      wireframe: opts.wireframe ?? false,
      side: opts.side ?? THREE.FrontSide,
    });
  }

  /** Build the geometry + material for a single entity (the visual grammar). */
  private entityObject(e: FieldEntity): THREE.Object3D {
    const g = new THREE.Group();
    const col = colNum(kindColor(e.kind));
    // Top-authority classes glow (bloom) selectively; the rest stay below threshold.
    const authority = topAuthorityBoost(e.kind);
    const base = (opacity = 1, depthWrite = false, extra = 1) =>
      this.luminousMat(col, { opacity, depthWrite, side: THREE.FrontSide, emissiveIntensity: (authority ? 1.7 : 1.05) * extra });

    switch (e.geometry) {
      case 'question': {
        // QUESTION — origin ring, larger than evidence, flat on the axis plane.
        const ring = new THREE.Mesh(new THREE.TorusGeometry(e.radius, 0.55, 10, 48), base(1));
        ring.rotation.x = Math.PI / 2;
        g.add(ring);
        const dot = new THREE.Mesh(new THREE.SphereGeometry(e.radius * 0.45, 18, 18), base(1));
        g.add(dot);
        break;
      }
      case 'evidence': {
        // EVIDENCE — small sphere/cluster (∝ real weight; never invented particles).
        const dot = new THREE.Mesh(new THREE.SphereGeometry(e.radius, 14, 14), base(0.9));
        g.add(dot);
        break;
      }
      case 'finding': {
        // FINDING — concentrated sphere + translucent convergence halo (shows the
        // evidence converging in, without opening the inspector).
        const dot = new THREE.Mesh(new THREE.SphereGeometry(e.radius, 22, 22), base(1));
        g.add(dot);
        const halo = new THREE.Mesh(
          new THREE.SphereGeometry(e.radius * 1.55, 18, 18),
          new THREE.MeshBasicMaterial({ color: col, transparent: true, opacity: 0.12, depthWrite: false, wireframe: true }),
        );
        halo.userData.isHalo = true;
        g.add(halo);
        break;
      }
      case 'prediction': {
        // PREDICTION — an honest mathematical field plane. NOT_EVALUATED => GHOST
        // wireframe + label, never a surface that looks like real data.
        const ghost = e.numericValue == null || !Number.isFinite(e.numericValue);
        const plane = new THREE.Mesh(
          new THREE.PlaneGeometry(e.radius * 5.2, e.radius * 3.8),
          ghost
            ? new THREE.MeshBasicMaterial({ color: col, transparent: true, opacity: 0.18, depthWrite: false, wireframe: true, side: THREE.DoubleSide })
            : this.luminousMat(col, { opacity: 0.5, depthWrite: false, side: THREE.DoubleSide }),
        );
        plane.rotation.x = -Math.PI / 2;
        plane.position.y -= 0.4;
        plane.userData.isGhost = ghost;
        g.add(plane);
        if (!ghost && e.numericValue != null) {
          const line = new THREE.Mesh(new THREE.BoxGeometry(e.radius * 7, 0.4, 0.5), new THREE.MeshBasicMaterial({ color: 0x2a6e73 }));
          line.position.y = THREE.MathUtils.clamp(e.numericValue * 14, -4, 4);
          g.add(line);
        }
        break;
      }
      case 'prescription': {
        // PRESCRIPTION — branch fan: a hub (the common point) that every real
        // ALTERNATIVE radiates from. The actual fan is drawn by the L3 `produced_by`
        // edges (alternative -> hub); the hub glyph just identifies the common point.
        const hub = new THREE.Mesh(new THREE.SphereGeometry(e.radius * 0.5, 16, 16), base(0.9));
        g.add(hub);
        const collar = new THREE.Mesh(new THREE.TorusGeometry(e.radius * 0.62, 0.4, 8, 28), base(0.85));
        collar.rotation.x = Math.PI / 2;
        g.add(collar);
        break;
      }
      case 'alternative': {
        // ALTERNATIVE — candidate point. The HUMAN-SELECTED alternative carries a
        // distinct violet ring + solid core; the RECOMMENDED one a diamond ring; a
        // plain candidate a thin ring. The double-ring authority node (DECISION) is
        // therefore never confusable with either.
        const dot = new THREE.Mesh(new THREE.SphereGeometry(e.radius, 18, 18), base(0.9));
        g.add(dot);
        if (e.humanSelected) {
          const ring = new THREE.Mesh(new THREE.RingGeometry(e.radius * 1.35, e.radius * 1.55, 44), base(1));
          ring.rotation.x = -Math.PI / 2;
          g.add(ring);
          const core = new THREE.Mesh(new THREE.TorusGeometry(e.radius * 0.6, 0.5, 8, 32), base(1));
          g.add(core);
        } else if (e.recommended) {
          const dia = new THREE.Mesh(new THREE.RingGeometry(e.radius * 1.4, e.radius * 1.56, 4), base(1));
          dia.rotation.x = -Math.PI / 2;
          g.add(dia);
        } else {
          const ring = new THREE.Mesh(new THREE.RingGeometry(e.radius * 1.25, e.radius * 1.36, 28), base(0.55));
          ring.rotation.x = -Math.PI / 2;
          g.add(ring);
        }
        break;
      }
      case 'decision': {
        // DECISION — human-authorized double-ring authority node, larger than any
        // prescription/alternative, elevated highest. Unmistakable.
        const dot = new THREE.Mesh(new THREE.SphereGeometry(e.radius + 0.8, 28, 28), base(1));
        g.add(dot);
        const r1 = new THREE.Mesh(new THREE.RingGeometry(e.radius * 1.35, e.radius * 1.52, 48), base(1));
        r1.rotation.x = -Math.PI / 2;
        r1.position.y = -e.radius * 0.3;
        g.add(r1);
        const r2 = new THREE.Mesh(new THREE.RingGeometry(e.radius * 1.85, e.radius * 1.96, 48), base(0.92));
        r2.rotation.x = -Math.PI / 2;
        r2.position.y = -e.radius * 0.3;
        g.add(r2);
        break;
      }
      case 'action': {
        // ACTION — discrete segments, count = real step count (never hardcoded).
        const steps = Math.max(1, (e as any).stepCount ?? 0);
        const total = steps;
        const gap = e.radius * 2.6;
        for (let i = 0; i < total; i++) {
          const seg = new THREE.Mesh(new THREE.CylinderGeometry(e.radius * 0.45, e.radius * 0.45, e.radius * 1.7, 10), base(0.95));
          seg.rotation.z = Math.PI / 2;
          seg.position.x = (i - (total - 1) / 2) * gap;
          g.add(seg);
        }
        break;
      }
      case 'execution': {
        // EXECUTION — a state segment; SIMULATED is unmistakable (ghost wireframe).
        const sim = /SIMULATED/i.test(e.status) || e.authority === 'SIMULATED';
        const mat = sim
          ? new THREE.MeshBasicMaterial({ color: col, transparent: true, opacity: 0.5, wireframe: true, depthWrite: false })
          : base(0.95, true);
        const seg = new THREE.Mesh(new THREE.CapsuleGeometry(e.radius * 0.7, e.radius * 2.6, 6, 12), mat);
        seg.rotation.z = Math.PI / 2;
        g.add(seg);
        break;
      }
      case 'result': {
        // RESULT — terminal node, the largest, end of path. Stabilized hexagonal seal.
        const hex = new THREE.Mesh(new THREE.CylinderGeometry(e.radius, e.radius, 1.4, 6), base(1));
        hex.rotation.x = Math.PI / 2;
        g.add(hex);
        const ring = new THREE.Mesh(new THREE.TorusGeometry(e.radius * 1.32, 0.32, 8, 40), base(0.95));
        ring.rotation.x = Math.PI / 2;
        g.add(ring);
        break;
      }
      case 'frozen': {
        // FROZEN — sealed octahedron (stabilized terminal state).
        const oct = new THREE.Mesh(new THREE.OctahedronGeometry(e.radius * 1.3), base(0.95));
        g.add(oct);
        const cage = new THREE.Mesh(new THREE.TorusGeometry(e.radius * 1.6, 0.16, 6, 24), base(0.7));
        cage.rotation.x = Math.PI / 2;
        g.add(cage);
        break;
      }
      default: {
        g.add(new THREE.Mesh(new THREE.SphereGeometry(e.radius, 14, 14), base(0.9)));
      }
    }
    return g;
  }

  /** Apply layer base intensity + focus salience + label policy. */
  private applyFocus(layout: CognitiveFieldLayout) {
    this.scene.traverse((o) => {
      if (o.userData.isAxis) return;
      if (o.userData.isLink) return;
      if (!o.userData.semanticEntityId || (o as any).isSprite) return; // labels handled separately
      const id = o.userData.semanticEntityId as string;
      const e = this.entities.find((x) => x.id === id);
      if (!e) return;
      const sal = layout.salience.get(id) ?? 1;
      const col = kindColor(e.kind);
      const mesh = o as THREE.Mesh;
      const mat = mesh.material as THREE.Material;
      const isHalo = (mesh.userData as any).isHalo;
      const isGhost = (mesh.userData as any).isGhost;
      const finalSal = this.hoverReinforce(sal, id);
      const layerBase = LAYER_BASE[e.layer] ?? 1;
      mesh.scale.setScalar(1 + (finalSal - 0.5) * 0.32);
      let baseOpacity = isHalo ? 0.1 : 1;
      if (isGhost) baseOpacity = 0.22;
      mat.opacity = baseOpacity * layerBase * (0.16 + finalSal * 0.84);
      if (mat instanceof THREE.MeshStandardMaterial) {
        // Luminous: keep the emissive scaleable by focus salience. Top-authority
        // classes keep their boost (that is what makes the selective bloom selective).
        const c = new THREE.Color(col);
        mat.color.set(c.clone().multiplyScalar(0.10).lerp(SURFACE_BG, 0.45));
        mat.emissive.copy(c);
        const author = topAuthorityBoost(e.kind);
        mat.emissiveIntensity = (author ? 1.7 : 1.05) * (0.55 + finalSal * 0.75);
      } else if (mat instanceof THREE.MeshBasicMaterial) {
        mat.color.set(toneColor(col, finalSal));
      }
      // L3 edges + gap markers also recede with the entity but stay subtle.
    });

    // label policy: origin/outcome always; focused + direct chain on MEDIUM/CLOSE.
    this.labelsByEntity.forEach((spr, id) => {
      const e = this.entities.find((x) => x.id === id);
      if (!e) return;
      const visible = this.labelPolicy(e);
      spr.visible = visible;
      if (visible) {
        const sal = layout.salience.get(id) ?? 1;
        (spr.material as THREE.SpriteMaterial).opacity = 0.2 + sal * 0.8;
      }
    });
    // link labels only on demand (provenance toggle)
    this.stageSprites.forEach((spr) => {
      if ((spr.userData as any).isLinkLabel) spr.visible = this.provenanceVisible;
    });
    this.positionFocusRing();
  }

  private positionFocusRing() {
    if (!this.focusRing) return;
    const id = this.focusId;
    const e = id ? this.entities.find((x) => x.id === id) : undefined;
    if (!e) {
      this.focusRing.visible = false;
      return;
    }
    this.focusRing.position.set(e.position.x, e.position.y, e.position.z);
    this.focusRing.scale.setScalar(e.radius * 1.35);
    (this.focusRing.material as THREE.MeshBasicMaterial).color.set(toneColor(kindColor(e.kind), 1));
    this.focusRing.visible = true;
  }

  private isOriginOrOutcome(e: FieldEntity): boolean {
    return e.kind === 'PROBLEM' || e.kind === 'RESULT' || e.kind === 'FROZEN';
  }

  private labelPolicy(e: FieldEntity): boolean {
    if (this.hideLabels) return false; // §4bis — visual grammar without labels
    if (this.isOriginOrOutcome(e)) return true;
    if (!this.focusId) return false;
    if (e.id === this.focusId) return true;
    const nb = this.neighbours.get(this.focusId);
    if (!nb) return e.id === this.focusId;
    if (nb.direct.has(e.id) && this.semanticZoom >= 0.7) return true;
    if (nb.second.has(e.id) && this.semanticZoom >= 1.6) return true;
    return false;
  }

  private hoverReinforce(sal: number, id: string): number {
    if (this.hoverId === id) return 1;
    return sal;
  }

  // ---------- interaction ----------

  private bindEvents() {
    const el = this.container;
    el.addEventListener('pointermove', (ev) => this.onPointerMove(ev));
    el.addEventListener('pointerleave', () => { this.hoverId = null; this.needsRender = true; });
    el.addEventListener('click', (ev) => this.onClick(ev));
    el.addEventListener('wheel', () => { this.needsRender = true; }, { passive: true });
  }

  private pick(ev: PointerEvent | MouseEvent): string | null {
    const rect = this.renderer.domElement.getBoundingClientRect();
    this.pointer.x = ((ev.clientX - rect.left) / rect.width) * 2 - 1;
    this.pointer.y = -((ev.clientY - rect.top) / rect.height) * 2 + 1;
    this.raycaster.setFromCamera(this.pointer, this.camera);
    const hits = this.raycaster.intersectObjects(this.pickables, true);
    if (!hits.length) return null;
    let o: THREE.Object3D | null = hits[0].object;
    while (o && !this.entityPicks.has(o)) o = o.parent;
    return o ? (this.entityPicks.get(o) ?? null) : null;
  }

  private onPointerMove(ev: PointerEvent) {
    const id = this.pick(ev);
    const changed = id !== this.hoverId;
    this.hoverId = id;
    if (changed) this.needsRender = true;
  }

  private onClick(ev: MouseEvent) {
    const id = this.pick(ev);
    if (id) this.callbacks.onEntitySelect?.(id);
  }

  // ---------- render loop ----------

  private updateSemanticZoom() {
    if (!this.layout) return;
    const span = this.axisSpan();
    const dist = this.camera.position.distanceTo(this.controls.target);
    const frac = dist / Math.max(span, 1);
    const z = THREE.MathUtils.clamp((1.62 - frac) * 1.5, 0, 2.4);
    if (Math.abs(z - this.semanticZoom) > 0.05) {
      this.semanticZoom = z;
      this.zoomCur = z;
      this.needsRender = true;
    }
  }

  private axisSpan(): number {
    if (!this.layout || !this.layout.entities.length) return 800;
    let minX = Infinity, maxX = -Infinity;
    this.layout.entities.forEach((e) => { minX = Math.min(minX, e.position.x); maxX = Math.max(maxX, e.position.x); });
    return Math.max(1, maxX - minX);
  }

  private loop = () => {
    if (this.disposed) return;
    this.raf = requestAnimationFrame(this.loop);
    const dt = this.clock.getDelta();
    if (!this.backendReady) return;
    this.controls.update(dt);
    this.updateSemanticZoom();
    if (this.needsRender || this.animating || this.controls.enableDamping) {
      if (this.composer && !this.webgpuUsed) {
        this.composer.render();
        this.renderLabels();   // composite label sprites on top, WITHOUT bloom
      } else {
        this.renderer.render(this.scene, this.camera);
      }
      this.needsRender = false;
    }
    // Deterministic readiness: fires only AFTER the first frame has actually been
    // drawn with a layout, i.e. after the flag-applied label pass (applyFocus) ran.
    // The capture harness waits on `[data-cog-ready="1"]` instead of a setTimeout.
    if (this.layout && !this.readySignalled) {
      this.readySignalled = true;
      this.container.setAttribute('data-cog-ready', '1');
    }
  };

  /** LS93 v7 fix — composite the label sprites (labelScene) on top WITHOUT bloom so
   *  the text stays crisp/legible instead of being blown out to a glowing pill. */
  private renderLabels() {
    if (!this.labelScene || this.webgpuUsed) return;
    this.renderer.autoClear = false;
    this.renderer.render(this.labelScene, this.camera);
    this.renderer.autoClear = true;
  }

  private onResize() {
    const w = this.container.clientWidth;
    const h = this.container.clientHeight;
    if (!w || !h) return;
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h);
    this.needsRender = true;
  }

  private animateTo(fit: { position: THREE.Vector3; target: THREE.Vector3 }, duration: number) {
    const fromPos = this.camera.position.clone();
    const fromTarget = this.controls.target.clone();
    const start = performance.now();
    this.animating = true;
    const step = () => {
      if (this.disposed) return;
      const t = Math.min(1, (performance.now() - start) / duration);
      const ease = 1 - Math.pow(1 - t, 3);
      this.camera.position.lerpVectors(fromPos, fit.position, ease);
      this.controls.target.lerpVectors(fromTarget, fit.target, ease);
      this.camera.lookAt(this.controls.target);
      this.needsRender = true;
      if (t < 1) requestAnimationFrame(step);
      else this.animating = false;
    };
    requestAnimationFrame(step);
  }

  /** Frame the WHOLE cognitive axis across the view, axis horizontal, authority-height
   *  vertical, field-depth receding. Start (QUESTION) and end (RESULT/FROZEN) both
   *  visible; leaves enough margin for the glyph sizes. */
  private frameAxis(): { position: THREE.Vector3; target: THREE.Vector3 } {
    const b = this.axisBounds();
    const cx = (b.minX + b.maxX) / 2;
    const cy = (b.minY + b.maxY) / 2;
    const spanX = (b.maxX - b.minX) + 160;
    const fovY = (this.camera.fov || 48) * (Math.PI / 180);
    const aspect = Math.max(0.2, this.camera.aspect || 1.6);
    const fovX = 2 * Math.atan(Math.tan(fovY / 2) * aspect);
    const dist = (spanX / 2) / Math.tan(fovX / 2) * 1.04;
    const target = new THREE.Vector3(cx, cy, 0);
    const dir = new THREE.Vector3(0.04, 0.34, 0.9).normalize();
    const position = target.clone().add(dir.multiplyScalar(dist));
    return { position, target };
  }

  private axisBounds() {
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity, minZ = Infinity, maxZ = -Infinity;
    this.entities.forEach((e) => {
      minX = Math.min(minX, e.position.x); maxX = Math.max(maxX, e.position.x);
      minY = Math.min(minY, e.position.y - e.radius); maxY = Math.max(maxY, e.position.y + e.radius);
      minZ = Math.min(minZ, e.position.z); maxZ = Math.max(maxZ, e.position.z);
    });
    if (!isFinite(minX)) { minX = -120; maxX = 120; minY = -20; maxY = 20; minZ = -40; maxZ = 40; }
    return { minX, maxX, minY, maxY, minZ, maxZ };
  }

  // ---------- label sprite ----------

  private makeLabel(text: string, color: number, opacity: number): THREE.Sprite {
    const cap = text.length > 20 ? text.slice(0, 19) + '…' : text;
    const size = 256;
    const canvas = document.createElement('canvas');
    canvas.width = size; canvas.height = 36;
    const ctx = canvas.getContext('2d')!;
    ctx.font = '600 15px "JetBrains Mono", monospace';
    ctx.textBaseline = 'middle';
    ctx.textAlign = 'center';
    const w = ctx.measureText(cap).width + 20;
    ctx.fillStyle = 'rgba(255,255,255,0.95)';
    roundRect(ctx, (size - w) / 2, 4, w, 28, 6);
    ctx.fill();
    const c = '#' + color.toString(16).padStart(6, '0');
    ctx.strokeStyle = c;
    ctx.lineWidth = 1;
    roundRect(ctx, (size - w) / 2, 4, w, 28, 6);
    ctx.stroke();
    ctx.fillStyle = c;
    ctx.fillText(cap, size / 2, 18);
    const tex = new THREE.CanvasTexture(canvas);
    tex.minFilter = THREE.LinearFilter;
    const mat = new THREE.SpriteMaterial({ map: tex, transparent: true, opacity, depthTest: false });
    const spr = new THREE.Sprite(mat);
    spr.scale.set(size * 0.7, 36 * 0.7, 1);
    spr.center.set(0.5, 0.5);
    // LS93 v7 fix — label sprites render on layer 1 so the bloom pass (geometry only)
    // never blows out the text; they are composited on top WITHOUT bloom and stay legible.
    spr.layers.set(1);
    return spr;
  }
}

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}
