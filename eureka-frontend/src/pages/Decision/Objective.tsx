import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { Target, ListChecks, ArrowRight, ShieldCheck } from "lucide-react";

export default function Objective() {
  return (
    <div className="flex flex-col h-full p-8 bg-canvas">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-text">Decision Objective</h1>
          <p className="text-text-muted mt-1 text-sm">Formalized goal state and constraints derived from user input.</p>
        </div>
        <div className="flex gap-2">
          <Badge variant="scientific">FORMALIZED</Badge>
          <Badge variant="neutral" className="bg-surface border-border">DEMO DATA</Badge>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        <Card className="bg-surface-elevated border-border col-span-2">
          <CardHeader className="border-b border-border">
            <CardTitle className="text-lg flex items-center gap-2">
              <Target className="h-5 w-5 text-cognitive" />
              Primary Objective Function
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            <div className="bg-surface p-6 rounded-lg border border-border font-mono text-sm text-text mb-6 shadow-inner">
              <span className="text-cognitive">MAXIMIZE</span>( Operational_Efficiency ) <br />
              <span className="text-text-muted ml-4">SUBJECT TO</span> <br />
              <span className="text-scientific ml-8">Risk_Exposure &lt;= 0.15</span> <br />
              <span className="text-scientific ml-8">Budget_Allocation &lt;= $1.5M</span>
            </div>
            
            <h3 className="text-sm font-medium tracking-widest text-text-muted uppercase mb-4">Semantic Constraints</h3>
            <ul className="space-y-3">
              <li className="flex items-center gap-3 p-3 bg-surface rounded border border-border">
                <ShieldCheck className="h-4 w-4 text-scientific" />
                <span className="text-sm text-text">Must comply with ISO-27001 guidelines for data handling.</span>
                <Badge variant="neutral" className="ml-auto">C-01</Badge>
              </li>
              <li className="flex items-center gap-3 p-3 bg-surface rounded border border-border">
                <ShieldCheck className="h-4 w-4 text-scientific" />
                <span className="text-sm text-text">Timeline for implementation cannot exceed Q3 2026.</span>
                <Badge variant="neutral" className="ml-auto">C-02</Badge>
              </li>
            </ul>
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card className="bg-surface border-border">
            <CardHeader className="border-b border-border">
              <CardTitle className="text-sm tracking-widest text-text-muted uppercase flex items-center gap-2">
                <ListChecks className="h-4 w-4" />
                Variables (V)
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 space-y-4">
              <div>
                <div className="flex justify-between items-center mb-1">
                  <span className="text-sm font-medium text-text">Operational_Efficiency</span>
                  <Badge variant="neutral">Target</Badge>
                </div>
                <p className="text-xs text-text-muted">Composite metric representing throughput vs cost.</p>
              </div>
              <div className="border-t border-border pt-4">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-sm font-medium text-text">Risk_Exposure</span>
                  <Badge variant="neutral">Constraint</Badge>
                </div>
                <p className="text-xs text-text-muted">Probability of system downtime during migration.</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}