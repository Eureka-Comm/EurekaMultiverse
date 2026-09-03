import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { FileText, ArrowRight, Clock } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { useNavigate } from "react-router-dom";

export default function Prescription() {
  const navigate = useNavigate();

  return (
    <div className="flex flex-col h-full p-8 bg-canvas">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-text">Prescription</h1>
          <p className="text-text-muted mt-1 text-sm">Formal instruction generated from the selected alternative.</p>
        </div>
        <div className="flex gap-2">
          <Badge variant="scientific">PRESCRIBED</Badge>
          <Badge variant="neutral" className="bg-surface border-border">DEMO DATA</Badge>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6 flex-1">
        <Card className="bg-surface-elevated border-border">
          <CardHeader className="border-b border-border">
            <CardTitle className="text-sm uppercase tracking-widest text-text-muted flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Proposed Action
            </CardTitle>
          </CardHeader>
          <CardContent className="p-8">
            <h2 className="text-2xl font-bold text-text mb-4">Deploy Strategy B (ALT-B)</h2>
            <p className="text-text-secondary mb-8 leading-relaxed">
              Based on the scientific evaluation against the formal objective predicate, ALT-B maximizes operational efficiency (Utility: 0.91) while strictly satisfying the risk exposure limit (0.12 ≤ 0.15) and budget constraints ($1.2M ≤ $1.5M).
            </p>
            
            <div className="p-4 bg-surface border border-border rounded-lg mb-8">
              <h3 className="text-xs font-mono text-text-muted uppercase mb-3 tracking-widest">Execution Payload</h3>
              <pre className="text-sm font-mono text-scientific overflow-x-auto">
{`{
  "action_type": "DEPLOY_STRATEGY",
  "target": "PRODUCTION_ENV",
  "parameters": {
    "strategy_id": "ST-092-B",
    "budget_alloc": 1200000,
    "risk_tolerance": 0.15
  },
  "justification_trace": "AF-249"
}`}
              </pre>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-surface border-border flex flex-col justify-between">
          <div>
            <CardHeader className="border-b border-border">
              <CardTitle className="text-sm uppercase tracking-widest text-text-muted flex items-center gap-2">
                <Clock className="h-4 w-4" />
                Status
              </CardTitle>
            </CardHeader>
            <CardContent className="p-8 text-center flex flex-col items-center justify-center mt-12">
              <div className="h-16 w-16 rounded-full bg-frozen/10 border border-frozen/30 flex items-center justify-center mb-6">
                <Clock className="h-8 w-8 text-frozen" />
              </div>
              <h2 className="text-xl font-bold text-text mb-2">AWAITING GOVERNANCE</h2>
              <p className="text-text-secondary text-sm max-w-sm">
                The prescription has been generated but execution is currently blocked. The system must transition to the FREEZE state to await external authority confirmation.
              </p>
            </CardContent>
          </div>
          
          <div className="p-6 border-t border-border">
            <Button className="w-full bg-frozen text-black hover:bg-frozen/90" onClick={() => navigate('/governance/freezer')}>
              Trigger System Freeze <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
}