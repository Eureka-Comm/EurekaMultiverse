import { useAnalyticalStore } from '../../store/analyticalStore';
import { motion } from 'framer-motion';
import type { EMStage } from '../../domain/mockData';

const STAGES: EMStage[] = [
  'OBJECTIVE', 'SEMANTICS', 'PREDICTION', 'SCIENCE', 'EVALUATION', 
  'RANKING', 'SELECTION', 'PRESCRIPTION', 'FREEZE', 'AUTHORITY', 'ACTION'
];

export function EMFlow() {
  const { decisionContext, timeline, selectEntity, selectedEntityId } = useAnalyticalStore();
  
  const currentStageIndex = STAGES.indexOf(decisionContext.emStage);
  
  return (
    <div className="w-full h-32 border border-[var(--eureka-spatial-hairline)] bg-surface relative flex items-center px-12 overflow-hidden">
      <div className="absolute inset-0 fabric-grid-bg opacity-30" />
      
      {/* Central Pipeline Line */}
      <div className="absolute left-12 right-12 top-1/2 -translate-y-1/2 h-[2px] bg-[var(--eureka-spatial-hairline)]" />
      
      {/* Active Pipeline Glow */}
      <motion.div 
        className="absolute left-12 top-1/2 -translate-y-1/2 h-[2px] bg-signal-cognitive shadow-[0_0_10px_var(--eureka-signal-cognitive)] origin-left"
        initial={{ scaleX: 0 }}
        animate={{ scaleX: (currentStageIndex) / (STAGES.length - 1) }}
        transition={{ duration: 1.5, ease: "easeOut" }}
      />
      
      <div className="relative z-10 flex items-center justify-between w-full h-full">
        {STAGES.map((stage, i) => {
          const isComplete = i < currentStageIndex;
          const isActive = i === currentStageIndex;
          const isPending = i > currentStageIndex;
          
          // Count events in this stage
          const eventsInStage = timeline.filter(t => t.stage === stage);
          const hasEvents = eventsInStage.length > 0;
          
          let colorClass = 'bg-canvas border-[var(--eureka-spatial-hairline)]';
          let textColor = 'text-text-micro';
          let glow = '';
          
          if (isActive) {
            colorClass = 'bg-signal-cognitive border-signal-cognitive';
            textColor = 'text-signal-cognitive font-bold';
            glow = '0 0 20px -5px var(--eureka-signal-cognitive)';
          } else if (isComplete) {
            colorClass = 'bg-[var(--eureka-spatial-hairline)] border-[var(--eureka-spatial-hairline)]';
            textColor = 'text-text-technical';
          }
          
          // Governance coloring for Authority/Action
          if (stage === 'AUTHORITY' && isActive) {
            colorClass = 'bg-signal-authority border-signal-authority';
            textColor = 'text-signal-authority';
            glow = '0 0 20px -5px var(--eureka-signal-authority)';
          }
          
          return (
            <div 
              key={stage} 
              className="flex flex-col items-center justify-center relative cursor-pointer group"
              onClick={() => {
                 if (hasEvents) selectEntity(eventsInStage[0].id, 'TIMELINE');
              }}
            >
              {/* Event indicators (Evidence/Metrics/etc) */}
              <div className="absolute -top-10 flex flex-col items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                {hasEvents && (
                  <div className="text-[9px] font-mono text-text-muted bg-surface-elevated px-2 py-0.5 border border-[var(--eureka-spatial-hairline)] rounded">
                    {eventsInStage.length} EVT
                  </div>
                )}
                {stage === 'SCIENCE' && isComplete && (
                  <div className="text-[9px] font-mono text-signal-scientific">µ: 0.92</div>
                )}
              </div>
            
              {/* Node */}
              <motion.div 
                className={`w-4 h-4 rounded-full border-2 transition-colors relative flex items-center justify-center ${colorClass}`}
                style={{ boxShadow: glow }}
                whileHover={{ scale: 1.2 }}
              >
                 {isActive && (
                    <motion.div 
                      className="absolute inset-0 rounded-full border border-signal-cognitive"
                      animate={{ scale: [1, 1.5, 1], opacity: [1, 0, 1] }}
                      transition={{ duration: 2, repeat: Infinity }}
                    />
                 )}
              </motion.div>
              
              {/* Label */}
              <span className={`absolute -bottom-8 text-[10px] font-mono uppercase tracking-widest whitespace-nowrap ${textColor}`}>
                {stage}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  );
}
