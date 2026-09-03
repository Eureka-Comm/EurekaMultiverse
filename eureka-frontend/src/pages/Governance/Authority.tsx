import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { ShieldCheck, FileSignature, Key, ArrowRight } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { useNavigate } from "react-router-dom";

export default function Authority() {
  const navigate = useNavigate();
  const [signed, setSigned] = useState(false);

  return (
    <div className="flex flex-col h-full p-8 bg-canvas">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-text">Authority Chain</h1>
          <p className="text-text-muted mt-1 text-sm">Human-in-the-loop cryptographic authorization.</p>
        </div>
        <div className="flex gap-2">
          {signed ? <Badge variant="authorized">AUTHORIZED</Badge> : <Badge variant="governance">AWAITING SIGNATURE</Badge>}
          <Badge variant="neutral" className="bg-surface border-border">DEMO DATA</Badge>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6 flex-1">
        <Card className="bg-surface-elevated border-border flex flex-col justify-between">
          <div>
            <CardHeader className="border-b border-border">
              <CardTitle className="text-sm uppercase tracking-widest text-text-muted flex items-center gap-2">
                <ShieldCheck className="h-4 w-4" />
                Review Payload (AF-249)
              </CardTitle>
            </CardHeader>
            <CardContent className="p-8">
              <div className="p-4 bg-surface border border-border rounded-lg mb-8">
                <pre className="text-sm font-mono text-text-secondary overflow-x-auto">
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

              <div className="space-y-4">
                <div className="flex items-center gap-3 p-3 rounded bg-surface border border-border">
                  <Badge variant="scientific">PASS</Badge>
                  <span className="text-sm text-text-secondary">Semantic Validation completed.</span>
                </div>
                <div className="flex items-center gap-3 p-3 rounded bg-surface border border-border">
                  <Badge variant="scientific">PASS</Badge>
                  <span className="text-sm text-text-secondary">Scientific Traceability unbroken.</span>
                </div>
              </div>
            </CardContent>
          </div>
        </Card>

        <Card className="bg-surface border-border flex flex-col justify-between">
          <div>
            <CardHeader className="border-b border-border">
              <CardTitle className="text-sm uppercase tracking-widest text-text-muted flex items-center gap-2">
                <FileSignature className="h-4 w-4" />
                Digital Signature
              </CardTitle>
            </CardHeader>
            <CardContent className="p-8">
              <div className="flex flex-col items-center justify-center text-center mb-8 mt-4">
                <div className={`h-16 w-16 rounded-full flex items-center justify-center mb-4 transition-colors ${signed ? 'bg-authorized/10' : 'bg-surface border border-border'}`}>
                  <Key className={`h-8 w-8 ${signed ? 'text-authorized' : 'text-text-muted'}`} />
                </div>
                <h3 className="text-lg font-medium text-text mb-1">CISO Authentication</h3>
                <p className="text-sm text-text-secondary max-w-xs">
                  Provide your cryptographic signature to unfreeze the system and authorize action.
                </p>
              </div>

              {!signed ? (
                <Button className="w-full bg-governance text-black hover:bg-governance/90 h-12" onClick={() => setSigned(true)}>
                  Sign & Authorize
                </Button>
              ) : (
                <div className="p-4 rounded border border-authorized/50 bg-authorized/5 text-center">
                  <p className="text-sm font-mono text-authorized mb-2">SIGNATURE VERIFIED</p>
                  <p className="text-xs text-text-muted break-all">0x8f2a...9b4c</p>
                </div>
              )}
            </CardContent>
          </div>
          
          <div className="p-6 border-t border-border">
            <Button 
              className="w-full bg-authorized text-black hover:bg-authorized/90 disabled:opacity-50" 
              disabled={!signed}
              onClick={() => navigate('/governance/actioner')}
            >
              Proceed to Actioner <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
}