import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { Scale, CheckCircle2, AlertTriangle, ShieldCheck } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { useNavigate } from "react-router-dom";

export default function Selection() {
  const navigate = useNavigate();

  return (
    <div className="flex flex-col h-full p-8 bg-canvas">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-text">Selection</h1>
          <p className="text-text-muted mt-1 text-sm">Adjudication of the ranked alternatives based on governance rules.</p>
        </div>
        <div className="flex gap-2">
          <Badge variant="scientific">RANKING AVAILABLE</Badge>
          <Badge variant="neutral" className="bg-surface border-border">DEMO DATA</Badge>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6 flex-1">
        <Card className="bg-surface-elevated border-border flex flex-col justify-between">
          <div>
            <CardHeader className="border-b border-border">
              <CardTitle className="text-sm uppercase tracking-widest text-text-muted flex items-center gap-2">
                <Scale className="h-4 w-4" />
                Selection Authority
              </CardTitle>
            </CardHeader>
            <CardContent className="p-8 text-center flex flex-col items-center justify-center min-h-[300px]">
              <div className="h-16 w-16 rounded-full bg-governance/10 flex items-center justify-center mb-6">
                <ShieldCheck className="h-8 w-8 text-governance" />
              </div>
              <h2 className="text-xl font-bold text-text mb-2">STATUS: REQUIRED</h2>
              <p className="text-text-secondary text-sm max-w-sm mb-8">
                The scientific foundation has produced a ranking. Selection requires explicit authority confirmation to proceed.
              </p>

              <div className="w-full text-left bg-surface border border-border p-4 rounded-lg mb-6">
                <div className="flex justify-between items-center mb-2 border-b border-border pb-2">
                  <span className="text-xs text-text-muted uppercase">Selection Rule</span>
                  <span className="font-mono text-sm text-text">AUTO_SELECT_TOP_RANK</span>
                </div>
                <div className="flex justify-between items-center mb-2 border-b border-border pb-2">
                  <span className="text-xs text-text-muted uppercase">Authority</span>
                  <span className="font-mono text-sm text-governance">EUREKA_ARCHITECTURAL</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-xs text-text-muted uppercase">Confirmation</span>
                  <span className="font-mono text-sm text-scientific">CONFIRMED</span>
                </div>
              </div>
            </CardContent>
          </div>
          <div className="p-6 border-t border-border">
            <Button className="w-full bg-scientific text-black hover:bg-scientific/90" onClick={() => navigate('/decision/prescription')}>
              Proceed to Prescription
            </Button>
          </div>
        </Card>

        <Card className="bg-surface border-border">
          <CardHeader className="border-b border-border">
            <CardTitle className="text-sm uppercase tracking-widest text-text-muted flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4" />
              Target Alternative
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            <div className="flex justify-between items-start mb-6">
              <div>
                <h3 className="font-mono text-2xl font-bold text-text">ALT-B</h3>
                <p className="text-sm text-text-muted mt-1">Rank 1</p>
              </div>
              <Badge variant="scientific">UTILITY 0.91</Badge>
            </div>
            
            <div className="space-y-4">
              <div className="p-4 bg-surface-elevated rounded border border-border">
                <h4 className="text-sm font-medium text-text mb-2">Risk Constraint</h4>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-text-secondary">Expected Risk</span>
                  <span className="font-mono text-scientific">0.12 (Pass)</span>
                </div>
              </div>
              <div className="p-4 bg-surface-elevated rounded border border-border">
                <h4 className="text-sm font-medium text-text mb-2">Budget Constraint</h4>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-text-secondary">Expected Cost</span>
                  <span className="font-mono text-scientific">$1.2M (Pass)</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}