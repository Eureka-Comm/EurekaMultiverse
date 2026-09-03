import { useState } from "react";
import { Card, CardContent } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { ChevronRight, ChevronLeft, Target, GitMerge, FileText, CheckCircle2, FileSignature, Zap, Activity } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

const storySteps = [
  { id: "problem", title: "The Problem", icon: Target, content: "The organization needs to deploy a new infrastructure strategy without exceeding a 15% risk profile and $1.5M budget.", color: "text-text-muted" },
  { id: "cognition", title: "Cognitive Analysis", icon: Activity, content: "Agent identified 4 valid strategies from historical data and unstructured context.", color: "text-cognitive" },
  { id: "formalization", title: "Formalization", icon: GitMerge, content: "ACFL constraints built: MAX(Efficiency) AND (Risk <= 0.15) AND (Budget <= 1.5M).", color: "text-scientific" },
  { id: "ranking", title: "Ranking", icon: GitMerge, content: "Strategy ALT-B ranked highest with a 0.91 Utility score.", color: "text-scientific" },
  { id: "prescription", title: "Prescription", icon: FileText, content: "Formal payload generated to execute ALT-B in production.", color: "text-text" },
  { id: "freeze", title: "System Frozen", icon: CheckCircle2, content: "Execution blocked. Waiting for HUMAN_EXTERNAL authority.", color: "text-frozen" },
  { id: "auth", title: "Authorized", icon: FileSignature, content: "CISO confirmed execution. Cryptographic signature attached.", color: "text-governance" },
  { id: "action", title: "Action", icon: Zap, content: "Payload dispatched to infrastructure orchestrator.", color: "text-authorized" },
];

export default function Executive() {
  const [currentStep, setCurrentStep] = useState(0);

  const handleNext = () => {
    if (currentStep < storySteps.length - 1) setCurrentStep(c => c + 1);
  };
  
  const handlePrev = () => {
    if (currentStep > 0) setCurrentStep(c => c - 1);
  };

  const step = storySteps[currentStep];
  const Icon = step.icon;

  return (
    <div className="flex flex-col h-full p-8 bg-canvas">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-text">Executive Story</h1>
          <p className="text-text-muted mt-1 text-sm">High-level narrative of the decision lifecycle.</p>
        </div>
        <Badge variant="neutral" className="bg-surface border-border">DEMO DATA</Badge>
      </div>

      <div className="flex-1 flex flex-col items-center justify-center max-w-4xl mx-auto w-full">
        
        {/* Progress Bar */}
        <div className="w-full flex gap-2 mb-12">
          {storySteps.map((s, i) => (
            <div 
              key={s.id} 
              className={`h-1 flex-1 rounded transition-colors ${i <= currentStep ? 'bg-text' : 'bg-surface-elevated'}`}
            />
          ))}
        </div>

        {/* Narrative Card */}
        <AnimatePresence mode="wait">
          <motion.div
            key={currentStep}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
            className="w-full"
          >
            <Card className="bg-surface-elevated border-border overflow-hidden shadow-2xl">
              <CardContent className="p-12 flex flex-col items-center text-center">
                <div className={`p-4 rounded-full bg-surface mb-8 border border-border shadow-inner`}>
                  <Icon className={`h-12 w-12 ${step.color}`} />
                </div>
                <h2 className="text-sm tracking-widest uppercase font-bold text-text-muted mb-4">
                  Step 0{currentStep + 1} // {step.title}
                </h2>
                <p className="text-3xl font-light text-text leading-tight max-w-2xl">
                  {step.content}
                </p>
              </CardContent>
            </Card>
          </motion.div>
        </AnimatePresence>

        {/* Navigation */}
        <div className="flex items-center gap-4 mt-12">
          <button 
            onClick={handlePrev} 
            disabled={currentStep === 0}
            className="p-4 rounded-full bg-surface-elevated border border-border text-text hover:bg-surface disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft className="h-6 w-6" />
          </button>
          
          <span className="font-mono text-sm text-text-muted">
            {currentStep + 1} / {storySteps.length}
          </span>
          
          <button 
            onClick={handleNext} 
            disabled={currentStep === storySteps.length - 1}
            className="p-4 rounded-full bg-surface-elevated border border-border text-text hover:bg-surface disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronRight className="h-6 w-6" />
          </button>
        </div>

      </div>
    </div>
  );
}