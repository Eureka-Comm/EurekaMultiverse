import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { Cpu, Server, Activity, Database, GitMerge } from "lucide-react";

export default function Runtime() {
  return (
    <div className="flex flex-col h-full p-8 bg-canvas">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-text">Runtime Architecture</h1>
          <p className="text-text-muted mt-1 text-sm">System topology and execution engine health.</p>
        </div>
        <Badge variant="scientific" className="animate-pulse">ONLINE</Badge>
      </div>

      <div className="grid grid-cols-3 gap-6 flex-1">
        
        {/* Topology Map */}
        <Card className="bg-surface-elevated border-border col-span-2 flex flex-col">
          <CardHeader className="border-b border-border">
            <CardTitle className="text-sm uppercase tracking-widest text-text-muted flex items-center gap-2">
              <Server className="h-4 w-4" />
              Service Topology
            </CardTitle>
          </CardHeader>
          <CardContent className="p-8 flex-1 flex items-center justify-center relative">
            <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-surface to-transparent opacity-50"></div>
            
            <div className="relative w-full max-w-2xl">
              <div className="grid grid-cols-3 gap-8 text-center">
                
                {/* Node 1 */}
                <div className="flex flex-col items-center">
                  <div className="h-20 w-20 rounded-xl bg-surface border border-cognitive/50 flex items-center justify-center mb-4 relative group">
                    <div className="absolute -inset-2 bg-cognitive/10 rounded-xl blur-lg group-hover:bg-cognitive/20 transition-all"></div>
                    <Cpu className="h-8 w-8 text-cognitive relative z-10" />
                  </div>
                  <span className="font-mono text-sm text-text">Cognitive Engine</span>
                  <span className="text-xs text-text-muted">LLM Orchestrator</span>
                </div>

                {/* Node 2 */}
                <div className="flex flex-col items-center mt-12">
                  <div className="h-20 w-20 rounded-xl bg-surface border border-scientific/50 flex items-center justify-center mb-4 relative group">
                    <div className="absolute -inset-2 bg-scientific/10 rounded-xl blur-lg group-hover:bg-scientific/20 transition-all"></div>
                    <GitMerge className="h-8 w-8 text-scientific relative z-10" />
                  </div>
                  <span className="font-mono text-sm text-text">Semantics Core</span>
                  <span className="text-xs text-text-muted">ACFL Compiler</span>
                </div>

                {/* Node 3 */}
                <div className="flex flex-col items-center">
                  <div className="h-20 w-20 rounded-xl bg-surface border border-authorized/50 flex items-center justify-center mb-4 relative group">
                    <div className="absolute -inset-2 bg-authorized/10 rounded-xl blur-lg group-hover:bg-authorized/20 transition-all"></div>
                    <Database className="h-8 w-8 text-authorized relative z-10" />
                  </div>
                  <span className="font-mono text-sm text-text">Action Bus</span>
                  <span className="text-xs text-text-muted">State Publisher</span>
                </div>

              </div>
              
              {/* Connecting lines */}
              <div className="absolute top-10 left-24 right-24 h-0.5 bg-gradient-to-r from-cognitive via-scientific to-authorized opacity-30 -z-10"></div>
            </div>
          </CardContent>
        </Card>

        {/* Telemetry */}
        <div className="space-y-6">
          <Card className="bg-surface border-border">
            <CardHeader className="border-b border-border">
              <CardTitle className="text-sm uppercase tracking-widest text-text-muted flex items-center gap-2">
                <Activity className="h-4 w-4" />
                Live Telemetry
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 space-y-4 font-mono text-sm">
              <div className="flex justify-between items-center border-b border-border pb-2">
                <span className="text-text-muted">Global Latency</span>
                <span className="text-text">42ms</span>
              </div>
              <div className="flex justify-between items-center border-b border-border pb-2">
                <span className="text-text-muted">Memory Usage</span>
                <span className="text-text">1.2GB</span>
              </div>
              <div className="flex justify-between items-center border-b border-border pb-2">
                <span className="text-text-muted">Active Workers</span>
                <span className="text-text">8 / 16</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-text-muted">Error Rate</span>
                <span className="text-scientific">0.01%</span>
              </div>
            </CardContent>
          </Card>
        </div>

      </div>
    </div>
  );
}