# EUREKA — Sistema de Constelación / Galaxy (diseño e integración)

> Documento técnico del lenguaje visual "cerebro / constelación / galaxia" (estilo
> reel) implementado en `eureka-frontend`, y de cómo conectarlo a los datos reales
> de Eureka para hacerlo funcional. Cubre: arquitectura, modelo de grafo
> ("grafología"), implementación del render, tema, pipeline de datos y mapa de
> integración.

---

## 1. Propósito

Añadir una **pieza hero espacial** (galaxia + constelación de agentes/etapas) que
comunique de un vistazo el "cerebro cognitivo" de Eureka: el proceso gobernado
(problema → evidencia → hallazgo → predicción → prescripción → decisión → acción →
ejecución → resultado), con sus agentes/entidades orbitando alrededor del núcleo.
Es tanto un **elemento visual de marca** (look "cósmico" premium) como un **mapa
espacial navegable** del estado cognitivo.

---

## 2. Arquitectura y mapa de archivos

```
eureka-frontend/src
├─ index.css                            # TOKENS de tema (oscuro cósmico por defecto + .theme-light)
├─ App.tsx                              # ruta DEV /__constellation (solo import.meta.env.DEV)
│
├─ components/
│  ├─ layout/
│  │  ├─ EurekaShell.tsx                # monta <ThemeToggle/> en el header
│  │  └─ ThemeToggle.tsx                # alterna oscuro/claro, persiste en localStorage
│  └─ cognitive/
│     ├─ CoreConstellation.tsx          # constelación ARBÓREA / data-driven (recibe `clusters`)
│     ├─ CognitiveConstellation.tsx     # wrapper DATOS REALES: grafo cognitivo → clusters
│     └─ GalaxyConstellation.tsx        # GALAXIA: núcleo de brasas + nodos que orbitan
│
├─ pages/
│  ├─ Cognitive/Chat.tsx                # hero = <GalaxyConstellation/> (página real)
│  └─ CoreConstellationDemo.tsx         # demo DEV (galaxia por defecto, ?mode=tree)
│
└─ (datos reales)
   store/workStore.ts                   # zustand: activeWork (CanonicalWorkState)
   hooks/useCognitiveProjection.ts      # buildCognitiveProjection(state) -> CognitiveProjectionDTO
   domain/cognitiveProjectionGraph.ts   # buildCognitiveProjectionGraph(dto) -> grafo gobernado
   domain/cognitiveProjection.ts        # DTO + build (single source, LS3 §30 / LS86)
```

**Flujo en dos niveles:**

1. **Evaluación (sin backend):** `GalaxyConstellation` / `CoreConstellation` generan
   datos simulados (deterministas, con `mulberry` seed) para mostrar el look sin estado.
2. **Datos reales:** `CognitiveConstellation` lee `workStore.activeWork` →
   `useCognitiveProjection` → `buildCognitiveProjectionGraph` → agrupa por `kind` en
   `clusters` → los pasa a `CoreConstellation` (render presentacional).

---

## 3. La "grafología" — modelo de grafo y relaciones

### 3.1 Tipos de nodo (etapas cognitivas gobernadas)
`CognitiveProjectionGraph.nodes[]` — cada uno `GraphArtifact`:

| `kind` | rol | EM que lo produce |
|---|---|---|
| `PROBLEM` | Pregunta/objetivo | EM Core |
| `EVIDENCE` | Texto/fragmentos extraídos y anclados | EM Structurer |
| `FINDING` | Hallazgo (afirmación con evidencia) | EM Descriptor |
| `PREDICTION` | Predicción determinista (ACFL/GCLV) | EM Predictor |
| `PRESCRIPTION` | Prescripción (racionalidad) | EM Prescriptor |
| `ALTERNATIVE` | Alternativas candidatas/recomendada/elegida | EM Prescriptor |
| `DECISION` | Decisión humana (solo de `human_decision`) | EM Prescriptor/Installer |
| `ACTION` | Plan de acción (pasos) | EM Actioner |
| `EXECUTION` | Ejecución (simulada preservada) | EM Installer |
| `RESULT` | Resultado publicado | EM Publisher |
| `FROZEN` | Resultado congelado (firma) | EM Installer |

### 3.2 Campos de un nodo (`GraphArtifact`)
`id, kind, label, status, authority, provenance[], evidence[], uncertainty, em,
sourceField, recommended, humanSelected, description, numericValue?, modelType?,
stepCount?`.

- **`authority`**: `PYTHON_GOVERNED / LLM_CANDIDATE / VALIDATED / UNSUPPORTED /
  HUMAN_AUTHORIZED / SIMULATED / PUBLISHED / FROZEN` — refleja el nivel de gobierno.
- **`status`**: depends on kind (`grounded`, `RECOMMENDED`, `HUMAN_SELECTED`, …).
- **`recommended`** (recomendado del sistema) y **`humanSelected`** (voto humano)
  **nunca se fusionan** (anti-hallucinación, LS86).

