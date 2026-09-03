import { create } from 'zustand';

interface AnalyticalState {
  globalTimeRange: [number, number];
  selectedDimensions: string[];
  activeScenarioId: string | null;
  selectedAlternatives: string[];
  
  setTimeRange: (range: [number, number]) => void;
  toggleDimension: (dim: string) => void;
  setActiveScenario: (id: string | null) => void;
  toggleAlternative: (alt: string) => void;
  resetFilters: () => void;
}

export const useAnalyticalStore = create<AnalyticalState>((set) => ({
  globalTimeRange: [0, 100],
  selectedDimensions: ['utility', 'cost', 'risk'],
  activeScenarioId: null,
  selectedAlternatives: [],
  
  setTimeRange: (range) => set({ globalTimeRange: range }),
  
  toggleDimension: (dim) => set((state) => ({
    selectedDimensions: state.selectedDimensions.includes(dim)
      ? state.selectedDimensions.filter(d => d !== dim)
      : [...state.selectedDimensions, dim]
  })),
  
  setActiveScenario: (id) => set({ activeScenarioId: id }),
  
  toggleAlternative: (alt) => set((state) => ({
    selectedAlternatives: state.selectedAlternatives.includes(alt)
      ? state.selectedAlternatives.filter(a => a !== alt)
      : [...state.selectedAlternatives, alt]
  })),
  
  resetFilters: () => set({
    globalTimeRange: [0, 100],
    selectedDimensions: ['utility', 'cost', 'risk'],
    activeScenarioId: null,
    selectedAlternatives: []
  })
}));
