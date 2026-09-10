import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useWorkStore } from '../store/workStore';
import CognitiveOperationalField from '../components/cognitive/CognitiveOperationalField';

/**
 * DEV-ONLY renderer de la Superficie Operativa Cognitiva (LS-CF-01).
 *   /__field                 -> estado conflict
 *   /__field?state=completed -> estado completed
 *   /__field?state=open      -> estado open
 */
export default function CognitiveFieldDemo() {
  const [params] = useSearchParams();
  const stateName = params.get('state') || 'conflict';
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    const fixture = stateName === 'completed' ? '/__shot_completed_state.json' : stateName === 'open' ? '/__shot_state.json' : '/__shot_conflict_state.json';
    fetch(fixture)
      .then((r) => r.json())
      .then((s) => { useWorkStore.setState({ activeWork: s, appState: 'READY' }); setLoaded(true); })
      .catch(() => setLoaded(true));
  }, [stateName]);

  return (
    <div style={{ height: '100vh', width: '100vw', background: 'var(--eureka-canvas)' }}>
      {loaded ? <CognitiveOperationalField /> : <div style={{ padding: 40, color: 'var(--eureka-text-technical)', fontFamily: 'monospace' }}>LOADING STATE…</div>}
    </div>
  );
}
