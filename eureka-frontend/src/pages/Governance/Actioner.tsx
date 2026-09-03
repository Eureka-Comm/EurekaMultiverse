import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { Zap, Terminal, CheckCircle2 } from "lucide-react";

export default function Actioner() {
  return (
    <div className="flex flex-col h-full p-8 bg-canvas">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-text">Actioner</h1>
          <p className="text-text-muted mt-1 text-sm">Execution gateway bridging intelligence to real-world infrastructure.</p>
        </div>
        <div className="flex gap-2">
          <Badge variant="authorized">EXECUTED</Badge>
          <Badge variant="neutral" className="bg-surface border-border">DEMO DATA</Badge>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6 flex-1">
        <Card className="bg-surface-elevated border-border flex flex-col">
          <CardHeader className="border-b border-border">
            <CardTitle className="text-sm uppercase tracking-widest text-text-muted flex items-center gap-2">
              <Terminal className="h-4 w-4" />
              Execution Log
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0 flex-1 bg-surface font-mono text-xs overflow-y-auto">
            <div className="p-4 space-y-2 text-text-muted">
              <div className="flex gap-4"><span className="text-scientific">10:32:41.012</span><span>[INFO] Authority signature verified. Unfreezing system.</span></div>
              <div className="flex gap-4"><span className="text-scientific">10:32:41.055</span><span>[INFO] Connecting to external orchestrator (Kubernetes_Prod).</span></div>
              <div className="flex gap-4"><span className="text-scientific">10:32:41.102</span><span>[INFO] Dispatching payload AF-249.</span></div>
              <div className="flex gap-4"><span className="text-scientific">10:32:41.890</span><span>[WARN] Target namespace scaling up...</span></div>
              <div className="flex gap-4"><span className="text-scientific">10:32:42.112</span><span>[INFO] Deployment acknowledged.</span></div>
              <div className="flex gap-4"><span className="text-authorized">10:32:42.500</span><span className="text-text">SUCCESS: Execution confirmed by remote host.</span></div>
            </div>
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card className="bg-surface border-border">
            <CardHeader className="border-b border-border">
              <CardTitle className="text-sm uppercase tracking-widest text-text-muted flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4" />
                Action Summary
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              <div className="h-16 w-16 rounded-full bg-authorized/10 flex items-center justify-center mb-6">
                <Zap className="h-8 w-8 text-authorized" />
              </div>
              <h2 className="text-xl font-bold text-text mb-2">DEPLOY_STRATEGY (ALT-B)</h2>
              <p className="text-text-secondary text-sm mb-6">
                The decision has been successfully executed in the target environment. The loop is now closed.
              </p>
              
              <div className="space-y-3">
                <div className="flex justify-between text-sm border-b border-border pb-2">
                  <span className="text-text-muted">Target</span>
                  <span className="font-mono text-text">PRODUCTION_ENV</span>
                </div>
                <div className="flex justify-between text-sm border-b border-border pb-2">
                  <span className="text-text-muted">Latency</span>
                  <span className="font-mono text-text">1.4s</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-text-muted">Trace ID</span>
                  <span className="font-mono text-text">AF-249</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}