import { Card, CardHeader, CardTitle, CardContent } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { CheckCircle2, Lock, Sparkles, BrainCircuit, Workflow, FileTerminal } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { useNavigate } from "react-router-dom";

export default function Sandbox() {
  const navigate = useNavigate();

  return (
    <div className="flex h-full flex-col gap-6 p-2 max-w-6xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Agent Sandbox</h1>
          <p className="text-sm text-text-muted mt-1">Isolating cognitive outputs from decision authority.</p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" onClick={() => navigate("/decision/ranking")}>
            View Ranking
          </Button>
        </div>
      </div>

      <Card className="bg-surface-elevated/30 border-white/5">
        <CardContent className="p-5 flex gap-4 items-start">
          <div className="mt-1 text-text-muted"><FileTerminal className="h-5 w-5" /></div>
          <div>
            <p className="text-xs font-medium text-text-muted uppercase tracking-wider mb-2">User Input</p>
            <p className="text-text-primary text-lg font-light leading-relaxed">
              "Tengo que elegir entre tres alternativas para el lanzamiento en Q4, priorizando ROI con riesgo menor a 0.5."
            </p>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-2 gap-6 flex-1 min-h-[500px]">
        {/* Untrusted Cognitive Area */}
        <Card className="flex flex-col border-cognitive/20 bg-surface shadow-2xl shadow-cognitive/5 relative overflow-hidden">
          <div className="absolute top-0 w-full h-1 bg-gradient-to-r from-cognitive/0 via-cognitive to-cognitive/0 opacity-20"></div>
          <CardHeader className="border-b border-white/5 pb-4 bg-cognitive/5">
            <div className="flex items-center justify-between">
              <CardTitle className="text-cognitive flex items-center gap-2 text-lg">
                <BrainCircuit className="h-5 w-5" />
                DeepSeek Output
              </CardTitle>
              <Badge variant="outline" className="border-cognitive/30 text-cognitive font-bold">UNTRUSTED</Badge>
            </div>
            <div className="flex gap-4 mt-3 text-xs text-text-muted">
              <span className="flex items-center gap-1.5"><div className="w-1.5 h-1.5 rounded-full bg-cognitive"></div> Provider: DeepSeek</span>
              <span className="flex items-center gap-1.5"><div className="w-1.5 h-1.5 rounded-full bg-cognitive"></div> Runtime: LOCAL</span>
              <span className="flex items-center gap-1.5"><div className="w-1.5 h-1.5 rounded-full bg-blocked"></div> Authority: NONE</span>
            </div>
          </CardHeader>
          <CardContent className="flex-1 overflow-y-auto pt-6 text-sm">
            <div className="space-y-6">
              <div>
                <h4 className="font-semibold text-cognitive mb-2 flex items-center gap-2">
                  <Sparkles className="h-4 w-4" /> Proposed Formalization
                </h4>
                <div className="bg-canvas border border-white/5 p-4 rounded-md font-mono text-sm text-text-primary shadow-inner">
                  Maximize(ROI) AND Risk &lt; 0.5
                </div>
              </div>
              
              <div>
                <h4 className="font-semibold text-cognitive mb-2">Alternatives Discovered</h4>
                <div className="space-y-2">
                  {['Aggressive Launch', 'Phased Entry', 'Partnership Model'].map((alt) => (
                    <div key={alt} className="bg-surface-elevated/50 p-3 rounded border border-white/5 flex items-center gap-3">
                      <div className="w-2 h-2 rounded-full bg-cognitive/50"></div>
                      <span className="text-text-primary">{alt}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Governed Verification Area */}
        <Card className="flex flex-col border-scientific/20 bg-surface shadow-2xl shadow-scientific/5 relative overflow-hidden">
          <div className="absolute top-0 w-full h-1 bg-gradient-to-r from-scientific/0 via-scientific to-scientific/0 opacity-20"></div>
          <CardHeader className="border-b border-white/5 pb-4 bg-scientific/5">
            <div className="flex items-center justify-between">
              <CardTitle className="text-text-primary flex items-center gap-2 text-lg">
                <Workflow className="h-5 w-5 text-scientific" />
                EUREKA Validation
              </CardTitle>
            </div>
          </CardHeader>
          <CardContent className="flex-1 pt-6 relative">
            <div className="absolute left-7 top-10 bottom-10 w-px bg-white/5"></div>
            
            <div className="space-y-8 relative z-10">
              <div className="flex items-start gap-4">
                <div className="mt-1 rounded-full bg-canvas border border-scientific/30 p-1.5 text-scientific shadow-lg shadow-scientific/20">
                  <CheckCircle2 className="h-4 w-4" />
                </div>
                <div className="flex-1">
                  <div className="flex justify-between items-start mb-1">
                    <h4 className="font-medium text-text-primary">Semantic Authority</h4>
                    <Badge variant="scientific">VALIDATED</Badge>
                  </div>
                  <p className="text-sm text-text-muted">Predicate structure parsed and mapped to core AST.</p>
                  <div className="mt-3 p-3 bg-canvas border border-white/5 rounded font-mono text-xs text-text-secondary">
                    PredicateBuilder.parse(Objective) -&gt; VALID
                  </div>
                </div>
              </div>

              <div className="flex items-start gap-4">
                <div className="mt-1 rounded-full bg-canvas border border-scientific/30 p-1.5 text-scientific shadow-lg shadow-scientific/20">
                  <CheckCircle2 className="h-4 w-4" />
                </div>
                <div className="flex-1">
                  <div className="flex justify-between items-start mb-1">
                    <h4 className="font-medium text-text-primary">Scientific Foundation</h4>
                    <Badge variant="scientific">EVALUATED</Badge>
                  </div>
                  <p className="text-sm text-text-muted">Variables [ROI, Risk] resolved. Mathematical evaluation complete.</p>
                </div>
              </div>

              <div className="flex items-start gap-4">
                <div className="mt-1 rounded-full bg-canvas border border-governance/30 p-1.5 text-governance shadow-lg shadow-governance/20">
                  <Lock className="h-4 w-4" />
                </div>
                <div className="flex-1">
                  <div className="flex justify-between items-start mb-1">
                    <h4 className="font-medium text-text-primary">Governance Authority</h4>
                    <Badge variant="governance">SELECTION REQUIRED</Badge>
                  </div>
                  <p className="text-sm text-text-muted">Mathematical ranking produced. LLM cannot authorize execution.</p>
                  <div className="mt-4">
                    <Button variant="outline" size="sm" className="w-full border-governance/30 text-governance hover:bg-governance/10 hover:text-governance" onClick={() => navigate("/decision/selection")}>
                      Transfer to Selection Authority
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}