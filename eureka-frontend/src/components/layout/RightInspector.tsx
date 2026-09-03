import { useUIStore } from "../../store/uiStore";
import { Button } from "../ui/Button";
import { X, Activity, ShieldAlert, Zap, Lock } from "lucide-react";
import { cn } from "../../lib/utils";
import { Badge } from "../ui/Badge";
import { motion, AnimatePresence } from "framer-motion";

const STATUS_COLORS = {
  cognitive: "text-cognitive",
  scientific: "text-scientific",
  governance: "text-governance",
  authorized: "text-authorized",
  blocked: "text-blocked",
};

export function RightInspector() {
  const { isInspectorOpen, selectedDecision, closeInspector } = useUIStore();

  return (
    <AnimatePresence>
      {isInspectorOpen && (
        <motion.div 
          initial={{ width: 0, opacity: 0 }}
          animate={{ width: 384, opacity: 1 }}
          exit={{ width: 0, opacity: 0 }}
          transition={{ duration: 0.3, ease: "easeInOut" }}
          className="h-full bg-surface-elevated border-l border-[var(--eureka-border)] flex flex-col overflow-hidden shrink-0"
        >
          {selectedDecision ? (
            <>
              {/* Header */}
              <div className="p-4 border-b border-[var(--eureka-border)] flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Activity className="w-4 h-4 text-text-muted" />
                  <h2 className="text-xs font-mono text-text-secondary uppercase tracking-widest">Context Inspector</h2>
                </div>
                <button onClick={closeInspector} className="text-text-muted hover:text-text-primary">
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Content */}
              <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-8">
                {/* Title and Status */}
                <div className="flex flex-col gap-3">
                  <Badge variant="outline" className={cn("w-max text-[10px] uppercase", STATUS_COLORS[selectedDecision.status as keyof typeof STATUS_COLORS] || "text-text-muted")}>
                    {selectedDecision.status}
                  </Badge>
                  <h3 className="text-xl font-bold text-text-primary">{selectedDecision.title}</h3>
                  <div className="text-xs font-mono text-text-muted">ID: {selectedDecision.id}</div>
                </div>

                {/* Risk Score */}
                <div className="flex flex-col gap-2">
                  <div className="flex justify-between items-center text-xs font-mono uppercase tracking-wider text-text-secondary">
                    <span>Risk Confidence</span>
                    <span className={selectedDecision.riskScore > 80 ? "text-blocked" : "text-scientific"}>
                      {selectedDecision.riskScore}%
                    </span>
                  </div>
                  <div className="h-1 bg-surface-glass rounded-full overflow-hidden">
                    <div 
                      className={cn("h-full", selectedDecision.riskScore > 80 ? "bg-blocked" : "bg-scientific")}
                      style={{ width: `${selectedDecision.riskScore}%` }}
                    />
                  </div>
                </div>

                {/* Key Parameters (Stylized JSON) */}
                <div className="flex flex-col gap-2">
                  <div className="text-xs font-mono uppercase tracking-wider text-text-secondary">Parameters</div>
                  <div className="bg-canvas border border-[var(--eureka-border)] rounded-md p-4 font-mono text-xs">
                    {Object.entries(selectedDecision.parameters).map(([key, value]) => (
                      <div key={key} className="flex gap-4 mb-2 last:mb-0">
                        <span className="text-scientific shrink-0">"{key}"</span>
                        <span className="text-text-muted">:</span>
                        <span className="text-authorized break-all">
                          {typeof value === 'string' ? `"${value}"` : value}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex flex-col gap-2 mt-auto">
                  <div className="text-xs font-mono uppercase tracking-wider text-text-secondary mb-2">Override Directives</div>
                  <div className="grid grid-cols-2 gap-2">
                    <Button variant="outline" className="text-governance border-governance/30 hover:bg-governance/10 justify-start h-9 text-xs">
                      <ShieldAlert className="w-3 h-3 mr-2" /> Approve
                    </Button>
                    <Button variant="outline" className="text-frozen border-frozen/30 hover:bg-frozen/10 justify-start h-9 text-xs">
                      <Lock className="w-3 h-3 mr-2" /> Freeze
                    </Button>
                    <Button variant="outline" className="col-span-2 text-authorized border-authorized/30 hover:bg-authorized/10 justify-center h-9 text-xs">
                      <Zap className="w-3 h-3 mr-2" /> Force Execution
                    </Button>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-text-muted text-sm">
              No decision selected.
            </div>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
