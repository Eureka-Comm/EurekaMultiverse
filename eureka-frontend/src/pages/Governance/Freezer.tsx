import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { Lock, Unlock, AlertTriangle, ShieldCheck } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { useNavigate } from "react-router-dom";

export default function Freezer() {
  const navigate = useNavigate();

  return (
    <div className="flex flex-col h-full p-8 bg-canvas">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-text">System Freezer</h1>
          <p className="text-text-muted mt-1 text-sm">Hard execution halt pending human-in-the-loop authority.</p>
        </div>
        <div className="flex gap-2">
          <Badge variant="frozen" className="animate-pulse">FROZEN</Badge>
          <Badge variant="neutral" className="bg-surface border-border">DEMO DATA</Badge>
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center">
        <Card className="w-full max-w-2xl bg-surface-elevated border-frozen shadow-[0_0_50px_rgba(var(--eureka-frozen-rgb),0.1)]">
          <CardHeader className="border-b border-border/50 text-center pb-8 pt-10">
            <div className="mx-auto h-20 w-20 rounded-full bg-frozen/10 flex items-center justify-center mb-6">
              <Lock className="h-10 w-10 text-frozen" />
            </div>
            <CardTitle className="text-3xl font-bold text-text mb-2">EXECUTION BLOCKED</CardTitle>
            <p className="text-text-secondary text-sm">Prescription payload generated but held in quarantine.</p>
          </CardHeader>
          <CardContent className="p-8">
            <div className="bg-surface rounded-lg p-6 border border-border mb-8">
              <div className="flex items-start gap-4">
                <AlertTriangle className="h-5 w-5 text-frozen mt-0.5" />
                <div>
                  <h3 className="text-sm font-medium text-text mb-1">Human Authority Required</h3>
                  <p className="text-sm text-text-secondary">
                    Governance rule <span className="font-mono text-governance">STRICT_SEMANTIC_GATES</span> dictates that any payload modifying production infrastructure must receive cryptographic signature from a verified human operator before execution.
                  </p>
                </div>
              </div>
            </div>

            <div className="flex gap-4">
              <Button variant="ghost" className="flex-1 bg-surface border border-border text-text hover:bg-surface-elevated">
                View Traceability Graph
              </Button>
              <Button className="flex-1 bg-governance text-black hover:bg-governance/90" onClick={() => navigate('/governance/authority')}>
                Request Authority <ShieldCheck className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}