### 3.3 Semántica de aristas (edgelist)
`GraphEdge { source, target, label }`, `label ∈`:

```
derived_from  | supports       | produced_by
selected_by   | authorized_by  | executed_as  | frozen_as
```

- Se prohíbe usar la palabra "causes".
- `projectionConflict` (ActionPlan ≠ decisión humana) se representa con **dos** aristas
  `selected_by` a dos alternativas distintas — nunca se auto-corrige.
- Los enlaces ausentes se muestran como "DATA NOT AVAILABLE"; **nunca se inventan**.

### 3.4 Jerarquía / proyección (lo que se ve en la constelación)
- **Núcleo (CORE)** = el trabajo/caso en curso.
- **Clusters** = un dominio conceptual. En `CoreConstellation` (modo árbol) cada
  cluster es un **árbol**: hub → ramas (roles) → hojas (agentes/artefactos), como el
  "mapa de agentes" del reel.
- En `GalaxyConstellation` los **nodos orbitan** en anillo alrededor del núcleo,
  conectados al centro y a sus vecinos (cadena), con labels contra-rotados
  (se mantienen horizontales mientras orbitan).
- **Filamentos** = aristas: `core→cluster` (gruesos, con flujo), `cluster→rama→hoja`
  (finos, con dash de "energía").

---

## 4. Implementación del render

### 4.1 SVG + viewBox
Todas las piezas usan **un solo `<svg viewBox="0 0 1440 900">`** (escala fija)
con `width/height:100%`. Esto permite que la galaxia escale a cualquier contenedor
(hero 320px o pantalla completa) manteniendo la composición.

### 4.2 Datos deterministas
- Generador de números pseudoaleatorios `mulberry(seed)` para que el layout **no
  cambie entre renders** (fundamental para evaluar y para pruebas visuales).
- `buildSimulated()` / `buildDust()` / `buildEmbers()` / `buildHeart()` /
  `buildOrbits()` calculan posiciones una sola vez (`useMemo`).

### 4.3 d3-force (solo en `CoreConstellation` simulator)
`buildSimulated()` usa `d3.forceSimulation` (forceManyBody + forceX/forceY por
cluster + forceLink + forceCollide) y `sim.tick(320)` para un layout orgánico
estable de los blobs/árboles. En el render NO se usa d3 (solo para el layout inicial).

### 4.4 Animación (framer-motion)
- **Nodos vivos** (`live`) pulsan opacidad con `repeat: Infinity`.
- **Filamentos con flujo**: `strokeDasharray="5 14"` + `animate={{ strokeDashoffset: [0, -200] }}` (energía que fluye).
- **Auroras/nebulosas**: grandes `div` con `radial-gradient` + `blur`, animados en `x/y`.
- **Galaxia girando**: `<motion.g animate={{ rotate: 360 }}>` con
  `transformOrigin: "720px 440px"` + `transformBox: "view-box"`.
- **Nodos que orbitan + labels horizontales**: el grupo de constelación rota `rotate:360`
  sobre el núcleo; **cada label va en un `motion.g` que contra-rota `rotate:-360`**
  con `transformOrigin` en la posición del nodo, de modo que el texto queda
  horizontal mientras el punto orbita. (Clave: `transformBox:'view-box'` para que las
  coordenadas de `transformOrigin` estén en unidades del viewBox.)

### 4.5 Rendimiento
- Las **partículas estáticas** (dust/estrellas) son `<circle>` normales (no animados) → baratas.
- Solo los **nodos vivos / labels / filamentos** usan `motion.*` (un subconjunto).
- Las partículas van en grupos rotados (transform de GPU), no se re-renderizan por frame.

### 4.6 Colores / neón
Paleta por rol (señales) y por dominio:
- Señales Eureka (oscuro): `cognitive cyan #29e0ff`, `semantic violet #9b6bff`,
  `ranking/authority #ffb03c/#ff7a3c`, `action green #4dff9d`, `blocked red #ff5d5d`.
- Dominios (maqueta): `SALES #ff3d8c`, `DEALS #29e0ff`, `OPERATIONS #ffb03c`,
  `INTELLIGENCE #6fe94b`, `DATA #9b6bff`, `CUSTOMER #ff6ad5`.

---

## 5. Sistema de tema oscuro

`index.css`:
- `:root { … }` → tokens **oscuro cósmico por defecto** (`--eureka-canvas:#07040f`,
  superficies profundas, señales neón, hairline/grid luminosos).
- `.theme-light { … }` → override con los valores claros originales (GitHub-like).
- Tailwind v4 mapea `@theme` (`--color-canvas`, `text-*`, `signal-*`, `spatial-*`)
  a `var(--eureka-*)`; por eso cambiar los tokens re-sklana TODO el shell sin tocar componentes.
