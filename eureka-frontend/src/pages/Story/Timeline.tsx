import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { GitCommit, Search } from "lucide-react";

export default function Timeline() {
  const events = [
    { id: "01", time: "10:31:02", state: "INPUT", actor: "User", desc: "Submitted NL Request" },
    { id: "02", time: "10:31:05", state: "COGNITIVE", actor: "Agent", desc: "Generated abstract proposal" },
    { id: "03", time: "10:31:06", state: "SEMANTICS", actor: "System", desc: "Formalized objective predicate" },
    { id: "04", time: "10:31:07", state: "SCIENCE", actor: "Engine", desc: "Evaluated truth values" },
    { id: "05", time: "10:31:08", state: "RANKING", actor: "Engine", desc: "Produced candidate matrix" },
    { id: "06", time: "10:31:09", state: "SELECTION", actor: "Rule", desc: "Selected highest utility" },
    { id: "07", time: "10:31:12", state: "PRESCRIPTION", actor: "System", desc: "Generated payload" },
    { id: "08", time: "10:31:12", state: "FREEZE", actor: "Governance", desc: "Execution blocked" },
  ];

  return (
    <div className="flex flex-col h-full p-8 bg-canvas">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-text">Decision Timeline</h1>
          <p className="text-text-muted mt-1 text-sm">Chronological view of the decision pipeline state transitions.</p>
        </div>
        <Badge variant="neutral" className="bg-surface border-border">DEMO DATA</Badge>
      </div>

      <Card className="bg-surface border-border flex-1 flex flex-col">
        <CardHeader className="border-b border-border bg-surface-elevated">
          <CardTitle className="text-sm uppercase tracking-widest text-text-muted flex items-center gap-2">
            <GitCommit className="h-4 w-4" />
            Transition History
          </CardTitle>
        </CardHeader>
        <CardContent className="p-8 flex-1 overflow-y-auto">
          <div className="space-y-0">
            {events.map((e, idx) => (
              <div key={e.id} className="flex gap-6 group">
                {/* Timeline Line */}
                <div className="flex flex-col items-center">
                  <div className="h-4 w-4 rounded-full bg-surface border-2 border-text-muted group-hover:border-text transition-colors mt-1"></div>
                  {idx !== events.length - 1 && <div className="w-0.5 h-16 bg-border group-hover:bg-text-muted transition-colors mt-2"></div>}
                </div>
                
                {/* Content */}
                <div className="pb-8 flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="font-mono text-sm text-text-muted">{e.time}</span>
                    <Badge variant={e.state === 'FREEZE' ? 'frozen' : e.state === 'COGNITIVE' ? 'cognitive' : e.state === 'SCIENCE' ? 'scientific' : 'neutral'}>
                      {e.state}
                    </Badge>
                  </div>
                  <div className="bg-surface-elevated p-4 rounded border border-border text-sm">
                    <div className="flex justify-between">
                      <span className="text-text">{e.desc}</span>
                      <span className="text-text-muted">By: {e.actor}</span>
                    </div>
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