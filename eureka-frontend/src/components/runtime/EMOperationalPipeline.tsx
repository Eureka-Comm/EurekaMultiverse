import React, { useState, useMemo } from 'react';
import type { CanonicalWorkState, EMStatus, ExecutionStep, Evidence } from '../../domain/canonicalSchema';
import NeuralPipelineRail from './NeuralPipelineRail';
import { useCognitiveProjection } from '../../hooks/useCognitiveProjection';
import {
  buildCognitiveProjectionGraph,
  relatedArtifactsForEM,
  emRoleLabel,
} from '../../domain/cognitiveProjectionGraph';
import { Inspector } from '../cognitive/Inspector';

interface Props {
  state: CanonicalWorkState;
}

function mapRailStatus(status: string): { status: 'completed' | 'waiting' | 'pending'; caption: string } {
  switch (status) {
    case 'COMPLETED': return { status: 'completed', caption: 'COMPLETED' };
    case 'WAITING_FOR_HUMAN_INPUT': return { status: 'waiting', caption: 'WAITING FOR HUMAN INPUT' };
    case 'WAITING_FOR_EVIDENCE': return { status: 'waiting', caption: 'WAITING FOR EVIDENCE' };
    case 'RUNNING': return { status: 'waiting', caption: 'RUNNING' };
    case 'READY': return { status: 'pending', caption: 'READY' };
    case 'PENDING': return { status: 'pending', caption: 'PENDING' };
    case 'NOT_REQUIRED': return { status: 'pending', caption: 'NOT REQUIRED' };
    case 'NOT_APPLICABLE': return { status: 'pending', caption: 'NOT APPLICABLE' };
    case 'GAP': return { status: 'waiting', caption: 'GAP' };
    case 'BLOCKED': return { status: 'waiting', caption: 'BLOCKED' };
    case 'FAILED': return { status: 'waiting', caption: 'FAILED' };
    default: return { status: 'pending', caption: status.replace(/_/g, ' ') };
  }
}

export default function EMOperationalPipeline({ state }: Props) {
  const pipeline = state.em_pipeline || [];

  const [selectedEM, setSelectedEM] = useState<string | null>(null);

  // §5 — read the SINGLE projection so the EM click affordance shows real artifacts.
  const dto = useCognitiveProjection(state);
  const graph = useMemo(() => buildCognitiveProjectionGraph(dto), [dto]);

  if (pipeline.length === 0) {
    return null;
  }

  // Mapear el estado real de los 8 EM al rail neuronal (NeuralPipelineRail).
  const railStages = pipeline.map((p) => {
    const m = mapRailStatus(p.status);
    return { key: p.canonical_em, label: p.canonical_em.replace('EM ', ''), status: m.status, caption: m.caption };
  });

  // Figure out the current EM
  const runningEMs = pipeline.filter(p => p.status === 'RUNNING' || p.status === 'FAILED' || p.status === 'BLOCKED' || p.status === 'GAP');
  const activeEM = runningEMs.length > 0 ? runningEMs[0] : null;

  // Get details of active EM from Execution steps
  let activeStepDetails: ExecutionStep | null = null;
  let activeEvidence: Evidence[] = [];

  if (activeEM) {
    const runningStepId = activeEM.step_ids.find(id => {
      const step = state.execution_plan.steps.find(s => s.step_id === id);
      return step && (step.status === 'RUNNING' || step.status === 'FAILED' || step.status === 'BLOCKED' || step.status === 'GAP');
    });

    if (runningStepId) {
      activeStepDetails = state.execution_plan.steps.find(s => s.step_id === runningStepId) || null;
    } else {
      activeStepDetails = state.execution_plan.steps.find(s => activeEM.step_ids.includes(s.step_id)) || null;
    }

    if (activeStepDetails && state.evidence) {
      activeEvidence = state.evidence;
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'COMPLETED': return '✓';
      case 'RUNNING': return '◉';
      case 'FAILED': return '❌';
      case 'BLOCKED': return '⏸';
      case 'GAP': return '⚠';
      case 'NOT_REQUIRED': return '○';
      case 'NOT_APPLICABLE': return '○';
      case 'READY': return '○';
      default: return '○';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'COMPLETED': return 'text-green-600';
      case 'RUNNING': return 'text-yellow-600 animate-pulse';
      case 'FAILED': return 'text-red-600';
      case 'BLOCKED': return 'text-orange-600';
      case 'GAP': return 'text-purple-600';
      case 'NOT_REQUIRED': return 'text-[var(--eureka-text-micro)] opacity-60';
      case 'NOT_APPLICABLE': return 'text-[var(--eureka-text-micro)] opacity-60';
      case 'READY': return 'text-blue-600';
      default: return 'text-[var(--eureka-text-label)]';
    }
  };

  const handleStageClick = (em: string) => {
    setSelectedEM((prev) => (prev === em ? null : em));
    // Dispatch so the Cognitive Story tab can also focus the inspector.
    window.dispatchEvent(new CustomEvent('eureka:inspect-em', { detail: { em } }));
  };

  const selectedArts = selectedEM ? relatedArtifactsForEM(selectedEM, graph) : [];
  const selectedRole = selectedEM ? emRoleLabel(selectedEM) : undefined;

  return (
    <div className="w-full">
      <div className="bg-white">
        {/* THE VISUAL PIPELINE RAIL (top) — NeuralPipelineRail (blanco, sin cabecera ni borde) */}
        <NeuralPipelineRail stages={railStages} onStageClick={handleStageClick} />
      </div>
      {selectedEM && (
        <div className="border-t border-[var(--eureka-spatial-hairline)] px-4 py-3 bg-[var(--eureka-surface)]">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--eureka-text-label)]">
              {selectedEM} · {selectedRole || 'EM role'}
            </span>
            <button
              onClick={() => setSelectedEM(null)}
              className="ml-auto text-[10px] text-[var(--eureka-text-micro)] hover:text-[var(--eureka-text-display)]"
            >
              CLOSE ✕
            </button>
          </div>
          <Inspector title={`EM INSPECT`} emRole={selectedRole} artifacts={selectedArts} emptyText="DATA NOT AVAILABLE — no governed artifacts for this EM." />
        </div>
      )}
    </div>
  );
}
