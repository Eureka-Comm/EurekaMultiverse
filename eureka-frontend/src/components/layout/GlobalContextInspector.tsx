import { motion, AnimatePresence } from "framer-motion";
import { useAnalyticalStore } from "../../store/analyticalStore";
import { X, Activity, ShieldAlert, GitMerge, FileText, Anchor, Clock, CheckCircle } from "lucide-react";
import { cn } from "../../lib/utils";

export function GlobalContextInspector() {
  const { 
    selectedEntityId, 
    selectedEntityType,
    decisionContext,
    alternatives,
    evidence,
    constraints,
    timeline,
    clearSelection 
  } = useAnalyticalStore();
  
  const isOpen = selectedEntityId !== null || selectedEntityType !== null;

  // Find the selected entity
  let selectedEntity: any = null;
  if (selectedEntityId) {
    if (selectedEntityType === 'ALTERNATIVE') selectedEntity = alternatives.find(a => a.id === selectedEntityId);
    else if (selectedEntityType === 'EVIDENCE') selectedEntity = evidence.find(e => e.id === selectedEntityId);
    else if (selectedEntityType === 'CONSTRAINT') selectedEntity = constraints.find(c => c.id === selectedEntityId);
    else if (selectedEntityType === 'TIMELINE') selectedEntity = timeline.find(t => t.id === selectedEntityId);
    else if (selectedEntityType === 'OBJECTIVE') selectedEntity = { type: 'OBJECTIVE', ...decisionContext };
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div 
          initial={{ width: 0, opacity: 0 }}
          animate={{ width: 384, opacity: 1 }}
          exit={{ width: 0, opacity: 0 }}
          transition={{ duration: 0.2, ease: "easeInOut" }}
          className="h-full bg-surface-elevated border-l border-[var(--eureka-spatial-hairline)] flex flex-col overflow-hidden shrink-0"
        >
          {/* Header */}
          <div className="p-4 border-b border-[var(--eureka-spatial-hairline)] flex items-center justify-between bg-surface">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-signal-cognitive" />
              <h2 className="text-[10px] font-mono text-text-label uppercase tracking-widest">Global Context Inspector</h2>
            </div>
            <button onClick={clearSelection} className="text-text-technical hover:text-text-display">
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Content Area */}
          <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-6">
            {!selectedEntity ? (
              <div className="flex flex-col items-center justify-center h-full text-center gap-4 text-text-technical">
                <ShieldAlert className="w-8 h-8 opacity-50" />
                <p className="text-sm font-mono uppercase tracking-wider">Entity Not Found</p>
              </div>
            ) : selectedEntityType === 'ALTERNATIVE' ? (
              <AlternativeInspectorContent entity={selectedEntity} />
            ) : selectedEntityType === 'EVIDENCE' ? (
              <EvidenceInspectorContent entity={selectedEntity} />
            ) : selectedEntityType === 'CONSTRAINT' ? (
              <ConstraintInspectorContent entity={selectedEntity} />
            ) : selectedEntityType === 'TIMELINE' ? (
              <TimelineInspectorContent entity={selectedEntity} />
            ) : selectedEntityType === 'OBJECTIVE' ? (
              <ObjectiveInspectorContent entity={selectedEntity} />
            ) : (
               <div className="text-sm text-text-muted">Unknown Entity Type</div>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function AlternativeInspectorContent({ entity }: { entity: any }) {
  return (
    <div className="flex flex-col gap-8 animate-in fade-in zoom-in-95 duration-200">
      <div className="flex flex-col gap-2">
        <div className="flex justify-between items-center">
           <div className="text-[10px] uppercase font-mono text-signal-ranking tracking-widest bg-signal-ranking/10 border border-signal-ranking/30 px-2 py-0.5 rounded-sm">
             RANK #{entity.rank}
           </div>
           {entity.status === 'SELECTED' && (
             <div className="flex items-center gap-1 text-[10px] font-mono text-signal-authority">
               <CheckCircle className="w-3 h-3" /> SELECTED
             </div>
           )}
        </div>
        
        <h3 className="text-2xl font-light text-text-display tracking-wide mt-2">{entity.title}</h3>
        <div className="text-xs font-mono text-text-technical flex justify-between">
          <span>ID: {entity.id}</span>
          <span>{entity.isDominated ? 'DOMINATED' : 'FRONTIER'}</span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <MetricCard label="Utility" value={entity.utility.toFixed(2)} color="text-signal-scientific" />
        <MetricCard label="Risk" value={entity.risk.toFixed(2)} color={entity.risk > 0.4 ? 'text-signal-warning' : 'text-signal-scientific'} />
        <MetricCard label="Confidence" value={`${(entity.confidence * 100).toFixed(0)}%`} color="text-signal-cognitive" />
        <MetricCard label="Feasibility" value={(entity.feasibility * 100).toFixed(0)} color="text-signal-authority" />
      </div>

      <div className="flex flex-col gap-3">
        <div className="text-[10px] uppercase font-mono text-text-micro tracking-widest border-b border-[var(--eureka-spatial-hairline)] pb-2">
          Scientific Metrics
        </div>
        <div className="flex justify-between items-center">
          <span className="text-xs text-text-label">P-Value</span>
          <span className="text-xs font-mono text-signal-scientific">{entity.scientificMetrics.pValue}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-xs text-text-label">Variance</span>
          <span className="text-xs font-mono text-text-technical">{entity.scientificMetrics.variance}</span>
        </div>
      </div>

      <div className="mt-auto pt-6 border-t border-[var(--eureka-spatial-hairline)] flex flex-col gap-2">
        <button className="flex items-center justify-center gap-2 w-full py-2 bg-surface border border-[var(--eureka-spatial-hairline)] hover:border-signal-cognitive text-xs font-mono text-text-section transition-colors">
          <GitMerge className="w-3 h-3" />
          TRACE DECISION PATH
        </button>
      </div>
    </div>
  );
}

function EvidenceInspectorContent({ entity }: { entity: any }) {
  return (
    <div className="flex flex-col gap-8 animate-in fade-in zoom-in-95 duration-200">
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2 text-[10px] uppercase font-mono text-text-technical tracking-widest">
           <FileText className="w-3 h-3" /> EVIDENCE NODE
        </div>
        <h3 className="text-xl font-light text-text-display tracking-wide">{entity.title}</h3>
        <div className="text-xs font-mono text-text-technical">ID: {entity.id}</div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <MetricCard label="Confidence" value={`${(entity.confidence * 100).toFixed(0)}%`} color="text-signal-cognitive" />
        <MetricCard label="Source" value={entity.source} color="text-text-display" />
      </div>
      <div className="flex flex-col gap-3">
        <div className="text-[10px] uppercase font-mono text-text-micro tracking-widest border-b border-[var(--eureka-spatial-hairline)] pb-2">
          Provenance
        </div>
        <div className="text-xs font-mono text-text-technical">{entity.provenance}</div>
        <div className="text-xs text-text-muted mt-2">{new Date(entity.timestamp).toLocaleString()}</div>
      </div>
    </div>
  );
}

function ConstraintInspectorContent({ entity }: { entity: any }) {
  return (
    <div className="flex flex-col gap-8 animate-in fade-in zoom-in-95 duration-200">
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2 text-[10px] uppercase font-mono text-signal-authority tracking-widest">
           <Anchor className="w-3 h-3" /> {entity.isHard ? 'HARD CONSTRAINT' : 'SOFT CONSTRAINT'}
        </div>
        <h3 className="text-xl font-light text-text-display tracking-wide">{entity.title}</h3>
        <div className="text-xs font-mono text-text-technical">ID: {entity.id}</div>
      </div>
      <div className="grid grid-cols-1 gap-4">
        <MetricCard label="Logical Operator" value={`${entity.operator} ${entity.threshold}`} color="text-signal-semantic" />
      </div>
      <div className="flex flex-col gap-3">
         <div className="text-[10px] uppercase font-mono text-text-micro tracking-widest border-b border-[var(--eureka-spatial-hairline)] pb-2">
          Description
        </div>
        <div className="text-xs text-text-label leading-relaxed">{entity.description}</div>
      </div>
    </div>
  );
}

function TimelineInspectorContent({ entity }: { entity: any }) {
  return (
    <div className="flex flex-col gap-8 animate-in fade-in zoom-in-95 duration-200">
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2 text-[10px] uppercase font-mono text-text-technical tracking-widest">
           <Clock className="w-3 h-3" /> TIMELINE EVENT
        </div>
        <h3 className="text-xl font-light text-text-display tracking-wide">{entity.title}</h3>
        <div className="text-xs font-mono text-text-technical">{new Date(entity.timestamp).toLocaleString()}</div>
      </div>
      <div className="flex flex-col gap-3">
         <div className="text-[10px] uppercase font-mono text-text-micro tracking-widest border-b border-[var(--eureka-spatial-hairline)] pb-2">
          Stage & Description
        </div>
        <div className="text-xs font-mono text-signal-cognitive">{entity.stage}</div>
        <div className="text-xs text-text-label leading-relaxed mt-2">{entity.description}</div>
      </div>
    </div>
  );
}

function ObjectiveInspectorContent({ entity }: { entity: any }) {
  return (
    <div className="flex flex-col gap-8 animate-in fade-in zoom-in-95 duration-200">
      <div className="flex flex-col gap-2">
        <div className="text-[10px] uppercase font-mono text-signal-authority tracking-widest">
           EUREKA CONTEXT
        </div>
        <h3 className="text-xl font-light text-text-display tracking-wide">{entity.title}</h3>
        <div className="text-xs font-mono text-text-technical">ID: {entity.id} | {entity.caseId}</div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <MetricCard label="EM Stage" value={entity.emStage} color="text-signal-cognitive" />
        <MetricCard label="Governance" value={entity.governanceState} color="text-signal-warning" />
      </div>
    </div>
  );
}

function MetricCard({ label, value, color }: { label: string, value: string | number, color: string }) {
  return (
    <div className="flex flex-col p-3 bg-surface border border-[var(--eureka-spatial-hairline)] rounded-sm">
      <span className="text-[10px] uppercase font-mono text-text-technical mb-1">{label}</span>
      <span className={cn("text-lg font-light tracking-wider truncate", color)} title={String(value)}>{value}</span>
    </div>
  );
}
