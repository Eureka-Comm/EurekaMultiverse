import { EMFlow } from "../components/intelligence/EMFlow";
import { DecisionField } from "../components/visualizations/DecisionField";
import { DecisionPhaseSpace } from "../components/visualizations/DecisionPhaseSpace";
import IntelligenceNetwork from "../components/visualizations/IntelligenceNetwork";
import { ScientificSurface } from "../components/visualizations/ScientificSurface";
import { useAnalyticalStore } from "../store/analyticalStore";

export default function Overview() {
  const { decisionContext } = useAnalyticalStore();

  return (
    <div className="w-full h-full flex flex-col p-6 gap-6 overflow-y-auto overflow-x-hidden relative">
      
      {/* CASE / DECISION CONTEXT */}
      <section className="shrink-0 flex flex-col gap-2 relative z-10">
        <h1 className="text-3xl font-light text-text-display tracking-wide">{decisionContext.title}</h1>
        <p className="text-sm font-mono text-text-technical uppercase tracking-widest">
          {decisionContext.workspace} &bull; {decisionContext.caseId} &bull; Agent: {decisionContext.agent}
        </p>
      </section>

      {/* LIVE INTELLIGENCE FLOW */}
      <section className="shrink-0 relative z-10">
        <EMFlow />
      </section>

      {/* MAIN SPATIAL GRID */}
      <section className="grid grid-cols-12 gap-6 flex-1 min-h-[800px] relative z-10">
        
        {/* LEFT COLUMN: DECISION FIELD & NETWORK (7 cols) */}
        <div className="col-span-7 flex flex-col gap-6">
          <div className="flex-1 flex flex-col gap-2 relative group min-h-[400px]">
            <div className="text-[10px] font-mono text-text-technical uppercase tracking-widest bg-canvas px-2 inline-block">Decision Field (Topology)</div>
            <DecisionField />
          </div>
          
          <div className="h-64 flex flex-col gap-2 relative group">
             <div className="text-[10px] font-mono text-text-technical uppercase tracking-widest bg-canvas px-2 inline-block">Intelligence Network</div>
             <IntelligenceNetwork />
          </div>
        </div>

        {/* RIGHT COLUMN: PHASE SPACE & SCIENTIFIC (5 cols) */}
        <div className="col-span-5 flex flex-col gap-6">
          
          <div className="flex-1 flex flex-col gap-2 min-h-[350px]">
            <div className="text-[10px] font-mono text-text-technical uppercase tracking-widest bg-canvas px-2 inline-block">Decision Phase Space</div>
            <DecisionPhaseSpace />
          </div>

          <div className="h-64 flex flex-col gap-2">
            <div className="text-[10px] font-mono text-text-technical uppercase tracking-widest bg-canvas px-2 inline-block">Scientific Evaluation</div>
            <ScientificSurface />
          </div>
          
        </div>
      </section>

    </div>
  );
}