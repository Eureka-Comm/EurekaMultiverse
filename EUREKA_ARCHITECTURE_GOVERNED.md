# EUREKA — Arquitectura Cognitiva Gobernada (Especificación de Autoridad)

> **Estado:** FORMALIZADO — documento rector. **Regla:** toda modificación de un EM debe declarar su autoridad y si el LLM es subordinado. No se cambia un EM sin actualizar este documento.
> **Tesis central:** **EUREKA no es un sistema de 8 agentes LLM.** Es un sistema cognitivo gobernado de 8 EM, donde cada EM tiene una **autoridad específica** y el **LLM es un mecanismo subordinado** — usado solo cuando la naturaleza de la operación requiere lenguaje/interpretación.

---

## 0. Regla fundamental (la que nunca se viola)

> **El LLM puede generar candidatos, interpretaciones y narrativa; NUNCA puede convertirse silenciosamente en la autoridad del artefacto que está generando.**

Es decir: `LLM ≠ autoridad matemática` y `LLM ≠ autoridad cognitiva`.

- El LLM puede **proponer, interpretar, explicar, narrar**.
- **Python** gobierna estructura, validación y autoridad.
- **MathEngine / ACFL** gobierna matemática (no el LLM).
- **Fuzzy / Neural** gobierna donde corresponde.
- **HITL** gobierna donde existe juicio humano.
- El **frontend** visualiza el conocimiento; el **storytelling** lo convierte en narrativa comprensible **de conocimiento ya gobernado** (no lo inventa).

---

## 1. Modelo de capas

```text
                           EUREKA
                              │
                   ┌──────────┴──────────┐
                   │                     │
            Capa Cognitiva          Capa Matemática
                   │                     │
          DeepSeek / Ollama       MathEngine / ACFL
                   │                     │
                   └──────────┬──────────┘
                              │
                      8 EM gobernados
                              │
        ┌─────────────────────┼──────────────────────┐
        │                     │                      │
     SEMÁNTICA            MATEMÁTICA            EJECUCIÓN
        │                     │                      │
 Core / Structurer       Predictor              Actioner
 Descriptor              Fuzzy/GCLV            Installer
 Prescriptor             Neural                Publisher*
```

> Incluso esto es una simplificación: el **Publisher**, por ejemplo, tiene una parte generativa **y** una parte de gobernanza. No es "el LLM que escribe el informe".

---

## 2. Autoridad explícita de los 8 EM

| EM              | Función primaria                     | LLM | Determinismo | Autoridad              |
| --------------- | ------------------------------------ | --: | -----------: | ---------------------- |
| **Core**        | comprender/orquestar el problema     |  🟡 |           🟢 | Problema / objetivo     |
| **Structurer**  | construir modelo estructurado        |  🟡 |           🟢 | Estructura              |
| **Descriptor**  | extraer conocimiento de evidencia    |  🟢 |           🟡 | Findings / evidencia    |
| **Predictor**   | predicción matemática                |  ❌ |           🟢 | Predicción              |
| **Prescriptor** | alternativas / decisión / prescripción| 🟡 |           🟢 | Prescripción gobernada  |
| **Actioner**    | transformar prescripción en acciones | ❌/🟡 |         🟢 | ActionPlan              |
| **Installer**   | autorización / ejecución / freeze    |  ❌ |           🟢 | Ejecución               |
| **Publisher**   | resultado + narrativa                |  🟢 |          🟢* | Publicación             |

> `🟡` = **puede usar LLM, pero el LLM NO posee la autoridad del resultado.** El determinismo es la base; el LLM es subordinado.

---

## 3. Dataflow por EM (flujos corregidos)

### 3.1 Predictor — NO LLM (corregido)
```text
Evidence
   ↓
Mathematical Engine (ACFL / GCLV / MSE)
   ↓
Prediction
   ↓
uncertainty (NOT_AVAILABLE, no se alucina)
   ↓
validation (Gate 12/13/14/15/17/20)
   ↓
PredictionKnowledge
```
El lenguaje, si se necesita después, entra **después**:
```text
PredictionKnowledge → Prescriptor / Publisher → interpretación lingüística
```
> **Confirmado:** el Predictor es 100% Python/matemático (ya implementado, `model=ACFL_DETERMINISTIC`).

### 3.2 Descriptor — híbrido (NO "LLM puro")
No debe ser `PDF → DeepSeek → "estos son mis insights"` (la estructura cognitiva quedaría dependiendo de una generación probabilística).

```text
                 EVIDENCIA
                     │
          ┌──────────┴──────────┐
          │                     │
   extracción estructural    DeepSeek
          │                     │
          │              interpretación
          │                     │
          └──────────┬──────────┘
                     ↓
             Descriptor
                     ↓
          Validated Findings
                     ↓
          provenance / evidence
```
- **Python:** identifica documentos, extrae texto, identifica entidades, conserva offsets/referencias, valida estructura, registra provenance.
- **DeepSeek:** interpreta texto, identifica relaciones, propone findings, resume, detecta patrones semánticos.
- **Python (autoridad vuelve):** valida, estructura, vincula evidencia, **rechaza findings sin soporte**.

### 3.3 Prescriptor — matemática primero, LLM interpreta (no inventa el óptimo)
No debe ser `DeepSeek → "ALT-002 parece la mejor"`.

