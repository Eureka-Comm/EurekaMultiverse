import type { CognitiveProjectionDTO } from '../../../domain/cognitiveProjection';
import type { CognitiveProjectionGraph, GraphArtifact } from '../../../domain/cognitiveProjectionGraph';

/** Common props every hero cognitive view receives. */
export interface HeroProps {
  dto: CognitiveProjectionDTO;
  graph: CognitiveProjectionGraph;
  /** Open the contextual Inspector for a real artifact (also highlights the lineage path). */
  onSelectArtifact: (a: GraphArtifact) => void;
  /** Current selection id (used to show an active state in a hero). */
  selectedId?: string | null;
  /** Operational work metadata (not cognitive meaning — surfaced only in CONTEXT). */
  workId?: string | null;
  workStatus?: string | null;
}
