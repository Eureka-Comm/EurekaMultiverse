import React, { useState } from 'react';
import { useWorkStore } from '../store/workStore';
import HITLDecisionWidget from './HITLDecisionWidget';
import Markdown from './Markdown';
import { buildNarrativeStages, findActiveHITLStage } from '../domain/narrative';
import { buildCopilotNarrativeContext } from '../domain/cognitiveStory';
import { useCognitiveProjection } from '../hooks/useCognitiveProjection';
import { ExecutiveCognitiveAnswer, type CognitiveFocus } from './cognitive/ExecutiveCognitiveAnswer';
import { API_BASE } from '../lib/apiBase';

// LS95 (auth): the LLM copilot is reached ONLY through the EUREKA backend, never via a
// browser-facing proxy that would expose DEEPSEEK_API_KEY. The backend holds the key and is
// the only component that talks to DeepSeek. This base mirrors everything else in the app.
const COPILOT_API = `${API_BASE}/api/copilot`;

// Sanitize raw DSML tool-call markup leak from the model (e.g. `<| DSML | tool_calls ...`).
// The model sometimes emits its function-call as inline DSML text instead of the structured
// `tool_calls` array; never show that raw — replace with a digestible EUREKA interaction line.
function sanitizeDsml(text: string): string {
  if (!text) return text;
  const t = text.trim();
  if (t.includes('<| DSML |') || t.includes('DSML')) {
    const m = t.match(/invoke name=['"]?([^'">]+)['"]?/);
    const tool = m ? m[1] : 'EUREKA';
    const param = t.match(/work_id['"]?\s*[=>]\s*['"]?([A-Z0-9-]+)['"]?/i);
    const wid = param ? ` (${param[1]})` : '';
    return `Consultando a EUREKA${wid} mediante la herramienta «${tool}»...`;
  }
  return text;
}