```text
Prediction + Evidence + Alternatives + Constraints + ACFL / GCLV
   ↓
Mathematical / deterministic evaluation   ← cálculo, autoridad
   ↓
candidate alternatives
   ↓
DeepSeek                                  ← rationale / interpretación semántica
   ↓
Prescriptor validation
   ↓
HITL
   ↓
Validated Prescription
```
> El LLM **puede interpretar el óptimo; no debe inventar el óptimo.**

### 3.4 Actioner / Installer — deterministas
- **Actioner:** transforma prescripción → ActionPlan (topo, dedup, validación). `❌/🟡`.
- **Installer:** autorización, ejecución, freeze (FAIL_CLOSED/WAITING). `❌`.
- Ambos → autoridad de **ejecución** (Python).

### 3.5 Publisher — resultado + narrativa (NO "LLM que escribe")
```text
              FROZEN KNOWLEDGE
                     │
                     ▼
             Publisher Core
                     │
        ┌────────────┼────────────┐
        │            │            │
     RESULT      VISUAL MODEL   STORY MODEL
        │            │            │
        │            │            ↓
        │            │       DeepSeek
        │            │            │
        │            │       narrative
        │            │            │
        └────────────┴────────────┘
                     ↓
             Published Result
```
- **LLM** genera: narrativa, explicación, executive summary, storytelling, adaptación a audiencia.
- **NO** decide qué conocimiento es verdadero: el conocimiento ya viene **gobernado upstream** (frozen/validado).

---

## 4. HITL como capa de autoridad (NO una pantalla de confirmación)

> **"El sistema calcula, interpreta y propone; EUREKA-0 conserva la autoridad sobre aquello que requiere juicio humano."**

```text
                 EUREKA-0
                    │
             HUMAN AUTHORITY
                    │
        ┌───────────┼───────────┐
        │           │           │
      risk        values    authorization
        │           │           │
        └───────────┼───────────┘
                    ↓
                   HITL
                    ↓
             governed artifact
```
HITL cubre: **decisión, autorización, freeze, excepciones, acciones sensibles, contradicciones, incertidumbre relevante.**

---

## 5. Visualization — significado cognitivo (NO un panel de gráficas)

No debe ser `datos → chart`. Debe ser:
```text
                 KNOWLEDGE GRAPH
                       │
          ┌────────────┼────────────┐
          ↓            ↓            ↓
       Evidence     Prediction   Decision
          │            │            │
          └────────────┼────────────┘
                       ↓
                  Visualization
                       ↓
               Cognitive meaning
                       ↓
                  Storytelling
```
La visualización responde: **¿Qué está pensando/descubriendo/decidiendo EUREKA y por qué?** No "¿qué gráfica pongo en este panel?".

---

## 6. Arquitectura completa

```text
                    EUREKA
                       │
          ┌────────────┴────────────┐
          │                         │
       KNOWLEDGE                 AUTHORITY
          │                         │
          │                        HITL
          │                         │
    ┌─────┴─────┐                   │
    │           │                   │
 SEMANTIC    MATHEMATICAL           │
    │           │                   │
 DeepSeek   ACFL/GCLV               │
    │        Neural                 │
    │        Fuzzy                  │
    └─────┬─────┘                   │
          │                         │
          ▼                         ▼
       Decision ───────────────→ Human
          │
          ▼
      Prescription
          │
          ▼
       ActionPlan
          │
          ▼
       Installer
          │
        Freeze
          │
          ▼
       Publisher
          │
     ┌────┴────┐
     ▼         ▼
Visualization Storytelling
     │         │
     └────┬────┘
          ▼
    Cognitive Narrative
```

---

## 7. Decisión de arquitectura adoptada

**Híbrido gobernado por autoridad** (no "todo determinista" ni "Descriptor determinista + Publisher LLM"):

```text
LLM donde existe lenguaje/interpretación
      +
Python donde existe estructura/validación
      +
MathEngine donde existe matemática
      +
Fuzzy/Neural donde corresponde
      +
HITL donde existe autoridad humana
      +
Frontend para visualizar el conocimiento
      +
Storytelling para convertir conocimiento gobernado en narrativa comprensible
```

Y la regla rectora:

> **El LLM puede generar candidatos, interpretaciones y narrativa; nunca puede convertirse silenciosamente en la autoridad del artefacto que está generando.**

Esto permite mantener **DeepSeek/Ollama** como componente real de EUREKA sin convertir a EUREKA en un simple wrapper de DeepSeek.

---

## 8. Reglas de implementación (para cambios futuros en EM)

1. **Todo EM declara** en su docstring/contrato: autoridad, LLM (`🟢/🟡/❌`), determinismo.
2. El **LLM nunca escribe el campo de autoridad**: solo produce candidatos que Python **valida**.
3. **Predictor** y **Accioner/Installer**: `LLM=❌` (deterministas/ejecución).
4. **Descriptor/Prescriptor/Publisher**: `LLM=🟡/🟢` pero SIEMPRE precedido por cálculo/gobierno y seguido por validación/provenance.
5. **HITL** siempre que exista juicio humano (decisión, autorización, freeze, contradicción, incertidumbre).
6. **Provenance** obligatorio en todo hallazgo/predicción/prescripción que provenga de un candidato LLM.
7. **No se alucina**: si no hay dato/fórmula autorizada → `NOT_EVALUATED` / `NOT_AVAILABLE`.

---

*Este documento es la fuente de verdad arquitectónica. Cualquier cambio de EM que no respete §0/§8 se rechaza como no-EUREKA.*
