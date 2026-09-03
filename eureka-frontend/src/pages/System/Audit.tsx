import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/Card";
import { Clock, ShieldCheck, FileKey, User, Bot, AlertTriangle } from "lucide-react";

export default function Audit() {
  const auditLogs = [
    { id: "evt-092", time: "10:32:42", type: "EXECUTION", actor: "System", description: "Action 'Deploy Strategy B' submitted to orchestrator.", icon: AlertTriangle, color: "text-authorized" },
    { id: "evt-091", time: "10:32:41", type: "AUTHORIZATION", actor: "System", description: "Artifact AF-249 UNFROZEN.", icon: FileKey, color: "text-authorized" },
    { id: "evt-090", time: "10:32:40", type: "HUMAN_EXTERNAL", actor: "Admin (CISO)", description: "Cryptographic signature validated for AF-249.", icon: User, color: "text-governance" },
    { id: "evt-089", time: "10:31:12", type: "FREEZE", actor: "Governance", description: "Prescription frozen. Awaiting HUMAN_EXTERNAL authority.", icon: ShieldCheck, color: "text-frozen" },
    { id: "evt-088", time: "10:31:12", type: "PRESCRIPTION", actor: "Foundation", description: "Prescription generated from Selection S-02.", icon: Clock, color: "text-scientific" },
    { id: "evt-087", time: "10:31:09", type: "SELECTION", actor: "Foundation", description: "Alternative ALT-B selected (Rank 1).", icon: Clock, color: "text-scientific" },
    { id: "evt-086", time: "10:31:08", type: "RANKING", actor: "Foundation", description: "Ranking matrix generated (4 alternatives).", icon: Clock, color: "text-scientific" },
    { id: "evt-085", time: "10:31:07", type: "EVALUATION", actor: "Foundation", description: "Scientific evaluation completed.", icon: Clock, color: "text-scientific" },
    { id: "evt-084", time: "10:31:06", type: "SEMANTICS", actor: "System", description: "Objective Predicate formally validated against ACFL.", icon: Clock, color: "text-text-muted" },
    { id: "evt-083", time: "10:31:05", type: "COGNITIVE", actor: "DeepSeek (R1)", description: "Agent response parsed and AST generated.", icon: Bot, color: "text-cognitive" },
    { id: "evt-082", time: "10:31:02", type: "INPUT", actor: "User", description: "Problem statement submitted in Natural Language.", icon: User, color: "text-text-muted" },
  ];

  return (
    <div className="flex flex-col h-full p-8 bg-canvas">
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight text-text">Audit Trail</h1>
        <p className="text-text-muted mt-1 text-sm">Immutable cryptographic log of all state transitions and authority events.</p>
      </div>

      <Card className="bg-surface-elevated border-border flex-1 overflow-hidden flex flex-col">
        <CardHeader className="border-b border-border">
          <CardTitle className="text-sm font-medium uppercase tracking-wider text-text-muted">Global Event Timeline</CardTitle>
        </CardHeader>
        <CardContent className="p-0 overflow-y-auto flex-1">
          <div className="divide-y divide-border">
            {auditLogs.map((log) => (
              <div key={log.id} className="p-4 hover:bg-surface/50 transition-colors flex items-start gap-4">
                <div className="mt-1">
                  <log.icon className={`h-5 w-5 ${log.color}`} />
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium text-sm text-text">{log.type}</span>
                    <span className="font-mono text-xs text-text-muted">{log.time}</span>
                  </div>
                  <p className="text-sm text-text-secondary">{log.description}</p>
                  <div className="mt-2 flex items-center gap-3 font-mono text-xs text-text-muted">
                    <span>ID: {log.id}</span>
                    <span>Actor: {log.actor}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}