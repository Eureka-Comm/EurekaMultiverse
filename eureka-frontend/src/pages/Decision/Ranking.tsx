import { useEffect, useState } from "react";
import { DemoDecisionRepository } from "../../infrastructure/adapters/DemoDecisionRepository";
import { type DecisionViewModel, type EvaluationViewModel } from "../../domain/models";
import { Card, CardHeader, CardTitle, CardContent } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { Scale, Check, X, ArrowRight, ShieldCheck } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";

const repo = new DemoDecisionRepository();

export default function Ranking() {
  const [decision, setDecision] = useState<DecisionViewModel | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    repo.getDecision("case-001").then(setDecision);
  }, []);

  if (!decision || !decision.ranking) return <div className="p-6 text-text-muted">Loading Ranking...</div>;

  return (
    <div className="flex h-full flex-col gap-6 p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Scientific Ranking</h1>
          <p className="text-sm text-text-muted mt-1">Mathematical evaluation of alternatives against the Objective Predicate.</p>
        </div>
        <Badge variant="scientific">SCIENTIFIC FOUNDATION</Badge>
      </div>

      <div className="flex gap-4 p-4 rounded-lg bg-surface-elevated/50 border border-white/5 items-center">
        <Scale className="h-5 w-5 text-scientific" />
        <div className="flex-1">
          <p className="text-xs text-text-muted">Evaluated Predicate</p>
          <p className="font-mono text-sm text-text-primary">{decision.objective?.expression}</p>
        </div>
      </div>

      <div className="flex-1">
        <div className="space-y-4">
          <AnimatePresence>
            {decision.ranking.sortedEvaluations.map((evalData: EvaluationViewModel, index: number) => {
              const alt = decision.alternatives.find(a => a.id === evalData.alternativeId);
              if (!alt) return null;
              
              const isViolator = evalData.truthValue === 0;

              return (
                <motion.div 
                  key={alt.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                >
                  <Card className={`relative overflow-hidden transition-all ${isViolator ? 'opacity-60 border-blocked/20' : index === 0 ? 'border-scientific shadow-lg shadow-scientific/10 bg-scientific/5' : 'border-white/5'}`}>
                    <div className="flex items-stretch h-full">
                      {/* Rank Indicator */}
                      <div className={`w-16 flex flex-col items-center justify-center border-r border-white/5 ${isViolator ? 'bg-blocked/5 text-blocked' : index === 0 ? 'bg-scientific/10 text-scientific' : 'bg-surface-elevated/30 text-text-muted'}`}>
                        <span className="text-sm font-bold">#{index + 1}</span>
                      </div>
                      
                      {/* Content */}
                      <div className="flex-1 p-5">
                        <div className="flex justify-between items-start mb-2">
                          <h3 className="text-lg font-medium text-text-primary">{alt.name}</h3>
                          <Badge variant={isViolator ? 'blocked' : 'scientific'}>
                            {isViolator ? 'VIOLATES PREDICATE' : `UTILITY: ${evalData.utility.toFixed(2)}`}
                          </Badge>
                        </div>
                        <p className="text-sm text-text-muted mb-4">{alt.description}</p>
                        
                        <div className="space-y-1">
                          {evalData.evidence.map((ev, i) => (
                            <div key={i} className="flex items-center gap-2 text-xs">
                              {isViolator && i === 0 ? <X className="h-3 w-3 text-blocked" /> : <Check className="h-3 w-3 text-scientific" />}
                              <span className={isViolator && i === 0 ? 'text-blocked' : 'text-text-secondary'}>{ev}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                      
                      {/* Actions */}
                      {!isViolator && (
                        <div className="w-48 flex items-center justify-center border-l border-white/5 p-4">
                          <Button 
                            variant={index === 0 ? 'primary' : 'outline'} 
                            className="w-full"
                            onClick={() => navigate("/decision/selection")}
                          >
                            Select <ArrowRight className="ml-2 h-4 w-4" />
                          </Button>
                        </div>
                      )}
                    </div>
                  </Card>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </div>
      </div>
      
      <div className="mt-4 flex justify-end">
        <Button variant="ghost" className="text-text-muted" onClick={() => navigate("/decision/selection")}>
          Proceed to Governance Selection <ShieldCheck className="ml-2 h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}