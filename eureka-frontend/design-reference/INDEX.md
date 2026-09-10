# Referencias de diseño — Front-end Eureka

> Carpetas de referencia para replicar el "lenguaje visual" de los reels
> (cerebro / constelación de agentes) en el front-end de Eureka.
> Las imágenes son las **portadas** de cada reel (el video completo está detrás de
> login de Instagram; por eso se usan las portadas como referencia visual).

## Mapa reel → implementación

| Portada | Autor | Qué es | Implementación open-source más cercana | ¿Replica el look? |
|---|---|---|---|---|
| `DbYh2P-MQnj.jpg` | alassafi.ai | Mapa "en vivo" de 137 agentes por departamento (hub central + constelación) | Concepto: **agems-ai/agems** (Agent Management System, org-chart agentes+humanos) | El **concepto** sí; el look constelación es **custom** |
| `DbwfkLPp36B.jpg` | wenmardigian | Dashboard "Cerebro + Agentes IA" (nube de neuronas + KPIs + agentes + conexiones + caja) | Concepto: **getnao/sylph** (company brain) + **getnao/nao** (analytics) | El **concepto** sí; el look es **custom** (d3/three) |
| `DaCFIiEMPEn.jpg` | kzzy47 | "Op system que compone": galaxia/cerebro con esfera central animada y anillos | Concepto: **sylph / agems** (agente OS) | **Custom** (constelación 3D) |
| `DZcSLefuxRU.jpg` | jonathonmj | Constelación de herramientas (Z.E.R.O), colores por categoría | **Lawofall/AgentCore** (multi-agent workbench) + Agent Zero frameworks | **Custom** (grafo de nodos) |
| `DbcPo0dMQ3d.jpg` | bennett.spooner | "Founder OS" (portada = toma de vida, no UI) | **agems / agent-zero** | No evaluable por portada |

## Stack para replicar el look
- **Grafo de nodos**: `@xyflow/react` (React Flow) o `d3`.
- **Layout orgánico / blobs**: `d3-force` (forceSimulation + forceManyBody + forceX/Y por cluster).
- **Núcleo cósmico / 3D**: `three.js` (WebGL) o SVG + gradientes + blur.
- **Animación "viva"**: `framer-motion` (pulso de nodos, filamentos, auroras).
- **Tema**: oscuro cósmico (violeta profundo → casi negro) + acentos neón por dominio.

## Componente de muestra (ya replicado en Eureka)
- `src/components/cognitive/CoreConstellation.tsx` — réplica con `d3-force` (constelación
  por departamento + nube de "cerebro" central + filamentos + neón).
- Ver en dev: `http://127.0.0.1:5199/__constellation` (ruta dev-only).
