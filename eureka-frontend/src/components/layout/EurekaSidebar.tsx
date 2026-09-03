import React, { useState } from 'react';
import { useWorkStore } from '../../store/workStore';
import { Plus, Settings, FolderOpen, Search, SlidersHorizontal, PanelRightClose, PanelRight } from 'lucide-react';

/**
 * EUREKA left sidebar (estilo DeepSeek Harness, colapsable, iconos SVG funcionales).
 * "New Session" -> limpia el work; Workspaces -> muestra la sesión activa; Settings.
 * Se puede contraer/expandir con el toggle de la esquina superior derecha.
 */
export default function EurekaSidebar() {
  const activeWork = useWorkStore((state) => state.activeWork);
  const clearWork = useWorkStore((state) => state.clearWork);
  const [collapsed, setCollapsed] = useState(false);
  const workId = activeWork?.work?.workId;
  const status = activeWork?.work?.status;

  if (collapsed) {
    return (
      <aside className="w-[56px] min-w-[56px] flex flex-col items-center gap-2 bg-[var(--eureka-canvas)] border-r border-[var(--eureka-spatial-hairline)] h-screen py-3">
        <button onClick={() => setCollapsed(false)} title="Expandir" className="p-2 text-[var(--eureka-text-label)] hover:text-[var(--eureka-text-display)] transition-colors"><PanelRight size={18} /></button>
        <button onClick={() => clearWork()} title="New Session" className="p-2 text-[var(--eureka-text-label)] hover:text-[var(--eureka-text-display)] transition-colors"><Plus size={18} /></button>
        {workId && <div className="w-5 h-5 rounded-full bg-[var(--eureka-surface-active)] border border-[var(--eureka-spatial-hairline)]" title={workId} />}
        <div className="flex-1" />
        <button onClick={() => window.location.assign('/legacy/settings')} title="Settings" className="p-2 text-[var(--eureka-text-label)] hover:text-[var(--eureka-text-display)] transition-colors"><Settings size={18} /></button>
      </aside>
    );
  }

  return (
    <aside className="w-[260px] min-w-[260px] flex flex-col bg-[var(--eureka-canvas)] border-r border-[var(--eureka-spatial-hairline)] h-screen">
      {/* LOGO + toggle */}
      <div className="px-4 py-4 flex items-center gap-2">
        <span className="text-lg font-black text-[var(--eureka-text-display)] tracking-tight">eureka</span>
        <span className="text-[9px] font-bold tracking-widest px-1.5 py-0.5 rounded bg-[var(--eureka-surface)] text-[var(--eureka-text-label)] uppercase">Multiverse</span>
        <button onClick={() => setCollapsed(true)} title="Contraer sidebar" className="ml-auto p-1 text-[var(--eureka-text-label)] hover:text-[var(--eureka-text-display)] transition-colors">
          <PanelRightClose size={18} />
        </button>
      </div>

      {/* NEW SESSION */}
      <div className="px-3">
        <button
          onClick={() => clearWork()}
          className="w-full flex items-center justify-center gap-2 text-sm font-medium text-[var(--eureka-text-display)] bg-white border border-[var(--eureka-spatial-hairline)] rounded-full py-2 hover:bg-[var(--eureka-surface-active)] transition-colors"
        >
          <Plus size={16} /> New Session
        </button>
      </div>

      {/* WORKSPACES */}
      <div className="flex-1 overflow-y-auto px-3 py-3">
        <div className="text-[11px] uppercase tracking-wide text-[var(--eureka-text-label)] mb-1 flex items-center justify-between px-1">
          <span>Workspaces</span>
          <span className="flex items-center gap-1.5 text-[var(--eureka-text-micro)]">
            <Search size={13} /><SlidersHorizontal size={13} /><FolderOpen size={13} />
          </span>
        </div>
        {workId ? (
          <div className="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-[var(--eureka-surface-active)] cursor-pointer text-sm text-[var(--eureka-text-section)]">
            <FolderOpen size={16} className="text-[var(--eureka-signal-cognitive)] shrink-0" />
            <span className="truncate">{workId}</span>
            <span className="ml-auto text-[10px] text-[var(--eureka-text-micro)]">{status}</span>
          </div>
        ) : (
          <div className="px-2 py-1.5 text-sm text-[var(--eureka-text-micro)]">Sin sesión activa</div>
        )}
      </div>

      {/* SETTINGS */}
      <div className="px-3 py-3 border-t border-[var(--eureka-spatial-hairline)]">
        <button onClick={() => window.location.assign('/legacy/settings')} className="flex items-center gap-2 text-sm text-[var(--eureka-text-label)] hover:text-[var(--eureka-text-display)] transition-colors px-2 py-1.5">
          <Settings size={15} /> Settings
        </button>
      </div>
    </aside>
  );
}
