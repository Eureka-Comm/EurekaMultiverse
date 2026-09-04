import { create } from 'zustand';
import { CanonicalWorkStateSchema } from '../domain/canonicalSchema';
import type { CanonicalWorkState } from '../domain/canonicalSchema';
import { z } from 'zod';
import { API_BASE } from '../lib/apiBase';

export type AppState = 'BOOTING' | 'READY' | 'NO_WORK' | 'CONTRACT_ERROR' | 'RUNTIME_ERROR';

interface WorkState {
  appState: AppState;
  activeWork: CanonicalWorkState | null;
  startWork: (intent: string, category: string, attachments?: string[]) => Promise<any>;
  toolCall: (capability: string, params: any) => Promise<any>;
  attachEvidence: (evidenceId: string) => Promise<any>;
  executeWork: (intent: string) => Promise<any>;
  pollState: () => void;
  clearWork: () => void;
}

export const useWorkStore = create<WorkState>((set, get) => ({
  appState: 'NO_WORK',
  activeWork: null,
  
  startWork: async (intent, category, attachments = []) => {
    set({ appState: 'BOOTING' });
    try {
      const apiUrl = API_BASE;
      const response = await fetch(`${apiUrl}/api/work/intake`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_intent: intent, task_hint: category, attachments })
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        set({ appState: 'RUNTIME_ERROR', activeWork: null });
        return { status: "ERROR", reason_code: data.detail?.reason_code || 'SYSTEM_ERROR', message: data.detail?.message || 'API Intake Failed' };
      }

      try {
        const validatedState = CanonicalWorkStateSchema.parse(data);
        set({ activeWork: validatedState, appState: 'READY' });
        return validatedState;
      } catch (validationError: any) {
        if (validationError.errors) {
          console.error("CONTRACT ERROR:", validationError.errors);
          set({ appState: 'CONTRACT_ERROR', activeWork: null });
          return { status: "CONTRACT_ERROR", reason_code: "CONTRACT_ERROR", message: validationError.errors.map((e: any) => e.path.join('.') + ' ' + e.message).join(', ') };
        }
        throw validationError;
      }
    } catch (e: any) {
      console.error(e);
      set({ appState: 'RUNTIME_ERROR', activeWork: null });
      return { status: "ERROR", reason_code: "SYSTEM_ERROR", message: e.message || 'Unknown network error' };
    }
  },


  
  toolCall: async (capability, params) => {
    const activeWork = get().activeWork;
    if (!activeWork) return { status: "ERROR", reason_code: "SYSTEM_ERROR" };
    
    try {
      const apiUrl = API_BASE;
      const response = await fetch(`${apiUrl}/api/work/${activeWork.work.workId}/tool_call`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ capability, parameters: params })
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        return { status: "ERROR", reason_code: data.detail?.reason_code || 'SYSTEM_ERROR' };
      }
      
      const st = data.state || data; // Extract state if wrapped
      
      try {
        const validatedState = CanonicalWorkStateSchema.parse(st);
        set({ activeWork: validatedState });
        return data; // Return the explicit status, reason_code from tool_call
      } catch (validationError: any) {
        if (validationError.errors) {
          console.error("CONTRACT ERROR ON TOOL CALL:", validationError.errors);
          const contractErrorState = {
            ...activeWork,
            work: {
              ...activeWork.work,
              status: 'CONTRACT_ERROR'
            },
            conditions: [{
              status: 'CONTRACT_ERROR',
              reason_code: 'CONTRACT_ERROR',
              message: `State validation failed: ${validationError.errors.map((e: any) => e.path.join('.') + ' ' + e.message).join(', ')}`
            }]
          };
          set({ activeWork: contractErrorState as CanonicalWorkState });
          return { status: "CONTRACT_ERROR", reason_code: "CONTRACT_ERROR" };
        }
        throw validationError;
      }
    } catch (e: any) {
      console.error(e);
      return { status: "ERROR", reason_code: "SYSTEM_ERROR" };
    }
  },
  
  attachEvidence: async (evidenceId: string) => {
    const activeWork = get().activeWork;
    if (!activeWork) return { status: "ERROR", reason_code: "SYSTEM_ERROR" };
    
    try {
      const apiUrl = API_BASE;
      const response = await fetch(`${apiUrl}/api/work/${activeWork.work.workId}/evidence`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ evidence_id: evidenceId })
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        return { status: "ERROR", reason_code: data.detail?.reason_code || 'SYSTEM_ERROR' };
      }
      
      const st = data.state || data;
      
      try {
        const validatedState = CanonicalWorkStateSchema.parse(st);
        set({ activeWork: validatedState });
        return data;
      } catch (validationError) {
        console.error("CONTRACT ERROR ON ATTACH EVIDENCE:", validationError);
        return { status: "CONTRACT_ERROR", reason_code: "CONTRACT_ERROR" };
      }
    } catch (e: any) {
      console.error(e);
      return { status: "ERROR", reason_code: "SYSTEM_ERROR" };
    }
  },
  
  executeWork: async (intent: string) => {
    const activeWork = get().activeWork;
    if (!activeWork) return { status: "ERROR", reason_code: "SYSTEM_ERROR" };
    
    try {
      const apiUrl = API_BASE;
      const response = await fetch(`${apiUrl}/api/work/${activeWork.work.workId}/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ intent })
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        return { status: "ERROR", reason_code: data.detail?.reason_code || 'SYSTEM_ERROR' };
      }
      
      const st = data.state || data;
      
      try {
        const validatedState = CanonicalWorkStateSchema.parse(st);
        set({ activeWork: validatedState });
        return { status: "SUCCESS", work_id: data.work_id, state_status: data.status };
      } catch (validationError: any) {
        console.error("CONTRACT ERROR ON EXECUTE WORK:", validationError);
        return { status: "CONTRACT_ERROR", reason_code: "CONTRACT_ERROR" };
      }
    } catch (e: any) {
      console.error(e);
      return { status: "ERROR", reason_code: "SYSTEM_ERROR" };
    }
  },
  
  pollState: async () => {
    const activeWork = get().activeWork;
    if (!activeWork) return;
    
    // LS46: always refresh while a work is active, so HITL states
    // (WAITING_FOR_HUMAN_INPUT) remain observable after a resume.
    
    try {
      const apiUrl = API_BASE;
      const response = await fetch(`${apiUrl}/api/work/${activeWork.work.workId}/state`);
      const data = await response.json();
      
      if (response.ok) {
        const validatedState = CanonicalWorkStateSchema.parse(data);
        set({ activeWork: validatedState });
      }
    } catch (e) {
      console.error("Polling error:", e);
    }
  },

  clearWork: () => set({ activeWork: null, appState: 'NO_WORK' })
}));

