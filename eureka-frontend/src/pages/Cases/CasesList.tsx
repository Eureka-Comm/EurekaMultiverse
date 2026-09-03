import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { DemoDecisionRepository } from "../../infrastructure/adapters/DemoDecisionRepository";
import { type DecisionViewModel } from "../../domain/models";
import { Activity, Plus, Search } from "lucide-react";

const repo = new DemoDecisionRepository();

export default function CasesList() {
  const [cases, setCases] = useState<DecisionViewModel[]>([]);
  const navigate = useNavigate();

  useEffect(() => {
    // In a real implementation, the repo would list multiple cases. 
    // Here we wrap the single mock case in an array.
    repo.getDecision("case-001").then((dec) => {
      if (dec) setCases([dec]);
    });
  }, []);

  const getStatusVariant = (state: string) => {
    switch(state) {
      case 'DRAFT': return 'neutral';
      case 'COGNITION': return 'cognitive';
      case 'EVALUATED': return 'scientific';
      case 'RANKED': return 'scientific';
      case 'FROZEN': return 'frozen';
      case 'AUTHORIZED': return 'authorized';
      default: return 'neutral';
    }
  };

  return (
    <div className="flex flex-col h-full p-8 bg-canvas">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-text">Active Cases</h1>
          <p className="text-text-muted mt-1 text-sm">Manage and monitor Decision Intelligence pipelines.</p>
        </div>
        <Button className="bg-cognitive text-black hover:bg-cognitive/90" onClick={() => navigate('/cases/new')}>
          <Plus className="mr-2 h-4 w-4" /> New Case
        </Button>
      </div>

      <div className="flex items-center gap-4 mb-6">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted" />
          <input 
            type="text" 
            placeholder="Search by ID, title, or objective..." 
            className="w-full bg-surface border border-border rounded-md py-2 pl-10 pr-4 text-sm text-text focus:outline-none focus:border-cognitive transition-colors"
          />
        </div>
      </div>

      <div className="grid gap-4">
        {cases.map((c) => (
          <Card 
            key={c.id} 
            className="bg-surface-elevated border-border hover:border-text-muted transition-colors cursor-pointer"
            onClick={() => navigate(`/cases/${c.id}`)}
          >
            <CardContent className="p-6 flex items-center justify-between">
              <div className="flex items-center gap-6">
                <div className="h-12 w-12 rounded-full bg-surface flex items-center justify-center border border-border">
                  <Activity className="h-5 w-5 text-text-muted" />
                </div>
                <div>
                  <div className="flex items-center gap-3 mb-1">
                    <span className="font-mono text-xs text-text-muted">{c.id}</span>
                    <Badge variant={getStatusVariant(c.status)}>{c.status}</Badge>
                    <Badge variant="neutral" className="bg-surface border-border">DEMO DATA</Badge>
                  </div>
                  <h3 className="text-lg font-medium text-text">{c.title || "Untitled Decision Case"}</h3>
                </div>
              </div>

              <div className="flex items-center gap-12 text-sm">
                <div>
                  <p className="text-text-muted text-xs mb-1 uppercase tracking-wider">Provider</p>
                  <p className="text-text font-medium">Local Mock</p>
                </div>
                <div>
                  <p className="text-text-muted text-xs mb-1 uppercase tracking-wider">Last Event</p>
                  <p className="text-text font-medium">{c.timeline[c.timeline.length - 1]?.description || 'N/A'}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
        {cases.length === 0 && (
          <div className="text-center py-12 border border-dashed border-border rounded-lg text-text-muted">
            No active cases found.
          </div>
        )}
      </div>
    </div>
  );
}