export default function DeepSeekCopilot({
  onExploreCognitiveStory,
}: {
  onExploreCognitiveStory?: (chapter: CognitiveFocus) => void;
}) {
  const activeWork = useWorkStore((state) => state.activeWork);
  const toolCall = useWorkStore((state) => state.toolCall);

  // SINGLE SOURCE for the Executive Cognitive Answer — never raw state in the view.
  const dto = useCognitiveProjection(activeWork);
  
  const [input, setInput] = useState('');
  const [history, setHistory] = useState<any[]>([]);
  const [isWaiting, setIsWaiting] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [openReasoning, setOpenReasoning] = useState<Record<number, boolean>>({});
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const hasInitializedRef = React.useRef(false);
  const attachEvidence = useWorkStore((state) => state.attachEvidence);
  // LS95: guard so the FINAL concrete answer is narrated exactly once, when the
  // pipeline actually reaches COMPLETED (not on a pre-completed reload).
  const completedNarratedRef = React.useRef(false);
  const isFirstRenderRef = React.useRef(true);
  const prevStatusRef = React.useRef<string | undefined>(undefined);

  const submitMessage = async (msgText: string, file: File | null) => {
    if ((!msgText.trim() && !file) || !activeWork) return;
    
    setIsWaiting(true);
    let currentHistory = [...history];
    // Commit the local snapshot to state WITHOUT clobbering concurrent additions
    // (e.g. a completion-card appended by an effect while this async call is in flight).
    const commitCurrentHistory = () => {
      const snapshot = [...currentHistory];
      setHistory((h) => (h.length > snapshot.length ? h : snapshot));
    };
    
    if (file) {
      currentHistory.push({ sender: 'USER', text: `[Uploading Evidence: ${file.name}...]` });
      commitCurrentHistory();
      try {
        const formData = new FormData();
        formData.append('file', file);
        const apiUrl = API_BASE;
        const res = await fetch(`${apiUrl}/api/evidence`, {
          method: 'POST',
          body: formData
        });
        if (!res.ok) throw new Error("Upload failed");
        const data = await res.json();
        
        await attachEvidence(data.evidence_id);
        
        currentHistory[currentHistory.length - 1] = { sender: 'EUREKA', text: `✓ ${file.name}\nEvidence attached` };
        commitCurrentHistory();
      } catch (e: any) {
        currentHistory[currentHistory.length - 1] = { sender: 'EUREKA', text: `ERROR uploading evidence: ${e.message}` };
        commitCurrentHistory();
        setIsWaiting(false);
        return;
      }
    }

    if (msgText.trim()) {
      currentHistory.push({ sender: 'USER', text: msgText });
      commitCurrentHistory();
    }

    // LS94: if the work is waiting for a BLOCKING INFORMATION request, feed the user's message
    // directly as the answer to that request (the chat doubles as the data input), so the
    // pipeline resumes and can produce a concrete recommendation — instead of only asking for
    // data and never advancing.
    try {
      const infoWork = useWorkStore.getState().activeWork as any;
      const workId = infoWork?.work?.workId || infoWork?.work?.work_id || infoWork?.work_id;
      const hreq = infoWork?.human_requests || [];
      const infoReq = hreq.find((h: any) => h.type === 'INFORMATION' && h.blocking && String(h.status || '').toUpperCase() === 'PENDING');
      if (workId && infoReq) {
        const apiUrl = API_BASE;
        const answer = await fetch(`${apiUrl}/api/work/${workId}/human_input`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ type: 'INFORMATION', request_id: infoReq.request_id || infoReq.id, value: msgText }),
        });
        if (answer.ok) {
          // Governed HITL contract: RECEIVED != SUFFICIENT. The backend returns the Python verdict on
          // the CONTENT of the answer; never claim the analysis continues if the data was insufficient.
          let payload: any = null;
          try { payload = await answer.json(); } catch { /* no body -> fall back to neutral text */ }
          const verdict = String(payload?.human_response_sufficiency || '').toUpperCase();
          if (verdict === 'SUFFICIENT') {
            currentHistory.push({ sender: 'EUREKA', text: '✓ Gracias — he recibido tu información y continúo el análisis.' });
          } else if (verdict) {
            currentHistory.push({ sender: 'EUREKA', text: `La información recibida no es suficiente (${verdict}). EUREKA te pedirá de nuevo, de forma concreta, los datos que siguen faltando; nada se publicará hasta recibirlos.` });
          } else {
            currentHistory.push({ sender: 'EUREKA', text: '✓ Respuesta registrada. EUREKA continúa el análisis.' });
          }
          commitCurrentHistory();
          setIsWaiting(false);
          // Refresh immediately so the UI shows the real outcome: the work resumed, or a governed
          // follow-up INFORMATION request is now pending.
          void useWorkStore.getState().pollState?.();
          return; // don't route to the copilot; the pipeline either resumes with the data or re-asks
        }
      }
    } catch (_e) { /* if the info-submit fails, fall through to the copilot */ }

    // Fresh context since activeWork might have changed (e.g., evidence added)
    const freshActiveWork = useWorkStore.getState().activeWork;
    if (!freshActiveWork) {
      setIsWaiting(false);
      return;
    }

    const narrativeStages = buildNarrativeStages(freshActiveWork);
    const narrativeHITL = findActiveHITLStage(narrativeStages);
    const narrativeSummary = narrativeStages
      .map((s) => `${s.order}.${s.shortTitle}(${s.cognitiveState})`)
      .join(' → ');

    // LS55: the Copilot now answers nested questions from the built Cognitive
    // Story + Cognitive Views (never from generic chat or invented data).
    const cognitiveNarrativeContext = buildCopilotNarrativeContext(freshActiveWork);

    const systemContext = `You are the EUREKA Cognitive Copilot. You narrate the EUREKA COGNITIVE STORY and answer nested questions from the Cognitive Views, not from generic chat.
The user intent was: ${freshActiveWork.work.userIntent}
Workspace status: ${freshActiveWork.work.status}
Active EM: ${freshActiveWork.active_em || 'None'}
Evidence files: ${freshActiveWork.evidence?.length || 0}
When the work is complete, answer the user's question with a DIGESTIBLE answer: explain the selected alternative (the prescription recommendation) and the plan / key findings in plain, human language. NEVER invent facts — only describe what the governed result says (selected alternative, rationale, action plan, validated findings). Do not dump raw output; give a concise, useful answer. If the result is not yet published, say so clearly. ALWAYS give a CONCRETE recommendation: if a human has selected an alternative, recommend that; if alternatives are listed, recommend the most suitable and explain why (final say = human); if there are NO alternatives yet and data is still being requested, STILL give a concrete INITIAL recommendation drawn from your general knowledge of what makes a system like this smarter (e.g. knowledge/context integration, adaptive learning from feedback, better grounding & evaluation, better uncertainty handling), presented clearly as suggestions, then note what additional info (the specific data points being requested) would make it more grounded. Never just say "there is no recommendation" or "give me data" — always offer a concrete path first.
WRITE LIKE A HUMAN EXPERT, NOT A SYSTEM (STRICT): Do NOT mention ANY internal ID or code (e.g. PRED-*, FND-*, AP-*, DEC-*, PRESC-*, WR-*, FROZEN-*), do NOT mention status codes/technical keywords (UNSUPPORTED, HUMAN_OPERATOR, SIMULATED, NOT_EVALUATED, VALIDATED, mse, confidence, accuracy, model names), and do NOT use jargon or internal terminology. Give a clear, natural, warm answer in plain language a non-technical reader understands. If something could not be computed because data was missing, say it simply ("estas cifras no pudieron calcularse porque faltaban datos de precisión") — NEVER cite an ID or a code. The technical trace lives in the Cognitive Story, not in this answer. State the recommendation, the reason, the plan and the outcome in everyday words.
Cognitive narrative stages: ${narrativeSummary}
${narrativeHITL ? `A human decision is currently required at stage: ${narrativeHITL.title}. Explain it and what the human must choose.` : ''}

GOVERNED RESULT (answer the question from this, never invent):
${(() => {
  const st = (freshActiveWork as any).state || {};
  const presc = st.prescriptive_knowledge?.prescriptions?.[0];
  const sel = presc?.selected_alternative;
  const ap = st.action_plan;
  const res = st.result;
  const lines: string[] = [];
  if (sel) lines.push(`Human-selected alternative: ${sel.alternative_id} — ${sel.description}`);
  const alts = (presc?.alternatives || []).map((a: any) => `${a.alternative_id}: ${a.description}`).join(' | ');
  if (alts) lines.push(`Alternatives considered: ${alts}`);
  if (presc?.rationale) lines.push(`Rationale: ${presc.rationale}`);
  if (ap?.actions?.length) lines.push(`Action plan (${ap.actions.length} steps): ${ap.actions.slice(0, 4).map((a: any) => a.description).join(' | ')}${ap.actions.length > 4 ? ' …' : ''}`);
  if (res?.summary) lines.push(`Result summary: ${res.summary}`);
  lines.push(`Result status: ${res?.status || '—'}`);
  return lines.join('\n');
})()}

${cognitiveNarrativeContext}`;

    const apiMessages: any[] = [
      { role: 'system', content: systemContext }
    ];
    
    currentHistory.forEach(msg => {
      if (msg.sender === 'USER' && !msg.text.startsWith('[Uploading')) {
        apiMessages.push({ role: 'user', content: msg.text });
      } else if (msg.sender === 'DEEPSEEK') {
        apiMessages.push({ role: 'assistant', content: msg.text });
      } else if (msg.sender === 'EUREKA') {
        apiMessages.push({ role: 'system', content: `Tool execution result: ${msg.text}` });
      } else if (msg.sender === 'TOOL_CALL') {
        apiMessages.push({ role: 'assistant', content: `I executed a tool: ${msg.text}` });
      }
    });

    const AVAILABLE_TOOLS = [
      {
        type: "function",
        function: {
          name: "retrieve_result",
          description: "Retrieves the final calculated result for the current active work.",
          parameters: { type: "object", properties: {}, required: [] }
        }
      },
      {
        type: "function",
        function: {
          name: "filter_alternatives",
          description: "Filters the available alternatives based on feasibility.",
          parameters: {
            type: "object",
            properties: {
              feasible: { type: "boolean", description: "Filter only feasible alternatives." }
            },
            required: ["feasible"]
          }
        }
      },
      {
        type: "function",
        function: {
          name: "adjust_acfl_weights",
          description: "Adjusts criteria weights for analysis, like cost or risk.",
          parameters: {
            type: "object",
            properties: {
              cost: { type: "number", description: "Weight for cost (0-100)" },
              risk: { type: "number", description: "Weight for risk (0-100)" }
            },
            required: ["cost", "risk"]
          }
        }
      },
      {
        type: "function",
        function: {
          name: "actioner",
          description: "Executes the current active decision or unfreezes the state.",
          parameters: { type: "object", properties: {}, required: [] }
        }
      },
      {
        type: "function",
        function: {
          name: "explain_claim",
          description: "Explains the current recommendation based on the evidence.",
          parameters: { type: "object", properties: {}, required: [] }
        }
      },
      {
        type: "function",
        function: {
          name: "execute_eureka",
          description: "Initiates a formal cognitive execution (8-EM pipeline) to analyze evidence, evaluate alternatives, predict outcomes, prescribe decisions, or formulate an action plan based on the user intent. USE ONLY for formal analysis requests, NOT for conversational answers.",
          parameters: {
            type: "object",
            properties: {
              intent: { type: "string", description: "The specific objective or problem statement to execute." }
            },
            required: ["intent"]
          }
        }
      }
    ];

    try {
      const response = await fetch(COPILOT_API, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: 'deepseek-chat',
          messages: apiMessages,
          temperature: 0.3,
          tools: AVAILABLE_TOOLS
        })
      });

      if (!response.ok) throw new Error(`LLM API Error: ${response.statusText}`);

      const data = await response.json();
      
      if (!data.choices || !Array.isArray(data.choices) || data.choices.length === 0) {
        throw new Error(`Invalid LLM response. Missing choices array. Details: ${JSON.stringify(data)}`);
      }
      
      const message = data.choices[0].message;

      if (message.tool_calls && message.tool_calls.length > 0) {
        apiMessages.push(message);

        for (const toolCallReq of message.tool_calls) {
          const capability = toolCallReq.function.name;
          
          let params = {};
          try {
            params = JSON.parse(toolCallReq.function.arguments || '{}');
          } catch {
            // malformed or empty tool-call arguments; fall back to an empty param object.
          }

          const allowedTools = ['retrieve_result', 'filter_alternatives', 'adjust_acfl_weights', 'actioner', 'explain_claim', 'execute_eureka'];
          
          let replyText = '';
          if (!allowedTools.includes(capability)) {
            replyText = `EUREKA: GOVERNANCE BLOCK.\nExecution of [${capability}] rejected. Tool unknown.`;
            currentHistory.push({ sender: 'EUREKA', text: replyText });
          } else if (capability === "execute_eureka") {
            currentHistory.push({ sender: 'TOOL_CALL', text: `Executing tool ${capability} with params ${JSON.stringify(params)}` });
            commitCurrentHistory();

            const executeWork = useWorkStore.getState().executeWork;
            if (!executeWork) {
               replyText = "SYSTEM ERROR. Reason: executeWork not implemented in store.";
            } else {
               const res = await executeWork((params as any).intent);
               if (res?.status === "SUCCESS") {
                 replyText = `APPROVED. Runtime initiated cognitive execution. Work ID: ${res.work_id}. Initial Status: ${res.state_status}. Polling will now observe the 8-EM pipeline.`;
               } else {
                 replyText = `SYSTEM ERROR. Reason: ${res?.reason_code}`;
               }
            }
            currentHistory.push({ sender: 'EUREKA', text: `Tool Result: ${replyText}` });
          } else {
            currentHistory.push({ sender: 'TOOL_CALL', text: `Executing tool ${capability} with params ${JSON.stringify(params)}` });
            commitCurrentHistory();

            const res = await toolCall(capability, params);
            
            if (res?.status === "SUCCESS") {
              replyText = `APPROVED. Runtime executed capability [${capability}].`;
            } else if (res?.status === "ERROR") {
              replyText = `SYSTEM ERROR. Reason: ${res.reason_code}`;
            } else if (res?.status === "GAP") {
              replyText = `CAPABILITY GAP. Reason: ${res.reason_code}. Capability [${capability}] is unavailable in the Canonical State.`;
            } else if (res?.status === "BLOCKED") {
              replyText = `GOVERNANCE BLOCK. Reason: ${res.reason_code}. Execution of [${capability}] requires higher authority.`;
            } else if (res?.status === "PARTIAL") {
              replyText = `PARTIAL - EVIDENCE REQUIRED. Reason: ${res.reason_code}. Capability [${capability}] missing prerequisites.`;
            } else if (res?.status === "CONTRACT_ERROR") {
              replyText = `CONTRACT ERROR. Reason: ${res.reason_code}. The CanonicalWorkState boundary validation failed.`;
            } else {
              replyText = `UNKNOWN RESPONSE.`;
            }
            
            currentHistory.push({ sender: 'EUREKA', text: `Tool Result: ${replyText}` });
          }
          
          apiMessages.push({
            role: 'tool',
            tool_call_id: toolCallReq.id,
            content: replyText
          });
        }
        
        commitCurrentHistory();

        const secondResponse = await fetch(COPILOT_API, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            model: 'deepseek-chat',
            messages: apiMessages,
            temperature: 0.3
          })
        });

        const secondData = await secondResponse.json();
        
        if (!secondData.choices || !Array.isArray(secondData.choices) || secondData.choices.length === 0) {
          throw new Error(`Invalid LLM response on second turn. Missing choices array. Details: ${JSON.stringify(secondData)}`);
        }
        
        currentHistory.push({ sender: 'DEEPSEEK', text: sanitizeDsml(secondData.choices[0].message.content), reasoning: secondData.choices[0].message.reasoning_content, usage: secondData.usage });
        commitCurrentHistory();

      } else {
        currentHistory.push({ sender: 'DEEPSEEK', text: sanitizeDsml(message.content), reasoning: message.reasoning_content, usage: data.usage });
        commitCurrentHistory();
      }
    } catch (e: any) {
      console.error(e);
      currentHistory.push({ sender: 'EUREKA', text: `COPILOT ERROR: No se pudo contactar al proveedor LLM. Razón: ${e.message}` });
      commitCurrentHistory();
    }
    
    setIsWaiting(false);
  };

  // LS95: when the 8-EM pipeline publishes a result (work -> COMPLETED), the chat must
  // show a CONCRETE answer in plain human language — not just a status card. This narrates
  // the governed result as a normal chat bubble; the technical trace lives in the Cognitive
  // Story. It runs WITHOUT tools (plain completion), so it can never re-execute the pipeline.
  const narrateCompletion = async () => {
    const stripId = (s: string) => String(s || '').replace(/\b[A-Z]{2,3}-\d+\b/g, '').trim();
    try {
      const fresh = useWorkStore.getState().activeWork as any;
      if (!fresh || fresh?.work?.status !== 'COMPLETED') return;
      const st = fresh.state || {};
      const presc = st.prescriptive_knowledge?.prescriptions?.[0];
      const sel = presc?.selected_alternative;
      const ap = st.action_plan;
      const res = st.result;
      const alts = (presc?.alternatives || []).map((a: any) => `${stripId(a.alternative_id)}: ${a.description}`).join(' | ');

      const governed = [
        sel ? `Alternativa elegida: ${sel.description}` : null,
        alts ? `Alternativas consideradas: ${alts}` : null,
        presc?.rationale ? `Justificación: ${presc.rationale}` : null,
        ap?.actions?.length ? `Plan de acción (${ap.actions.length} pasos): ${ap.actions.slice(0, 5).map((a: any) => a.description).join(' | ')}${ap.actions.length > 5 ? '…' : ''}` : null,
        res?.summary ? `Resultado: ${res.summary}` : null,
      ].filter(Boolean).join('\n');

      const system = `Eres el Copiloto Cognitivo de EUREKA. El análisis con el pipeline de 8 EM ha FINALIZADO y el resultado está publicado. Da al usuario una respuesta CONCRETA, clara y cálida, en lenguaje humano y en español. Explica la recomendación / alternativa elegida, por qué se eligió, el plan de acción y el resultado obtenido, y propón un siguiente paso práctico.
REGLAS ESTRICTAS: NO menciones ningún ID ni código interno (nada de PRED-*, AP-*, DEC-*, PRESC-*, WR-*, FROZEN-*), no uses jerga técnica ni términos en mayúsculas (UNSUPPORTED, NOT_EVALUATED, VALIDATED, mse, confidence, accuracy, nombres de modelos). Habla como un experto cercano y no técnico. Si algo no pudo calcularse, dilo de forma sencilla y sin códigos.
Intención del usuario: ${fresh.work.userIntent}
RESULTADO GOBERNADO (responde SOLO desde esto, no inventes):
${governed}`;

      const response = await fetch(COPILOT_API, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: 'deepseek-chat',
          messages: [
            { role: 'system', content: system },
            { role: 'user', content: fresh.work.userIntent },
          ],
          temperature: 0.3,
        }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      const text = sanitizeDsml(data.choices?.[0]?.message?.content || '');
      if (!text) throw new Error('LLM returned empty content');
      setHistory((h) => [...h, { sender: 'DEEPSEEK', text, usage: data.usage }]);
      return;
    } catch (_e) {
      // Deterministic fallback: the chat is never left without a concrete answer.
      const fresh = useWorkStore.getState().activeWork as any;
      const st = fresh?.state || {};
      const presc = st.prescriptive_knowledge?.prescriptions?.[0];
      const sel = presc?.selected_alternative;
      const ap = st.action_plan;
      const res = st.result;
      const parts: string[] = [];
      parts.push('El análisis ha terminado y aquí está la respuesta concreta:');
      parts.push('');
      if (sel?.description) parts.push(`Recomendación: ${stripId(sel.description)}`);
      else if (res?.summary) parts.push(`Resultado: ${stripId(res.summary)}`);
      else parts.push('Se completó el análisis y se publicó un resultado.');
      if (presc?.rationale) parts.push(`Motivo: ${stripId(presc.rationale)}`);
      if (ap?.actions?.length) parts.push(`Plan de acción (${ap.actions.length} pasos): ${ap.actions.slice(0, 5).map((a: any) => stripId(a.description)).join(' | ')}${ap.actions.length > 5 ? '…' : ''}`);
      setHistory((h) => [...h, { sender: 'DEEPSEEK', text: parts.join('\n') }]);
    }
  };

  const handleChatSubmit = () => {
    if (isWaiting) return;
    submitMessage(input, selectedFile);
    setInput('');
    setSelectedFile(null);
  };

  // LS95: narrate the FINAL concrete answer the moment the work transitions to COMPLETED.
  // The first render only records the current status (so a pre-completed work on reload is
  // answered by the mount auto-submit, which already sees the governed result) — it never
  // narrates twice.
  React.useEffect(() => {
    const status = (activeWork as any)?.work?.status;
    if (isFirstRenderRef.current) {
      isFirstRenderRef.current = false;
      prevStatusRef.current = status;
      return;
    }
    const prev = prevStatusRef.current;
    prevStatusRef.current = status;
    if (status === 'COMPLETED' && prev !== 'COMPLETED' && !completedNarratedRef.current) {
      completedNarratedRef.current = true;
      narrateCompletion();
    }
  }, [(activeWork as any)?.work?.status]);

  React.useEffect(() => {
    if (activeWork && history.length === 0 && !isWaiting && !hasInitializedRef.current) {
      hasInitializedRef.current = true;
      submitMessage(activeWork.work.userIntent, null);
    }
  }, [activeWork, history.length, isWaiting]);

  // Completion is shown by a persistent inline card (robust, no race). It appears when the
  // work is COMPLETED AND there is no follow-up user message yet (so it does not duplicate).

  // LS55: a "ASK THE COPILOT" dispatch from any Cognitive View submits the
  // chapter question to the narrator.
  React.useEffect(() => {
    const handler = (ev: Event) => {
      const q = (ev as CustomEvent).detail?.question;
      if (q && !isWaiting) {
        hasInitializedRef.current = true;
        submitMessage(String(q), null);
      }
    };
    window.addEventListener('eureka:ask-copilot', handler);
    return () => window.removeEventListener('eureka:ask-copilot', handler);
  }, [isWaiting]);

  return (
    <div className="flex flex-col h-full bg-[var(--eureka-canvas)]">
      <div className="flex-1 min-h-0 px-[9%] py-4 overflow-y-auto overflow-x-hidden space-y-3">
        {activeWork && (
          <div className="flex justify-end">
            <div className="max-w-[85%] rounded-2xl bg-[#ddf4ff] px-4 py-3 text-sm text-[var(--eureka-text-display)] break-words whitespace-pre-wrap">{activeWork.work.userIntent}</div>
          </div>
        )}

        {history.map((msg, idx) => {
          if (idx === 0 && msg.sender === 'USER' && msg.text === activeWork?.work?.userIntent) {
            return null;
          }
          // No mostrar los tool-calls / tool-results internos dentro del chat.
          if (msg.sender === 'TOOL_CALL' || msg.sender === 'EUREKA') {
            return null;
          }
          if (msg.sender === 'USER') {
            return (
              <div key={idx} className="flex justify-end">
                <div className="max-w-[85%] rounded-2xl bg-[#ddf4ff] px-4 py-3 text-sm text-[var(--eureka-text-display)] break-words whitespace-pre-wrap">{msg.text}</div>
              </div>
            );
          }
          const label = msg.sender === 'DEEPSEEK' ? 'EUREKA' : msg.sender === 'TOOL_CALL' ? 'Tool call' : msg.sender === 'EUREKA' ? 'EUREKA' : msg.sender;
          const isTool = msg.sender === 'TOOL_CALL' || msg.sender === 'EUREKA';
          const accent = msg.sender === 'DEEPSEEK' ? 'var(--eureka-signal-cognitive)' : 'var(--eureka-signal-authority)';
          const reasoning = (msg as any).reasoning as string | undefined;
          const usage = (msg as any).usage as { prompt_tokens?: number; completion_tokens?: number; total_tokens?: number } | undefined;
          const isOpen = !!openReasoning[idx];
          return (
            <div key={idx} className="group">
              <div className="mb-1">
                <span className="text-[10px] uppercase tracking-wider font-mono" style={{ color: accent }}>{label}</span>
              </div>

              {/* Bloque "Think" colapsable (razonamiento del modelo) */}
              {reasoning ? (
                <div className="mb-1">
                  <button
                    onClick={() => setOpenReasoning((s) => ({ ...s, [idx]: !s[idx] }))}
                    className="flex items-center gap-1.5 text-[10px] text-[var(--eureka-text-micro)] hover:text-[var(--eureka-text-display)] transition-colors"
                  >
                    <span className="text-[var(--eureka-signal-semantic)]">🔍</span>
                    <span className="uppercase tracking-wider">Think</span>
                    <span>{isOpen ? '▾' : '▸'}</span>
                  </button>
                  {isOpen && (
                    <div className="mt-1 text-xs text-[var(--eureka-text-label)] bg-[var(--eureka-surface-elevated)] rounded-md p-2 border-l-2 border-[var(--eureka-signal-semantic)] whitespace-pre-wrap font-mono">
                      {reasoning}
                    </div>
                  )}
                </div>
              ) : null}

              {isTool ? (
                <div className="flex items-start gap-2 rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-2">
                  <span className="text-[var(--eureka-signal-authority)]">🔧</span>
                  <div className="text-sm font-mono text-[var(--eureka-text-section)] break-words overflow-x-hidden whitespace-pre-wrap">{msg.text}</div>
                </div>
              ) : (
                <Markdown>{msg.text}</Markdown>
              )}

              {/* Footer: copiar + StatsLine */}
              <div className="mt-2 flex items-center gap-3">
                <button
                  onClick={() => navigator.clipboard?.writeText(msg.text)}
                  className="flex items-center gap-1 text-sm text-[var(--eureka-text-label)] hover:text-[var(--eureka-text-display)] transition-colors"
                  title="Copiar respuesta"
                >⧉ Copiar</button>
                {usage && (
                  <span className="text-xs text-[var(--eureka-text-label)] font-mono">
                    ↳ {usage.prompt_tokens ?? 0} prompt · {usage.completion_tokens ?? 0} completion · {usage.total_tokens ?? 0} tokens
                  </span>
                )}
              </div>
            </div>
          );
        })}
        {/* La decisión humana (HITL) se pide DENTRO del chat (imagen 4) */}
        <HITLDecisionWidget />
        {isWaiting && (
          <div className="text-[10px] text-[var(--eureka-signal-cognitive)] animate-pulse">PROCESSING...</div>
        )}
        {/* Aviso de finalización (persistente) — SOLO cuando COMPLETED y SIN follow-up (no duplica) */}
        {(() => {
          const userCount = history.filter((m) => m.sender === 'USER').length;
          const hasFollowUp = userCount > 1;
          if ((activeWork as any)?.work?.status === 'COMPLETED' && !hasFollowUp) {
            return (
              <div data-executive-cognitive-answer className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface)] p-4 flex items-center justify-between gap-3 flex-wrap">
                <div className="text-[11px] font-mono uppercase tracking-wider text-[var(--eureka-text-label)]">
                  ✓ Análisis completado · resultado disponible
                </div>
                <button
                  onClick={() => {
                    const focus: CognitiveFocus = dto.actionPlan?.id ? 'ACTION' : dto.result?.id ? 'RESULT' : 'DECISION';
                    (onExploreCognitiveStory ?? ((_f: CognitiveFocus) => {}))(focus);
                  }}
                  className="px-3 py-1.5 rounded border border-[var(--eureka-signal-cognitive)] text-[var(--eureka-signal-cognitive)] text-[11px] font-bold hover:bg-[var(--eureka-surface-active)] transition-colors"
                >
                  EXPLORAR LA TRAZA GOBERNADA →
                </button>
              </div>
            );
          }
          return null;
        })()}
      </div>

      <div className="px-[9%] py-3">
        {selectedFile && (
          <div className="flex justify-between items-center p-2 mb-2 bg-[var(--eureka-surface-elevated)] border border-[var(--eureka-spatial-hairline)] rounded-xl text-xs text-[var(--eureka-text-section)]">
            <span>📎 {selectedFile.name} ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)</span>
            <button onClick={() => setSelectedFile(null)} disabled={isWaiting} className="text-red-500 hover:text-red-400 font-bold px-2 disabled:opacity-50">X</button>
          </div>
        )}
        <div className="flex items-center gap-3 bg-[var(--eureka-surface-elevated)] border border-[var(--eureka-spatial-hairline)] rounded-full px-5 py-4 shadow-[0_1px_2px_rgba(0,0,0,0.04),0_8px_20px_-6px_rgba(0,0,0,0.10)]">
          <input type="file" ref={fileInputRef} className="hidden" onChange={(e) => { if (e.target.files && e.target.files.length > 0) setSelectedFile(e.target.files[0]); }} />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isWaiting}
            className="w-11 h-11 shrink-0 flex items-center justify-center rounded-full bg-[var(--eureka-surface-active)] text-[var(--eureka-text-label)] hover:text-[var(--eureka-text-display)] transition-colors disabled:opacity-50"
            title="Adjuntar"
          >
            ＋
          </button>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleChatSubmit()}
            disabled={isWaiting}
            placeholder="Message the agent"
            className="flex-1 bg-transparent text-base text-[var(--eureka-text-section)] focus:outline-none disabled:opacity-50"
          />
          <button
            onClick={handleChatSubmit}
            disabled={isWaiting || (!input.trim() && !selectedFile)}
            className="w-11 h-11 shrink-0 flex items-center justify-center rounded-full bg-[var(--eureka-signal-cognitive)] text-white disabled:opacity-50 hover:opacity-90 transition-opacity"
            title="Enviar"
          >
            ↑
          </button>
        </div>
        <div className="flex items-center mt-1.5 px-1">
          <span className="text-[10px] text-[var(--eureka-signal-cognitive)]">{isWaiting ? 'PROCESSING...' : ''}</span>
        </div>
      </div>
    </div>
  );
}
