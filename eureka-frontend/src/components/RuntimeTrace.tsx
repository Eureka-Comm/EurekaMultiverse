import React, { useState } from 'react';
import { useWorkStore } from '../store/workStore';

export default function RuntimeTrace() {
  const activeWork = useWorkStore((state) => state.activeWork);
  const [isOpen, setIsOpen] = useState(false);

  if (!activeWork) return null;

  const traceSteps = [
    { label: 'RAW INTENT', value: activeWork.work.userIntent },
    { label: 'EVIDENCE ATTACHED', value: activeWork.evidence?.length ? activeWork.evidence.map(e => `${e.filename} (${e.evidence_id})`).join('\n') : 'None' },
    { label: 'PROBLEM MODEL', value: `Structured Domain: ${activeWork.work.taskCategory}\nCapabilities Needed: ${activeWork.available_capabilities?.length || 0}` },
    { label: 'REQUIREMENTS', value: `Resolved: ${activeWork.available_capabilities?.join(', ') || 'None'}` },
    { label: 'CAPABILITY RESOLUTION', value: `GAPs Found: ${activeWork.gaps?.length || 0}\n${activeWork.gaps?.join(', ') || ''}` },
    { label: 'EXECUTION PLAN', value: `Steps: ${activeWork.execution_plan.steps.map(s => s.target).join(' -> ')}` },
    { label: 'EXECUTION EVENT', value: `Tool Calls Processed. Latest Revision: ${activeWork.revision || 1}` },
    { label: 'PROVENANCE', value: `Log tracking active. Extracted from original evidence.` },
    { label: 'CANONICAL STATE REVISION', value: `Revision: ${activeWork.revision || 1}\nStatus: ${activeWork.work.status}` },
    { label: 'VISUAL MANIFEST', value: activeWork.visualizations?.map(v => `${v.id} [${v.status || 'AVAILABLE'}]`).join(', ') || 'None' },
    { label: 'STORY', value: `Dynamic Acts Derived.` },
    { label: 'ARTIFACT', value: `PDF / Report Projection ready.` }
  ];

  return (
    <>
      <button 
        onClick={() => setIsOpen(!isOpen)}
        title="Runtime Trace"
        className="fixed bottom-[92px] right-4 w-8 h-8 flex items-center justify-center rounded-full bg-[#1e1e24] text-[var(--eureka-text-technical)] border border-[var(--eureka-spatial-hairline)] z-50 hover:bg-[#2a2a32] text-sm leading-none"
      >
        ⌗
      </button>

      {isOpen && (
        <div className="fixed inset-y-0 right-0 w-[450px] bg-[#0d0d12] border-l border-[var(--eureka-spatial-hairline)] z-40 p-6 flex flex-col shadow-2xl">
          <div className="flex justify-between items-center mb-6 pb-4 border-b border-[var(--eureka-spatial-hairline)]">
            <h2 className="text-sm font-mono text-[var(--eureka-text-display)]">EUREKA RUNTIME TRACE</h2>
            <button onClick={() => setIsOpen(false)} className="text-[var(--eureka-text-label)] hover:text-white text-xs">CLOSE</button>
          </div>
          
          <div className="flex-1 overflow-y-auto space-y-4 font-mono pr-2">
            {traceSteps.map((step, idx) => (
              <div key={idx} className="relative">
                {idx !== traceSteps.length - 1 && (
                  <div className="absolute left-[7px] top-6 bottom-[-20px] w-[1px] bg-[var(--eureka-spatial-hairline)] z-0"></div>
                )}
                <div className="flex gap-4 relative z-10">
                  <div className="w-4 h-4 mt-1 rounded-full bg-[#1e1e24] border border-[var(--eureka-signal-semantic)] flex items-center justify-center flex-shrink-0">
                    <div className="w-1.5 h-1.5 bg-[var(--eureka-signal-semantic)] rounded-full"></div>
                  </div>
                  <div className="flex-1 pb-4">
                    <h3 className="text-xs text-[var(--eureka-text-label)] mb-1">{step.label}</h3>
                    <p className="text-xs text-[var(--eureka-text-technical)] bg-[#1e1e24] p-2 rounded whitespace-pre-wrap break-words border border-[#2a2a32]">
                      {step.value || 'N/A'}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
          
          <div className="mt-4 pt-4 border-t border-[var(--eureka-spatial-hairline)] text-[10px] text-[var(--eureka-text-label)]">
            <p>WORK_ID: {activeWork.work.workId}</p>
            <p>REVISION: {activeWork.revision || 1}</p>
          </div>
        </div>
      )}
    </>
  );
}
