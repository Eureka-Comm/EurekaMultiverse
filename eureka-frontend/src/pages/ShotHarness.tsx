import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useWorkStore } from '../store/workStore';
import { useCognitiveProjection } from '../hooks/useCognitiveProjection';
import { ExecutiveCognitiveAnswer } from '../components/cognitive/ExecutiveCognitiveAnswer';
import CognitiveStoryTab from '../components/cognitive/CognitiveStoryTab';

/**
 * DEV-ONLY screenshot / render harness. NOT a production route; it is only
 * registered in dev mode so the browser can capture the spatial cognitive
 * instrument (Chat command center + Cognitive Story canvas) deterministically
 * over a REAL governed work state for BEFORE/AFTER evaluation.
 *
 *   ?view=chat            -> EUREKA Cognitive Command Center (Chat primary)
 *   ?view=story           -> Spatial Cognitive Story canvas (chapter trajectory)
 *   ?view=story&c=<id>    -> jump straight to a chapter by id
 */
export default function ShotHarness() {
  const [params] = useSearchParams();
  const view = params.get('view') || 'story';
  const chapter = params.get('c');
  const stateName = params.get('state') || 'open';
  const [loaded, setLoaded] = useState(false);

  // Load a REAL completed governed state into the workspace store (single source).
  useEffect(() => {
    const fixture = stateName === 'completed' ? '/__shot_completed_state.json' : stateName === 'conflict' ? '/__shot_conflict_state.json' : '/__shot_state.json';
    fetch(fixture)
      .then((r) => r.json())
      .then((s) => {
        useWorkStore.setState({ activeWork: s, appState: 'READY' });
        setLoaded(true);
      })
      .catch((e) => {
        console.error('shot harness fixture load failed', e);
        setLoaded(true);
      });
  }, [stateName]);

  const activeWork = useWorkStore((s) => s.activeWork);
  const dto = useCognitiveProjection(activeWork);

  if (!loaded) {
    return <div style={{ padding: 40, color: '#8c959f', fontFamily: 'monospace' }}>LOADING SHOT STATE…</div>;
  }

  return (
    <div style={{ height: '100vh', overflow: 'auto', background: 'var(--eureka-canvas)' }}>
      {/* a thin dev toolbar */}
      <div style={{ display: 'flex', gap: 10, padding: '10px 16px', borderBottom: '1px solid var(--eureka-spatial-hairline)', background: '#fff', fontSize: 10, fontFamily: 'monospace' }}>
        <a href="?view=chat" style={{ color: 'var(--eureka-signal-cognitive)' }}>CHAT</a>
        <a href="?view=story" style={{ color: 'var(--eureka-signal-cognitive)' }}>STORY</a>
        <a href="?view=story&m=graph" style={{ color: 'var(--eureka-signal-cognitive)' }}>KNOWLEDGE SPACE</a>
        <a href="?view=story&m=graph&state=completed" style={{ color: 'var(--eureka-text-label)' }}>COMPLETED</a>
        {view === 'story' && (
          ['open', 'question', 'context', 'discovery', 'prediction', 'prescription', 'decision', 'action', 'result'].map((c) => (
            <a key={c} href={`?view=story&c=${c}`} style={{ color: 'var(--eureka-text-label)', textTransform: 'uppercase' }}>{c}</a>
          ))
        )}
      </div>
      <div style={{ padding: view === 'chat' ? '24px 9%' : '12px 3%' }}>
        {view === 'chat' ? (
          <div
            data-shot-view="chat"
            style={{ maxWidth: 920, margin: '0 auto', borderRadius: 6, border: '1px solid var(--eureka-spatial-hairline)', background: '#fff', padding: '18px 22px' }}
          >
            <ExecutiveCognitiveAnswer dto={dto} onExplore={(c) => { window.location.href = `?view=story&c=${c.toLowerCase() === 'action' ? 'action' : c.toLowerCase() === 'result' ? 'result' : 'decision'}`; }} />
          </div>
        ) : (
          <div data-shot-view="story">
            <CognitiveStoryTab />
          </div>
        )}
      </div>
    </div>
  );
}
