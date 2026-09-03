import { create } from 'zustand';
import { MOCK_DECISION_GRAPH } from '../domain/mockData';
import type { Alternative, Evidence, Constraint, TimelineEvent, NodeBase } from '../domain/mockData';

export interface AnalyticalState {
  decisionContext: typeof MOCK_DECISION_GRAPH.context;
  alternatives: Alternative[];
  evidence: Evidence[];
  constraints: Constraint[];
  timeline: TimelineEvent[];
  edges: typeof MOCK_DECISION_GRAPH.edges;

  // Selection state
  selectedEntityId: string | null;
  selectedEntityType: 'ALTERNATIVE' | 'EVIDENCE' | 'CONSTRAINT' | 'TIMELINE' | 'OBJECTIVE' | null;
  
  activeFilters: Record<string, any>;
  hoveredEntity: string | null;
  
  // Computed helpers (could also be derived in components)
  inspectorMode: 'default' | 'alternative' | 'evidence' | 'constraint' | 'temporal' | 'governance';
  
  // Actions
  selectEntity: (id: string | null, type?: 'ALTERNATIVE' | 'EVIDENCE' | 'CONSTRAINT' | 'TIMELINE' | 'OBJECTIVE' | null) => void;
  setHoveredEntity: (id: string | null) => void;
  setInspectorMode: (mode: AnalyticalState['inspectorMode']) => void;
  clearSelection: () => void;
}

export const useAnalyticalStore = create<AnalyticalState>((set) => ({
  decisionContext: MOCK_DECISION_GRAPH.context,
  alternatives: MOCK_DECISION_GRAPH.alternatives,
  evidence: MOCK_DECISION_GRAPH.evidence,
  constraints: MOCK_DECISION_GRAPH.constraints,
  timeline: MOCK_DECISION_GRAPH.timeline,
  edges: MOCK_DECISION_GRAPH.edges,

  selectedEntityId: null,
  selectedEntityType: null,
  
  activeFilters: {},
  hoveredEntity: null,
  inspectorMode: 'default',
  
  selectEntity: (id, type) => {
    let mode: AnalyticalState['inspectorMode'] = 'default';
    if (id) {
       if (type === 'ALTERNATIVE') mode = 'alternative';
       else if (type === 'EVIDENCE') mode = 'evidence';
       else if (type === 'CONSTRAINT') mode = 'constraint';
       else if (type === 'TIMELINE') mode = 'temporal';
       else if (type === 'OBJECTIVE') mode = 'governance'; // Map objective context to governance/overview
    }
    set({ selectedEntityId: id, selectedEntityType: type || null, inspectorMode: mode });
  },
  
  setHoveredEntity: (id) => set({ hoveredEntity: id }),
  setInspectorMode: (mode) => set({ inspectorMode: mode }),
  
  clearSelection: () => set({
    selectedEntityId: null,
    selectedEntityType: null,
    hoveredEntity: null,
    inspectorMode: 'default',
  }),
}));
