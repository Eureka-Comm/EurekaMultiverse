import React, { useMemo, useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useWorkStore } from '../../store/workStore';
import { useUIStore } from '../../store/uiStore';
import { useCognitiveProjection } from '../../hooks/useCognitiveProjection';
import {
  buildCognitiveProjectionGraph,
  relatedArtifactsForEM,
  emRoleLabel,
  type GraphArtifact,
} from '../../domain/cognitiveProjectionGraph';
import { CHAPTERS, type ChapterId } from './chapters/registry';
import { ChapterNavigator } from './ChapterNavigator';
import { LineageRibbon } from './LineageRibbon';
import { CognitiveOperationMap } from './CognitiveOperationMap';
import { Inspector } from './Inspector';
import { StorytellingPanel } from './StorytellingPanel';
import { RegisterPlus, CoordReadout } from './primitives';
import { statusColor } from './cognitiveColors';
import './cognitiveInstrument.css';

/**
 * SPATIAL COGNITIVE STORY — the SECONDARY cognitive surface (chat stays primary).
 * This is a cognitive canvas / instrument, not a card grid:
 *   · a CHAPTER TRAJECTORY carries the user through the 8 cognitive states;
 *   · a single primary HERO view (the current cognitive state) fills the stage;
 *   · the stage is a spatial field (grid + registration + coordinate HUD);
 *   · a contextual Inspector appears on demand;
 *   · a single LINEAGE THREAD traces EVI→…→FROZEN.
 * Every value reads from the single `CognitiveProjectionDTO` (via the graph model).
 * Nothing is fabricated.
 */

const EM_TO_CHAPTER: Record<string, ChapterId> = {
  'EM Predictor': 'prediction',
  'EM Prescriptor': 'decision',
  'EM Installer': 'action',
  'EM Descriptor': 'discovery',
  'EM Structurer': 'discovery',
  'EM Publisher': 'result',
  'EM Core': 'question',
};

type Mode = 'map' | 'narrative';

interface Selection {
  title: string;
  emRole?: string;
  artifacts: GraphArtifact[];
}

