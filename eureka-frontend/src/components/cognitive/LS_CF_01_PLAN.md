# LS-CF-01 — Constellation → Cognitive Operational Surface (plan)

> Objetivo: convertir la Constellation (capa de representación) en una **superficie
> operativa** de observabilidad / navegación / trazabilidad / gobernanza del estado
> cognitivo real de EUREKA. Semántica > estética. **Sin** AgentFactory/Dynamic Agents
> todavía, **sin** más partículas/animaciones, **sin** métricas inventadas ni agentes
> ficticios. Honesty layer: si no se sabe, se dice "NO SÉ".

## Principio rector
**La Constellation no representa "el proceso de EUREKA"; representa el estado
cognitivo verificable de un caso y permite operar sobre él.**

Geometría con significado; la ausencia de información es información operativa.

---

## Arquitectura (una superficie, una fuente, cuatro modos)

```
CANONICAL STATE
   ↓
CognitiveProjection (LS86, puro)
   ↓
CognitiveGraph { nodes, edges, lineage, currentState }
   ↓
┌──────────────────────────────────────────────┐
│          EUREKA COGNITIVE FIELD               │
│                                               │
│  UNDERSTAND · EXPLORE · AUDIT · OPERATE       │
│     │            │        │         │         │
│  Operation Map  Constellation  Provenance  HITL/State
│                                               │
│  Inspector / Evidence / Lineage / HITL        │
└──────────────────────────────────────────────┘
```

Todas las sub-superficies consumen **el mismo grafo** (una sola fuente de datos).

---

## Funcionalidades (mapeadas a lo ya implementado / pendiente)

| # | Capacidad | Estado | Dónde |
|---|---|---|---|
| 1 | **11 tipos de objeto cognitivo** | ✅ en el grafo | `cognitiveProjectionGraph.ts` |
| 2 | **Semántica de aristas** (derived_from/supports/produced_by/selected_by/authorized_by/executed_as/frozen_as) — nunca "causes" | ✅ en el grafo | `cognitiveProjectionGraph.ts` |
| 3 | **Honestidad** (DATA NOT AVAILABLE / NOT_EVALUATED / UNSUPPORTED / NOT_APPLICABLE / WAITING_FOR_HUMAN_INPUT) | ✅ campo (integer de la etapa + chips) | `CognitiveOperationalField.tsx` |
| 4 | **Autoridad humana** (HUMAN AUTHORITY en DECISION) | ✅ chip | `CognitiveOperationalField.tsx` |
| 5 | **Recomendado vs seleccionado humano** (recommended / humanSelected) | ✅ chips REC / HUMAN SELECT | `CognitiveOperationalField.tsx` |
| 6 | **Why?** (reconstrucción de provenance hacia arriba al hacer click) | ✅ panel AUDIT | `CognitiveOperationalField.tsx` |
| 7 | **Detección de huecos / Cognitive Integrity** (etapas presentes, unsupported, no evaluado, waiting human, frozen, human decisions) | ✅ strip INTEGRITY | `CognitiveOperationalField.tsx` |
| 8 | **4 modos** (UNDERSTAND / EXPLORE / AUDIT / OPERATE) | ✅ tabs | `CognitiveOperationalField.tsx` |
| 9 | **Inspector / detalle** | parcial (¿por qué?) | integrar `Inspector`/`ArtifactDetail` |
| 10 | **Replay (línea de tiempo por lineage)** | ⏳ pendiente | animar aparición por `lineage` |
| 11 | **What changed?** (before/after acción→resultado) | ⏳ pendiente | diff del pipeline |
| 12 | **Chat controla la superficie** (focus/highlight/zoomTo) | ⏳ pendiente | puente Chat→Field |

---

## Siguientes pasos (orden priorizado, incremental)

1. **LS-CF-01a (hecho hoy):** superficie operativa con 4 modos + honestidad +
   autoridad humana + propuesto-vs-decidido + WHY + integridad. Ver en dev:
   `/__field` (o `?state=completed|open`).
2. **LS-CF-01b:** integrar el **Inspector** real (`ArtifactDetail`) en el panel de
   selección (en lugar del panel inline), reutilizando piezas existentes.
3. **LS-CF-01c:** **Cognitive Replay** — slider por `lineage` que muestra el estado en T0…Tn
   ("¿qué sabía EUREKA cuando decidió?"). Sin animación cosmética.
4. **LS-CF-01d:** **What changed?** (before → action → after) sobre RESULT/frozen.
5. **LS-CF-01e:** **Chat→Field** (botón "ver en el campo" resalta/focaliza el nodo).
6. **LS-CF-01f:** **Cognitive Integrity** como overlay clicable (click en gap → foco).
7. **Después (solo cuando exista el Agent Runtime real):** conectar la superficie a
   `AgentGenome`, segregators e integrators (segregación → especialización → integración).
   La misma superficie visualizará esa evolución.

---

## Lo que NO se hará
❌ más partículas / nebulosas / animaciones · ❌ 3D como principal · ❌ nodos para llenar
espacio · ❌ líneas sin semántica · ❌ agentes ficticios · ❌ métricas inventadas ·
❌ "AI confidence" inventada · ❌ causalidad visual inexistente · ❌ grafo enorme por
"Eureka es complejo". La complejidad **emerge de los datos reales**.

---

## Referencia
- `CONSTELLATION_SYSTEM.md` (documento del sistema actual, respaldado en `_backup_constelaciones`).
- Componente operativo: `src/components/cognitive/CognitiveOperationalField.tsx`.
- Demo DEV: `src/pages/CognitiveFieldDemo.tsx` → `/__field`.
