import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { Bot, Zap, Cpu, Settings2 } from "lucide-react";

export default function Agents() {
  return (
    <div className="flex flex-col h-full p-8 bg-canvas">
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight text-text">Agent Fleet</h1>
        <p className="text-text-muted mt-1 text-sm">Manage the active cognitive providers and their configurations.</p>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <Card className="bg-surface-elevated border-cognitive hover:border-cognitive/80 transition-colors">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-lg flex items-center gap-2">
              <Bot className="h-5 w-5 text-cognitive" />
              DeepSeek Reasoner (R1)
            </CardTitle>
            <Badge variant="cognitive">ACTIVE</Badge>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-text-secondary">Primary cognitive engine for complex analytical reasoning and semantic formalization.</p>
            <div className="flex gap-4 text-xs font-mono text-text-muted">
              <span className="flex items-center gap-1"><Zap className="h-3 w-3"/> ~2.4s latency</span>
              <span className="flex items-center gap-1"><Cpu className="h-3 w-3"/> API</span>
            </div>
            <div className="mt-4 pt-4 border-t border-border flex justify-end">
              <button className="text-xs flex items-center gap-1 text-text-muted hover:text-text transition-colors">
                <Settings2 className="h-3 w-3" /> Configure
              </button>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-surface border-border hover:border-text-muted transition-colors opacity-80">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-lg flex items-center gap-2">
              <Bot className="h-5 w-5 text-scientific" />
              Local Mock Engine
            </CardTitle>
            <Badge variant="neutral">STANDBY</Badge>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-text-secondary">Deterministic mock engine used for zero-cost testing and UI verification.</p>
            <div className="flex gap-4 text-xs font-mono text-text-muted">
              <span className="flex items-center gap-1"><Zap className="h-3 w-3"/> ~0ms latency</span>
              <span className="flex items-center gap-1"><Cpu className="h-3 w-3"/> In-Memory</span>
            </div>
            <div className="mt-4 pt-4 border-t border-border flex justify-end">
              <button className="text-xs flex items-center gap-1 text-text-muted hover:text-text transition-colors">
                <Settings2 className="h-3 w-3" /> Configure
              </button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}