- El `ThemeToggle` alterna la clase `.theme-light` en `<html>`, persiste en
  `localStorage('eureka-theme')`, y **por defecto es oscuro**.
- Transición suave (`body transition`) y bloque de código adaptativo (`var(--eureka-surface-elevated)`).

---

## 6. Cómo se alimenta con datos reales (pipeline)

```
workStore.activeWork (CanonicalWorkState)
        │  useCognitiveProjection(state)  → buildCognitiveProjection (puro, LS86)
        ▼
CognitiveProjectionDTO
        │  buildCognitiveProjectionGraph(dto)
        ▼
CognitiveProjectionGraph { nodes: GraphArtifact[], edges: GraphEdge[], lineage }
        │  CognitiveConstellation: agrupa nodes por `kind` → ClustersSpec[]
        ▼
CoreConstellation (clusters)  →  árbol/constelación con datos reales
```

- `CognitiveConstellation` mapea cada `kind` a color neón (`KIND_META`) y a una posición
  radial; los nodos son los artefactos reales; `live` = `DECISION`/
  `HUMAN_AUTHORIZED`/`recommended`/`humanSelected`.
- Si no hay `activeWork`, `CognitiveConstellation` retorna `null` (y las páginas usan
  la versión simulada como fallback de evaluación).

---

## 7. Cómo puede volverse FUNCIONAL para Eureka

### 7.1 Fuentes reales que se pueden conectar
| Fuente (ya existe en Eureka) | Qué mapea en la constelación |
|---|---|
| `CognitiveProjectionGraph` (grafo gobernado) | nodos = artefactos cognitivos; clusters = etapas (`kind`); filamentos = `edges` reales |
| `System/Agents` (agentes) | clúster "agent team" o nodos orbitando (roles/habilidades) |
| `Analytics/Networks`, `Scenarios` | redes/escenarios como constelación |
| `KnowledgeMap` (`components/cognitive/KnowledgeMap`) | conocimiento como cluster del "cerebro" |
| `Story/Timeline`, `ChapterNavigator` | jugar la trayectoria por capítulos (fase del proceso) |
| `ProvenanceChain` / `LineageRibbon` | aristas `derived_from`/`authorized_by`/`executed_as` |

### 7.2 Interacciones naturales a añadir
- **Click en un nodo** → abrir `Inspector`/`ArtifactDetail` (ya existe en
  `components/cognitive/Inspector`).
- **Hover** → tooltip con `label`, `em` (rol 8-EM), `authority`, `status`.
- **Zoom/pan** en el hero → usar `@xyflow/react` (ya es dependencia) para un canvas
  navegable, o `framer-motion` + `useTransform` para zoom sencillo.
- **Filtros** por `kind` / EM / authority; "enfoque" en un subgrafo.
- **Play del tiempo**: animar la aparición de nodos en el orden `lineage`
  (problema → … → resultado) — storytelling del proceso.
- **Drill-down**: clúster `DECISION` → ver alternativas recomendada vs. humana.

### 7.3 Páginas dónde montar el hero
- **Cognitive (Chat / Sandbox / DecisionField)**: hero "cerebro" (ya en Chat) —
  comunica el OS cognitivo.
- **Story (Executive/Technical/Timeline)**: constelación narrada por capítulos.
- **System (Agents / Runtime / Audit)**: "mapa de agentes en operación" (agentes como
  nodos orbitando, estado/audit como color).
- **Analytics (Dashboard / Network / Networks / Scenarios)**: redes del caso.

### 7.4 Valor
- **Ejecutivo**: entiende de un vistazo el pipeline cognitivo (qué se decidió y por qué).
- **Operador**: superficie espacial para navegar el estado, inspiración e interacción.
- **Marca**: el "wow" cósmico posiciona a Eureka como un *agent/cognitive OS*, no un chat.

---

## 8. Extensiones / roadmap sugerido
1. Conectar la constelación **árbol** y la **galaxia** al grafo real con interacciones
   (click→Inspector, filtros, play de fases).
2. Migrar el hero a un **canvas React Flow** (`@xyflow/react`) para pan/zoom y layouts
   preservando el look (nodos SVG/HTML, glows, filamentos animados; o `three.js` WebGL
   para partículas 3D).
3. Aplicar el **tema oscuro** a más superficies y ajustar contrastes de las señales neón
   para legibilidad en gobernanza/decision.
4. Data-driven: pasar `clusters` reales a `GalaxyConstellation` (nodos = agentes/casos)
   y a `CoreConstellation` (árbol = organización/etapas).

---

## 9. Cómo verlo (rutas DEV)
- `/__constellation` → **galaxia** (núcleo de brasas + corazón púrpura + nodos orbitando), fondo negro.
- `/__constellation?mode=tree` → **árbol de agentes** (6 dominios con ramas).
- `/legacy/chat` → página real con la galaxia como hero + tema oscuro + toggle.
- Toggle de tema en el header (Light/Dark).
```
