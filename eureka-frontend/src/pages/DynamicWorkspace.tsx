import React, { useRef, useEffect, useState } from 'react';
import { useWorkStore } from '../store/workStore';
import { useUIStore } from '../store/uiStore';
import DeepSeekCopilot from '../components/DeepSeekCopilot';
import CompensationSurface from '../components/visualizations/CompensationSurface';
import IntelligenceNetwork from '../components/visualizations/IntelligenceNetwork';
import CognitiveStoryTab from '../components/cognitive/CognitiveStoryTab';
import CognitiveConstellation from '../components/cognitive/CognitiveConstellation';
import CognitiveTimeline from '../components/story/cognitiveViews/CognitiveTimeline';
import RuntimeTrace from '../components/RuntimeTrace';
import EMOperationalPipeline from '../components/runtime/EMOperationalPipeline';
import HITLDecisionWidget from '../components/HITLDecisionWidget';
import EvolutionHITLWidget from '../components/EvolutionHITLWidget';
import { API_BASE } from '../lib/apiBase';

type TabId = 'chat' | 'trajectory' | 'cognition' | 'constellation' | 'evidence' | 'surfaces' | 'evolution';

const TABS: { id: TabId; label: string }[] = [
  { id: 'chat', label: 'Chat' },
  { id: 'trajectory', label: 'Trajectory' },
  { id: 'cognition', label: 'EUREKA COGNITIVE STORY' },
  { id: 'constellation', label: 'Constelación' },
  { id: 'evidence', label: 'Evidence' },
  { id: 'surfaces', label: 'Decision Surfaces' },
  { id: 'evolution', label: 'Evolución' },
];

const TAB_KEY = 'eureka.activeTab';

function num(v: any): number | null {
  const n = typeof v === 'number' ? v : Number(v);
  return Number.isFinite(n) ? n : null;
}
function meanScore(sv: any): number | null {
  if (sv == null) return null;
  if (typeof sv === 'number') return sv;
  if (typeof sv === 'object' && !Array.isArray(sv)) {
    const vals = Object.values(sv).map(num).filter((x): x is number => x != null);
    return vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null;
  }
  return null;
}

