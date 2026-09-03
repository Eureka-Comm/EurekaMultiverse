import { Outlet } from "react-router-dom";
import { IntelligenceRibbon } from "./IntelligenceRibbon";
import { GlobalContextInspector } from "./GlobalContextInspector";
import { TemporalRail } from "./TemporalRail";
import { CommandPalette } from "../CommandPalette";
import { ErrorBoundary } from "./ErrorBoundary";

export function EurekaShell() {
  return (
    <ErrorBoundary>
      <div className="flex h-screen w-full flex-col overflow-hidden bg-canvas font-sans text-text-section selection:bg-signal-cognitive selection:text-canvas">
      
      {/* Global Context / System State Header */}
      <header className="h-12 shrink-0 border-b border-[var(--eureka-spatial-hairline)] bg-surface flex items-center justify-between px-4">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono text-text-technical uppercase tracking-widest">Workspace</span>
            <span className="text-xs font-medium text-text-display uppercase tracking-wide">Strategic Planning</span>
          </div>
          <div className="w-[1px] h-4 bg-[var(--eureka-spatial-hairline)]" />
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono text-text-technical uppercase tracking-widest">Case</span>
            <span className="text-xs font-medium text-signal-semantic uppercase tracking-wide">Q4 Expansion / Case-001</span>
          </div>
        </div>
        
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-signal-authority" />
            <span className="text-[10px] font-mono text-signal-authority uppercase tracking-widest">Governed</span>
          </div>
          <div className="w-[1px] h-4 bg-[var(--eureka-spatial-hairline)]" />
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono text-text-technical uppercase tracking-widest">Agent</span>
            <span className="text-xs font-medium text-signal-cognitive uppercase tracking-wide">DeepSeek</span>
          </div>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <IntelligenceRibbon />
        
        <main className="flex-1 overflow-hidden relative flex flex-col bg-canvas fabric-grid-bg">
          <div className="flex-1 overflow-y-auto overflow-x-hidden relative z-10">
             <Outlet />
          </div>
        </main>

        <GlobalContextInspector />
      </div>
      
      <TemporalRail />
      <CommandPalette />
      </div>
    </ErrorBoundary>
  );
}
