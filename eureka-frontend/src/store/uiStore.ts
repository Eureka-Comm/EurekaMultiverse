import { create } from 'zustand';

interface Decision {
  id: string;
  title: string;
  status: string;
  riskScore: number;
  parameters: Record<string, string | number>;
}

interface UIState {
  isInspectorOpen: boolean;
  selectedDecision: Decision | null;
  openInspector: (decision: Decision) => void;
  closeInspector: () => void;

  /** §20 — deep-link focus for the Cognitive Story (e.g. 'DECISION' chapter). */
  cognitiveFocusChapter: string | null;
  requestCognitiveFocus: (chapter: string) => void;
  consumeCognitiveFocus: () => string | null;
}

export const useUIStore = create<UIState>((set, get) => ({
  isInspectorOpen: false,
  selectedDecision: null,
  openInspector: (decision) => set({ isInspectorOpen: true, selectedDecision: decision }),
  closeInspector: () => set({ isInspectorOpen: false, selectedDecision: null }),

  cognitiveFocusChapter: null,
  requestCognitiveFocus: (chapter) => set({ cognitiveFocusChapter: chapter }),
  consumeCognitiveFocus: () => {
    const c = get().cognitiveFocusChapter;
    if (c) set({ cognitiveFocusChapter: null });
    return c;
  },
}));
