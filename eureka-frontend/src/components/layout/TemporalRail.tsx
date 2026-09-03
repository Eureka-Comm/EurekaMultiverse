import { useAnalyticalStore } from "../../store/analyticalStore";
import { motion } from "framer-motion";

export function TemporalRail() {
  const { timeline, decisionContext, selectEntity, selectedEntityId } = useAnalyticalStore();

  return (
    <div className="h-16 w-full bg-surface border-t border-[var(--eureka-spatial-hairline)] flex flex-col px-4 font-mono text-[10px] text-text-technical overflow-hidden relative">
      <div className="absolute inset-0 fabric-grid-bg opacity-30" />
      
      <div className="flex-1 flex items-center relative z-10 w-full">
        {/* Connection line */}
        <div className="absolute left-0 right-0 h-[1px] bg-[var(--eureka-spatial-hairline)] top-1/2 -translate-y-1/2" />
        
        {/* Events */}
        <div className="flex items-center justify-between w-full relative px-8">
          {timeline.map((event, i) => {
            const isSelected = selectedEntityId === event.id;
            
            return (
              <div 
                key={event.id}
                className="relative flex flex-col items-center group cursor-pointer"
                onClick={() => selectEntity(event.id, 'TIMELINE')}
              >
                <div className={`w-2.5 h-2.5 rounded-full z-10 transition-colors border ${
                   isSelected ? 'bg-signal-cognitive border-signal-cognitive shadow-[0_0_10px_var(--eureka-signal-cognitive)]' :
                   'bg-surface-elevated border-[var(--eureka-spatial-hairline)] group-hover:border-text-technical'
                }`} />
                
                <div className="absolute top-4 flex flex-col items-center opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
                  <span className="text-[9px] text-text-label">{event.title}</span>
                  <span className="text-[8px] text-text-muted">{new Date(event.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                </div>
                
                {isSelected && (
                  <motion.div 
                    className="absolute -top-6 flex flex-col items-center whitespace-nowrap"
                    initial={{ y: 5, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                  >
                    <span className="text-[10px] text-signal-cognitive font-bold uppercase">{event.title}</span>
                    <div className="w-[1px] h-4 bg-signal-cognitive mt-1" />
                  </motion.div>
                )}
              </div>
            )
          })}
        </div>
      </div>
      
      <div className="shrink-0 h-4 flex justify-between items-center z-10 text-[8px] uppercase text-text-muted px-2">
        <span>T: {new Date(decisionContext.createdAt).toLocaleDateString()}</span>
        <span className="text-signal-semantic">EUREKA-CORE TIMELINE</span>
        <span>T: {new Date(decisionContext.updatedAt).toLocaleDateString()}</span>
      </div>
    </div>
  );
}