export function CognitiveStoryTab() {
  const activeWork = useWorkStore((s) => s.activeWork);
  const dto = useCognitiveProjection(activeWork);
  const graph = useMemo(() => buildCognitiveProjectionGraph(dto), [dto]);

  const [chapter, setChapter] = useState<ChapterId>(() => {
    // Dev/screenshot harness: jump to a chapter via ?c=<id>.
    const c = new URLSearchParams(window.location.search).get('c');
    return (c && CHAPTERS.some((x) => x.id === c)) ? (c as ChapterId) : 'question';
  });
  const [mode, setMode] = useState<Mode>(() => {
    // Dev/screenshot harness: jump straight to the Knowledge Space via ?m=graph,
    // the narrative chapters via ?m=narrative, or default to the Operation Map.
    const m = new URLSearchParams(window.location.search).get('m');
    if (m === 'narrative') return 'narrative';
    return 'map';
  });
  const [selection, setSelection] = useState<Selection | null>(null);

  const setChapterForArtifact = (kind: string) => {
    const map: Record<string, ChapterId> = {
      EVIDENCE: 'discovery',
      FINDING: 'discovery',
      PREDICTION: 'prediction',
      PRESCRIPTION: 'prescription',
      ALTERNATIVE: 'prescription',
      DECISION: 'decision',
      ACTION: 'action',
      EXECUTION: 'result',
      RESULT: 'result',
      FROZEN: 'result',
      PROBLEM: 'question',
    };
    const ch = map[kind];
    if (ch) setChapter(ch);
  };

  // §20 — deep-link focus from the Chat "[EXPLORE COGNITIVE STORY]" bridge.
  const consumeCognitiveFocus = useUIStore((s) => s.consumeCognitiveFocus);
  useEffect(() => {
    const focus = consumeCognitiveFocus();
    const focused: Record<string, ChapterId> = { DECISION: 'decision', ACTION: 'action', RESULT: 'result' };
    if (focus && focused[focus]) {
      setChapter(focused[focus]);
      setMode('narrative');
    }
  }, [consumeCognitiveFocus]);

  // §5 — listen for EM clicks dispatched from the persistent 8-EM rail.
  useEffect(() => {
    const handler = (ev: Event) => {
      const em = (ev as CustomEvent).detail?.em;
      if (!em) return;
      const arts = relatedArtifactsForEM(em, graph);
      setSelection({
        title: 'EM INSPECT',
        emRole: emRoleLabel(em),
        artifacts: arts,
      });
      const ch = EM_TO_CHAPTER[em] || 'context';
      setChapter(ch);
      setMode('narrative');
      if (arts[0]) setChapterForArtifact(arts[0].kind);
    };
    window.addEventListener('eureka:inspect-em', handler);
    return () => window.removeEventListener('eureka:inspect-em', handler);
  }, [graph]);

  const onSelectArtifact = (a: GraphArtifact) => {
    setSelection({ title: `ARTIFACT · ${a.id}`, artifacts: [a] });
  };

  const selectedId = selection?.artifacts[0]?.id ?? null;
  const activeChapter = CHAPTERS.find((c) => c.id === chapter)!;
  const ActiveHero = activeChapter.Component;

  if (!activeWork) return null;

  const isEmpty = graph.nodes.length === 0;

  return (
    <div className="ci-root">
      {/* Chapter navigator — the cognitive trajectory */}
      <ChapterNavigator chapters={CHAPTERS} active={chapter} onSelect={(id) => setChapter(id)} dto={dto} />

      {/* Instrument header */}
      <div className="ci-header">
        <div className="ci-title">
          Cognitive Story<span className="ci-title-rule" />
          <span className="ci-sub">CognitiveProjectionDTO · single source</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-[11px] font-mono text-[var(--eureka-text-label)]">{activeWork.work.workId}</span>
          <span
            className="inline-flex items-center gap-1 text-[9px] font-mono uppercase tracking-wider px-2 py-0.5 rounded border"
            style={{ color: statusColor(activeWork.work.status), borderColor: statusColor(activeWork.work.status) }}
          >
            {activeWork.work.status}
          </span>
          {/* mode toggle: UNDERSTAND (operation map) vs EXPLORE (3D knowledge space) */}
          <div className="flex items-center gap-0.5 rounded-lg border border-[var(--eureka-spatial-hairline)] p-0.5 overflow-hidden">
            {(['map', 'narrative'] as Mode[]).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={`px-2.5 py-1 text-[9px] font-mono uppercase tracking-wider rounded transition-colors ${
                  mode === m ? 'bg-[var(--eureka-surface-selected)] text-[var(--eureka-text-display)]' : 'text-[var(--eureka-text-label)] hover:text-[var(--eureka-text-display)]'
                }`}
              >
                {m === 'map' ? 'Understand' : 'Cognitive State'}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Main instrument body: primary stage + contextual inspector */}
      <div className={`ci-body ${selection ? 'has-inspector' : ''}`}>
        <section className="ci-stage" data-chapter={activeChapter.id}>
          <CoordReadout>
            CHAPTER {activeChapter.num} · {activeChapter.short.toUpperCase()}
          </CoordReadout>
          <RegisterPlus pos="tl" />
          <RegisterPlus pos="tr" />
          <RegisterPlus pos="bl" />
          <RegisterPlus pos="br" />
          <div className="ci-stage-scroll">
            <AnimatePresence mode="wait">
              <motion.div
                key={mode === 'map' ? 'map' : chapter}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.24, ease: 'easeOut' }}
              >
                {mode === 'map' ? (
                  <div className="w-full h-[560px]" data-operationsurface="map">
                    <CognitiveOperationMap dto={dto} graph={graph} onSelectArtifact={onSelectArtifact} />
                  </div>
                ) : (
                  <div className="ci-hero">
                    <ActiveHero
                      dto={dto}
                      graph={graph}
                      onSelectArtifact={onSelectArtifact}
                      selectedId={selectedId}
                      workId={activeWork.work.workId}
                      workStatus={activeWork.work.status}
                    />
                  </div>
                )}
              </motion.div>
            </AnimatePresence>
          </div>
        </section>

        {/* Contextual inspector — appears only on demand */}
        <AnimatePresence>
          {selection && (
            <motion.aside
              initial={{ opacity: 0, x: 26 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 26 }}
              transition={{ duration: 0.22, ease: 'easeOut' }}
              className="ci-inspector-rail"
            >
              <div className="flex items-center justify-between px-4 py-2.5 border-b border-[var(--eureka-spatial-hairline)]">
                <span className="text-[9px] font-mono uppercase tracking-[0.1em] text-[var(--eureka-text-label)]">Inspector</span>
                <button onClick={() => setSelection(null)} className="text-[10px] text-[var(--eureka-text-micro)] hover:text-[var(--eureka-text-display)]">
                  ✕
                </button>
              </div>
              <div className="ci-inspector-scroll">
                <Inspector title={selection.title} emRole={selection.emRole} artifacts={selection.artifacts} />
              </div>
            </motion.aside>
          )}
        </AnimatePresence>
      </div>

      {/* Lineage thread (single cognitive rail, real ids only) */}
      <LineageRibbon graph={graph} onSelectArtifact={onSelectArtifact} selectedId={selectedId} />

      {/* Storytelling — progressive visual narrative (secondary reading surface) */}
      {!isEmpty && (
        <div className="ci-panel mt-4">
          <div className="ci-panel-title">Narrative · progressive disclosure</div>
          <div className="p-4">
            <StorytellingPanel dto={dto} onSelectArtifact={onSelectArtifact} />
          </div>
        </div>
      )}
    </div>
  );
}

export default CognitiveStoryTab;