export default function DynamicWorkspace() {
  const activeWork = useWorkStore((state) => state.activeWork);
  const clearWork = useWorkStore((state) => state.clearWork);
  const attachEvidence = useWorkStore((state) => state.attachEvidence);
  const pollState = useWorkStore((state) => state.pollState);
  const [tab, setTabState] = useState<TabId>(() => {
    const saved = localStorage.getItem(TAB_KEY) as TabId | null;
    return saved && TABS.some((t) => t.id === saved) ? saved : 'chat';
  });
  const [statusMsg, setStatusMsg] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const setTab = (id: TabId) => {
    setTabState(id);
    localStorage.setItem(TAB_KEY, id);
  };

  // §20 — bridge: Chat (COMPLETED / Executive Answer) → Cognitive Story, deep-linked
  // to the RELEVANT chapter (ACTION / RESULT / DECISION).
  const openCognitiveStory = (chapter: 'DECISION' | 'ACTION' | 'RESULT' = 'DECISION') => {
    useUIStore.getState().requestCognitiveFocus(chapter);
    setTab('cognition');
  };

  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;
    const pollable = ['RUNNING', 'READY', 'WAITING_FOR_HUMAN_INPUT', 'WAITING_FOR_EVIDENCE'];
    if (activeWork && pollable.includes(activeWork.work.status)) {
      interval = setInterval(() => {
        pollState();
      }, 500);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [activeWork?.work.status, pollState]);

  if (!activeWork) return null;

  const uploadEvidence = async (file: File) => {
    setStatusMsg('Uploading evidence...');
    try {
      const apiUrl = API_BASE;
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch(`${apiUrl}/api/evidence`, { method: 'POST', body: formData });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      await attachEvidence(data.evidence_id);
      setStatusMsg(`Evidence attached: ${file.name} (${data.evidence_id})`);
    } catch (e: any) {
      setStatusMsg(`ERROR uploading: ${e.message}`);
    }
  };

  // Download the published work as a real artifact (txt/md/docx/pdf/pptx/png/svg).
  const downloadArtifact = async (fmt: string) => {
    const apiUrl = API_BASE;
    const workId = (activeWork as any)?.work?.workId
      || (activeWork as any)?.work?.work_id
      || (activeWork as any)?.work_id;
    if (!workId) {
      setStatusMsg('ERROR: no work id for export');
      return;
    }
    setStatusMsg(`Exporting ${fmt.toUpperCase()}...`);
    try {
      const res = await fetch(`${apiUrl}/api/work/${workId}/download?format=${encodeURIComponent(fmt)}`);
      if (!res.ok) {
        const err = await res.text();
        throw new Error(`HTTP ${res.status}: ${err}`);
      }
      const blob = await res.blob();
      const filename = (res.headers.get('content-disposition') || '').match(/filename="?([^";]+)"?/i)?.[1]
        || `EUREKA_${workId}.${fmt}`;
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setStatusMsg(`Exported ${filename}`);
    } catch (e: any) {
      setStatusMsg(`ERROR exporting ${fmt}: ${e.message}`);
    }
  };

  const EXPORT_FORMATS = [
    { id: 'txt', label: 'TXT' },
    { id: 'md', label: 'MD' },
    { id: 'docx', label: 'DOCX' },
    { id: 'pdf', label: 'PDF' },
    { id: 'pptx', label: 'PPTX' },
    { id: 'png', label: 'PNG' },
    { id: 'svg', label: 'SVG' },
  ];

  const renderExportBar = () => (
    <div className="flex flex-wrap items-center gap-2 mb-4">
      <span className="text-[11px] font-mono uppercase tracking-widest text-[var(--eureka-text-label)] mr-1">Exportar</span>
      {EXPORT_FORMATS.map((f) => (
        <button
          key={f.id}
          onClick={() => downloadArtifact(f.id)}
          className="px-3 py-1.5 text-[11px] font-mono uppercase tracking-wider rounded border border-[var(--eureka-signal-cognitive)]/40 text-[var(--eureka-signal-cognitive)] hover:bg-[var(--eureka-signal-cognitive)] hover:text-white transition-colors"
        >
          {f.label}
        </button>
      ))}
    </div>
  );

  const renderSurfaces = () => {
    return (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 auto-rows-[350px]">
        {activeWork.visualizations.map((viz, idx) => {
          if (viz.id === 'Inspector') return null;
          if (viz.status === 'GAP' || viz.status === 'UNAVAILABLE') {
            return (
              <div key={idx} className="fabric-panel p-6 flex flex-col justify-center items-center text-center bg-[var(--eureka-surface-elevated)] border-[var(--eureka-signal-blocked)] border-dashed">
                <div className="text-[var(--eureka-signal-blocked)] text-sm mb-2">{viz.status}</div>
                <h4 className="text-[var(--eureka-text-display)] text-lg mb-1">{viz.id}</h4>
                <p className="text-[var(--eureka-text-label)] text-xs">{viz.reason || 'Missing required capability or data'}</p>
              </div>
            );
          }
          switch (viz.id) {
            case 'Compensation Surface': {
              const _acfl = activeWork.state?.acfl || {};
              const _hasAcfl = (_acfl.frontier && _acfl.frontier.length > 0) || Object.keys(_acfl.weights || {}).length > 0;
              if (!_hasAcfl) {
                return (
                  <div key={idx} className="fabric-panel p-6 flex flex-col justify-center items-center text-center bg-[var(--eureka-surface-elevated)] border-[var(--eureka-signal-blocked)] border-dashed">
                    <div className="text-[var(--eureka-signal-blocked)] text-sm mb-2">UNAVAILABLE</div>
                    <h4 className="text-[var(--eureka-text-display)] text-lg mb-1">{viz.id}</h4>
                    <p className="text-[var(--eureka-text-label)] text-xs">ACFL FRONTIER DATA UNAVAILABLE</p>
                  </div>
                );
              }
              return <CompensationSurface key={idx} />;
            }
            case 'Intelligence Network':
              return <IntelligenceNetwork key={idx} />;
            default: {
              // Differentiate the surface by id: Scientific=metrics, Decision=alternatives+scoring, Phase=feasibility.
              const _w = activeWork.state?.acfl?.weights || {};
              const _al = activeWork.state?.acfl?.alternatives || [];
              const _sc = activeWork.state?.acfl?.normalized_scores || {};
              const _dopts: any[] = (activeWork.decision_points || []).flatMap((dp: any) => dp.options || []);
              const _metrics = (activeWork as any).scientific_metrics || null;
              const wEnts = Object.entries(_w);
              const altIds = [...new Set([..._al.map((a: any) => a.alternative_id || a.id), ..._dopts.map((o: any) => o.id)])].filter(Boolean);
              const which = viz.id;
              const title = which === 'Scientific Surface' ? 'Scientific metrics' : which === 'Decision Field' ? 'Alternatives & scoring' : 'Feasibility / phase space';
              return (
                <div key={idx} className="fabric-panel p-6 flex flex-col border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface)]">
                  <h3 className="text-xs font-bold text-[var(--eureka-text-display)] mb-4 uppercase">{viz.id}</h3>
                  {which === 'Decision Field' && altIds.length > 0 ? (
                    <div className="space-y-2 text-xs">
                      {altIds.map((id: any) => {
                        const s = meanScore((_sc as any)[id]);
                        return (
                          <div key={id} className="flex items-center justify-between border border-[var(--eureka-spatial-hairline)] rounded px-3 py-2">
                            <span className="font-mono text-[var(--eureka-signal-cognitive)]">{id}</span>
                            <span className={`font-mono ${s != null ? 'text-[var(--eureka-text-metric)]' : 'text-[var(--eureka-text-micro)]'}`}>
                              {s != null ? `${s.toFixed(2)} / 1.00` : 'no score'}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  ) : which === 'Scientific Surface' && _metrics ? (
                    <p className="text-xs text-[var(--eureka-text-label)]">Scientific metrics available (surface pending metric detail).</p>
                  ) : which === 'Phase Space' ? (
                    <div className="space-y-2 text-xs">
                      <p className="text-[10px] uppercase text-[var(--eureka-text-label)]">Feasibility</p>
                      <div className="flex items-center justify-between">
                        <span className="text-[var(--eureka-text-section)]">Feasible only</span>
                        <span className={`font-mono ${activeWork.state?.feasible_only ? 'text-[var(--eureka-signal-action)]' : 'text-[var(--eureka-text-label)]'}`}>
                          {activeWork.state?.feasible_only ? 'ACTIVE' : 'OFF'}
                        </span>
                      </div>
                      {wEnts.length > 0 && (
                        <div className="flex flex-wrap gap-2 mt-2">{wEnts.map(([k, v]) => (<span key={k} className="bg-[var(--eureka-surface-elevated)] border border-[var(--eureka-spatial-hairline)] px-2 py-1 rounded">{k}: {String(v)}</span>))}</div>
                      )}
                    </div>
                  ) : (
                    <div className="space-y-3 text-xs">
                      {wEnts.length > 0 && (
                        <div><p className="text-[10px] uppercase text-[var(--eureka-text-label)] mb-1">ACFL weights</p><div className="flex flex-wrap gap-2">{wEnts.map(([k, v]) => (<span key={k} className="bg-[var(--eureka-surface-elevated)] border border-[var(--eureka-spatial-hairline)] px-2 py-1 rounded">{k}: {String(v)}</span>))}</div></div>
                      )}
                      {altIds.length > 0 && (<div><p className="text-[10px] uppercase text-[var(--eureka-text-label)] mb-1">Alternatives ({altIds.length})</p><div className="flex flex-wrap gap-2">{altIds.map((id: any) => (<span key={id} className="bg-[var(--eureka-surface-elevated)] border border-[var(--eureka-spatial-hairline)] px-2 py-1 rounded">{id}</span>))}</div></div>)}
                      {_metrics && (<p className="text-[var(--eureka-text-label)]">Scientific metrics available.</p>)}
                    </div>
                  )}
                </div>
              );
            }
          }
        })}
      </div>
    );
  };

  const renderDetailBlock = (label: string, content: React.ReactNode) => (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-1">{label}</div>
      <div className="text-[11px] text-[var(--eureka-text-section)]">{content}</div>
    </div>
  );

  const renderResult = () => {
    const res = activeWork.state.result;
    const pub = (activeWork as any).publication_state;
    const exec = (activeWork as any).execution_state;
    const frozen = (activeWork as any).frozen_result;
    const dps = (activeWork as any).decision_points || [];
    const ap = (activeWork as any).action_plan;
    if (!res) {
      return (
        <div className="fabric-panel p-6 bg-[var(--eureka-surface)] border border-[var(--eureka-spatial-hairline)] flex flex-col items-center justify-center h-40">
          <div className="text-sm text-[var(--eureka-text-label)]">The final result will appear here once the pipeline publishes.</div>
        </div>
      );
    }
    return (
      <div className="space-y-6">
        <div className="fabric-panel p-6 bg-[var(--eureka-surface)] border border-[var(--eureka-spatial-hairline)]">
          <h3 className="text-xs font-bold text-[var(--eureka-text-display)] mb-4 tracking-widest uppercase">WORK RESULT</h3>
          {renderExportBar()}
          <div className="space-y-6">
            {renderDetailBlock('Status', <span className={`font-bold uppercase ${res.status === 'AVAILABLE' ? 'text-[var(--eureka-signal-action)]' : 'text-[var(--eureka-signal-blocked)]'}`}>{res.status || '—'}</span>)}
            <div className="border-b border-[var(--eureka-spatial-hairline)] pb-5">
              {renderDetailBlock('Resumen', res.summary ? <div className="whitespace-pre-wrap text-[var(--eureka-text-display)]">{res.summary}</div> : <span className="text-[var(--eureka-text-micro)]">—</span>)}
            </div>
            {/* METADATA — compact aligned grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {renderDetailBlock('Result id', res.result_id || '—')}
              {renderDetailBlock('Publication', pub?.status || '—')}
              {renderDetailBlock('Execution', `${exec?.status || '—'}${exec?.result?.status ? ` · ${exec.result.status}` : ''}`)}
              {frozen?.status ? renderDetailBlock('Frozen result', `${frozen.result_id || ''} · ${frozen.status}`) : null}
              {ap ? renderDetailBlock('Action plan', `${ap.plan_id || ''} · ${(ap.actions || []).length} actions`) : null}
              {res.confidence != null ? renderDetailBlock('Confidence', String(res.confidence)) : null}
              {(res.gaps || []).length > 0 ? renderDetailBlock('Gaps', <ul className="list-disc pl-5 space-y-1 text-[var(--eureka-signal-blocked)]">{res.gaps.map((g: string, i: number) => <li key={i}>{g}</li>)}</ul>) : null}
            </div>
            {/* SOURCES / PROVENANCE */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {renderDetailBlock('Sources', (res.evidence_ids || []).length ? <ul className="font-mono text-[var(--eureka-text-section)] space-y-1">{res.evidence_ids.map((e: string, i: number) => <li key={i}>{e}</li>)}</ul> : <span className="text-[var(--eureka-text-micro)]">No direct source referenced</span>)}
              {renderDetailBlock('Provenance', (res.provenance || []).length ? <ul className="space-y-1 border-l-2 border-[var(--eureka-spatial-hairline)] pl-3 font-mono text-[var(--eureka-text-section)]">{res.provenance.map((on: string, i: number) => <li key={i} className="flex gap-2"><span className="text-[var(--eureka-signal-semantic)]">→</span>{on}</li>)}</ul> : <span className="text-[var(--eureka-text-micro)]">No provenance established</span>)}
            </div>
            {(dps.length > 0) && (
              <div>{renderDetailBlock('Human decisions', <ul className="space-y-1">{dps.map((d: any, i: number) => <li key={i} className="flex gap-2 text-[var(--eureka-text-section)]"><span className="font-mono">{d.decision_id}</span><span className="text-[var(--eureka-text-micro)]">{d.originating_em} · {d.status}</span><span className="text-[var(--eureka-signal-action)]">{d.human_selection || ''}</span></li>)}</ul>)}</div>
            )}
            {/* PROPUESTA DETALLADA — full width, always rendered (sections if present,
                else a truthful fallback composed from the real canonical data) */}
            {(() => {
              const rawSections = (pub?.publications || []).flatMap((pp: any) => (pp.sections || []).map((s: any) => ({ section_type: s.section_type || 'SECTION', content: s.content })));
              const fallback: { section_type: string; content: string }[] = [];
              if (res.summary) fallback.push({ section_type: 'SUMMARY', content: res.summary });
              if ((res.findings || []).length) fallback.push({ section_type: 'FINDINGS', content: (res.findings as string[]).join('\n') });
              if ((res.recommendations || []).length) fallback.push({ section_type: 'RECOMMENDATIONS', content: (res.recommendations as string[]).join('\n') });
              if (res.calculations && Object.keys(res.calculations).length) fallback.push({ section_type: 'CALCULATIONS', content: Object.entries(res.calculations).map(([k, v]) => `${k}: ${v}`).join('\n') });
              if (ap) fallback.push({ section_type: 'ACTION_PLAN', content: `${ap.plan_id || 'AP'} · ${(ap.actions || []).length} acciones` });
              const selected = (dps as any[]).find((d: any) => d.human_selection)?.human_selection;
              if (selected) fallback.push({ section_type: 'DECISION', content: `Alternativa seleccionada por humano: ${selected}` });
              if (exec?.result?.status) fallback.push({ section_type: 'EXECUTION_RESULT', content: `Estado de ejecución: ${exec.result.status}` });
              const sections = rawSections.length ? rawSections : fallback;
              if (!sections.length) return null;
              return (
                <div className="border-t border-[var(--eureka-spatial-hairline)] pt-4">
                  <div className="text-xs font-bold uppercase tracking-widest text-[var(--eureka-text-display)] mb-3">Propuesta detallada</div>
                  <div className="space-y-4">
                    {sections.map((sec: any, si: number) => (
                      <div key={si}>
                        <div className="text-[11px] font-bold uppercase tracking-widest text-[var(--eureka-signal-cognitive)] mb-1">{sec.section_type || 'SECTION'}</div>
                        <div className="text-sm text-[var(--eureka-text-display)] whitespace-pre-wrap leading-relaxed pl-3 border-l-2 border-[var(--eureka-spatial-hairline)]">{sec.content}</div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })()}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="flex h-screen bg-[var(--eureka-canvas)] text-[var(--eureka-text-section)] overflow-hidden">
      <RuntimeTrace />
      <div className="flex-1 flex flex-col">
        {/* Top: flujo de los 8 EM (pipeline) */}
        <div className="border-b border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface)]">
          <EMOperationalPipeline state={activeWork} />
        </div>

        <div className="flex gap-1 px-6 border-b border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface)] overflow-x-auto">
          {TABS.map((t) => (
            <button key={t.id} onClick={() => setTab(t.id)}
              className={`px-3 py-3 text-[11px] font-mono uppercase tracking-wider border-b-2 whitespace-nowrap transition-colors ${tab === t.id ? 'border-[var(--eureka-signal-cognitive)] text-[var(--eureka-text-display)]' : 'border-transparent text-[var(--eureka-text-label)] hover:text-[var(--eureka-text-section)]'}`}>
              {t.label}
            </button>
          ))}
        </div>

        <div className={"flex-1 min-h-0 " + (tab === 'chat' ? 'overflow-hidden' : 'overflow-auto p-6')}>
          {activeWork.work.status === 'CONTRACT_ERROR' ? (
            <div className="flex flex-col items-center justify-center h-full space-y-6">
              <div className="text-center space-y-2"><h2 className="text-3xl text-purple-500 font-light">CONTRACT ERROR</h2><p className="text-[var(--eureka-text-label)]">FRONTEND-BACKEND STATE VALIDATION FAILED</p></div>
              <div className="fabric-panel p-6 bg-[var(--eureka-surface-elevated)] border-purple-500 max-w-2xl w-full">
                <p className="text-sm text-purple-300 break-words">{activeWork.conditions?.find((c) => c.status === 'CONTRACT_ERROR')?.message || 'Unknown Validation Error'}</p>
                <p className="text-xs text-[var(--eureka-text-technical)] mt-4">The API payload did not match the CanonicalWorkStateSchema.</p>
              </div>
            </div>
          ) : activeWork.work.status === 'BLOCKED' ? (
            <div className="flex flex-col items-center justify-center h-full space-y-6">
              <div className="text-center space-y-2"><h2 className="text-3xl text-[var(--eureka-signal-blocked)] font-light">WORK BLOCKED</h2><p className="text-[var(--eureka-text-label)]">EUREKA LACKS ALL REQUIRED CAPABILITIES FOR THIS PROBLEM</p></div>
              <div className="fabric-panel p-6 bg-[var(--eureka-surface-elevated)] border-[var(--eureka-signal-blocked)]"><p className="text-sm">Gaps detected: {activeWork.gaps.join(', ')}</p></div>
            </div>
          ) : (
            <div className={"h-full " + (tab === 'chat' ? '' : 'space-y-4')}>
              {tab === 'chat' && <DeepSeekCopilot onExploreCognitiveStory={openCognitiveStory} />}
              {tab === 'trajectory' && <CognitiveTimeline state={activeWork} />}
              {tab === 'cognition' && (
                <div className="space-y-6">
                  <CognitiveStoryTab />
                </div>
              )}
              {tab === 'constellation' && (
                <div className="w-full h-[calc(100%-32px)] min-h-[520px] rounded-xl overflow-hidden border border-[var(--eureka-spatial-hairline)]">
                  <CognitiveConstellation />
                </div>
              )}
              {tab === 'evidence' && (
                <div className="space-y-4">
                  <div className="fabric-panel p-6 bg-[var(--eureka-surface)] border border-[var(--eureka-spatial-hairline)] flex flex-col items-center justify-center gap-3 text-center">
                    <div className="text-xs uppercase tracking-widest text-[var(--eureka-text-label)]">Robustecer el análisis con documentación</div>
                    <p className="text-xs text-[var(--eureka-text-micro)]">Sube documentos (txt, pdf, docx, csv) para que EUREKA los use como evidencia.</p>
                    <button onClick={() => fileInputRef.current?.click()} className="px-4 py-2 rounded border border-[var(--eureka-signal-cognitive)] text-[var(--eureka-signal-cognitive)] text-[11px] font-bold hover:bg-[var(--eureka-surface-active)]">
                      Subir documentación
                    </button>
                    <input ref={fileInputRef} type="file" className="hidden" onChange={async (e) => { if (e.target.files && e.target.files.length > 0) await uploadEvidence(e.target.files[0]); }} />
                    {statusMsg && <div className="text-[11px] text-[var(--eureka-text-label)]">{statusMsg}</div>}
                  </div>
                  <div className="fabric-panel p-6 bg-[var(--eureka-surface)] border border-[var(--eureka-spatial-hairline)]">
                    <h3 className="text-xs font-bold text-[var(--eureka-text-display)] mb-3 tracking-widest uppercase">EVIDENCE FABRIC</h3>
                    {activeWork.evidence && activeWork.evidence.length > 0 ? (
                      <div className="space-y-2">
                        {activeWork.evidence.map((ev: any) => (
                          <div key={ev.evidence_id} className="border border-[var(--eureka-spatial-hairline)] rounded p-3 text-[11px]">
                            <div className="flex justify-between items-center">
                              <span className="font-mono text-[var(--eureka-text-display)]">{ev.filename || ev.evidence_id}</span>
                              <span className="text-[10px] uppercase tracking-wider text-[var(--eureka-signal-action)]">{ev.extraction_status || 'EXTRACTED'}</span>
                            </div>
                            <div className="text-[10px] text-[var(--eureka-text-micro)] mt-1">{ev.evidence_id} · {ev.media_type || ''}</div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-[var(--eureka-text-label)]">No evidence attached. Upload a document above to strengthen the analysis.</p>
                    )}
                  </div>
                </div>
              )}
              {tab === 'surfaces' && renderSurfaces()}
              {tab === 'evolution' && <EvolutionHITLWidget />}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
