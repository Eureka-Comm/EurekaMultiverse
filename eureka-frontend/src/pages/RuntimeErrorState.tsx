import React from 'react';
import { useWorkStore } from '../store/workStore';

export default function RuntimeErrorState() {
  const activeWork = useWorkStore((state) => state.activeWork);
  const clearWork = useWorkStore((state) => state.clearWork);
  
  // Extract error message if activeWork exists (it might not if intake failed)
  const errorMessage = activeWork?.conditions?.find(c => c.status === 'ERROR')?.message || 'SYSTEM_ERROR';

  return (
    <div className="flex h-screen bg-[var(--eureka-canvas)] items-center justify-center text-[var(--eureka-text-section)]">
      <div className="flex flex-col items-center max-w-3xl space-y-6 text-center">
        <h2 className="text-3xl text-red-500 font-light">EUREKA RUNTIME ERROR</h2>
        <div className="fabric-panel p-6 bg-[#16161c] border-red-500 border w-full text-left overflow-auto">
          <p className="text-sm text-red-300 font-bold mb-4">
            The EUREKA Runtime could not complete this operation.
          </p>
          <div className="space-y-2 text-xs text-[var(--eureka-text-technical)] font-mono">
            <p><strong>Reason:</strong></p>
            <p className="bg-black p-2">{errorMessage}</p>
          </div>
          <p className="text-xs text-[var(--eureka-text-label)] mt-6">
            No result has been fabricated.
          </p>
        </div>
        <div className="flex gap-4">
          <button 
            onClick={() => window.location.reload()} 
            className="px-6 py-2 bg-[#1e1e24] text-[var(--eureka-text-technical)] border border-[var(--eureka-spatial-hairline)] font-bold rounded text-sm hover:opacity-90"
          >
            RETRY
          </button>
          <button 
            onClick={() => {
              clearWork();
              useWorkStore.setState({ appState: 'NO_WORK' });
            }} 
            className="px-6 py-2 bg-[var(--eureka-signal-action)] text-white font-bold rounded text-sm hover:opacity-90"
          >
            RETURN TO INTAKE
          </button>
        </div>
      </div>
    </div>
  );
}
