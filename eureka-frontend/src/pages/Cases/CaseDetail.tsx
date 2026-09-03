import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { DemoDecisionRepository } from "../../infrastructure/adapters/DemoDecisionRepository";
import { type DecisionViewModel } from "../../domain/models";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { ArrowLeft, GitMerge, FileText, Database, Shield } from "lucide-react";

const repo = new DemoDecisionRepository();

export default function CaseDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [decision, setDecision] = useState<DecisionViewModel | null>(null);

  useEffect(() => {
    if (id) {
      repo.getDecision(id).then(setDecision);
    }
  }, [id]);

  if (!decision) return <div className="p-8 text-text-muted">Loading Case Details...</div>;

  return (
    <div className="flex flex-col h-full p-8 bg-canvas">
      <div className="mb-8">
        <Button variant="ghost" className="mb-4 text-text-muted hover:text-text -ml-4" onClick={() => navigate('/cases')}>
          <ArrowLeft className="mr-2 h-4 w-4" /> Back to Cases
        </Button>
        <div className="flex items-center gap-4 mb-2">
          <h1 className="text-3xl font-bold tracking-tight text-text">{decision.title || `Case ${decision.id}`}</h1>
          <Badge variant="neutral">DEMO DATA</Badge>
          <Badge variant="scientific">{decision.status}</Badge>
        </div>
        <p className="text-text-muted">Detailed view of the decision context and current state.</p>
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2 space-y-6">
          <Card className="bg-surface-elevated border-border">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <FileText className="h-5 w-5 text-cognitive" />
                Problem Statement
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-text-secondary whitespace-pre-wrap">{decision.objective ? decision.objective.expression : "Objective formulation pending."}</p>
            </CardContent>
          </Card>

          <Card className="bg-surface-elevated border-border">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <GitMerge className="h-5 w-5 text-scientific" />
                Pipeline Execution
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {decision.timeline.map((event) => (
                  <div key={event.id} className="flex gap-4">
                    <div className="flex flex-col items-center">
                      <div className="h-2 w-2 rounded-full bg-scientific mt-2"></div>
                      <div className="w-px h-full bg-border mt-2"></div>
                    </div>
                    <div className="pb-4">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-medium text-text">{event.stage}</span>
                        <span className="text-xs text-text-muted font-mono">{new Date(event.timestamp).toLocaleTimeString()}</span>
                      </div>
                      <p className="text-sm text-text-secondary">{event.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card className="bg-surface border-border">
            <CardHeader>
              <CardTitle className="text-sm uppercase tracking-wider text-text-muted flex items-center gap-2">
                <Database className="h-4 w-4" />
                Context Assets
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm">
                <li className="flex items-center justify-between p-2 rounded bg-surface-elevated border border-border">
                  <span className="text-text-secondary">Historical_Data.csv</span>
                  <Badge variant="neutral">Dataset</Badge>
                </li>
                <li className="flex items-center justify-between p-2 rounded bg-surface-elevated border border-border">
                  <span className="text-text-secondary">Compliance_Rules_2026.pdf</span>
                  <Badge variant="neutral">Document</Badge>
                </li>
              </ul>
            </CardContent>
          </Card>

          <Card className="bg-surface border-border">
            <CardHeader>
              <CardTitle className="text-sm uppercase tracking-wider text-text-muted flex items-center gap-2">
                <Shield className="h-4 w-4" />
                Authority Chain
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-sm space-y-3">
                <div>
                  <span className="block text-xs text-text-muted mb-1">Cognitive Provider</span>
                  <span className="font-mono text-cognitive">Local Mock (Zero-Cost)</span>
                </div>
                <div>
                  <span className="block text-xs text-text-muted mb-1">Governance Rule</span>
                  <span className="font-mono text-governance">STRICT_SEMANTIC_GATES</span>
                </div>
                <div>
                  <span className="block text-xs text-text-muted mb-1">Execution Authority</span>
                  <span className="font-mono text-frozen">HUMAN_EXTERNAL Required</span>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Button className="w-full bg-scientific text-black hover:bg-scientific/90" onClick={() => navigate('/chat')}>
            Open in Sandbox
          </Button>
        </div>
      </div>
    </div>
  );
}