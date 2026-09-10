import { useSearchParams } from 'react-router-dom';
import GalaxyConstellation from '../components/cognitive/GalaxyConstellation';
import CoreConstellation from '../components/cognitive/CoreConstellation';

/**
 * DEV-ONLY renderer del lenguaje "cerebro / constelación".
 *   /__constellation          -> GALAXIA cósmica (reel DaCFIiEMPEn) por defecto
 *   /__constellation?mode=tree-> constelación en árbol (mapa de agentes)
 */
export default function CoreConstellationDemo() {
  const [params] = useSearchParams();
  const mode = params.get('mode') || 'galaxy';
  return (
    <div style={{ height: '100vh', width: '100vw', background: '#07040f' }}>
      {mode === 'tree' ? <CoreConstellation /> : <GalaxyConstellation />}
    </div>
  );
}
