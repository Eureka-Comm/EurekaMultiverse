import { useEffect, useState } from "react";
import ReactFlow, { Background, Controls, type Node, type Edge, Position } from "reactflow";
import "reactflow/dist/style.css";
import { DemoDecisionRepository } from "../../infrastructure/adapters/DemoDecisionRepository";
import { type DecisionViewModel } from "../../domain/models";
import { Badge } from "../../components/ui/Badge";

const repo = new DemoDecisionRepository();

const nodeTypes = {}; // We can add custom node types here

export default function Technical() {
  const [decision, setDecision] = useState<DecisionViewModel | null>(null);
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);

  useEffect(() => {
    repo.getDecision("case-001").then(dec => {
      if (dec) {
        setDecision(dec);
        
        // Generate pipeline nodes from timeline
        const newNodes: Node[] = dec.timeline.map((event, index) => {
          let bgColor = 'var(--eureka-surface-elevated)';
          let borderColor = 'rgba(255,255,255,0.1)';
          
          if (event.state === 'SUCCESS') { borderColor = 'var(--eureka-scientific)'; bgColor = 'rgba(139,92,246,0.1)'; }
          if (event.state === 'WARNING') { borderColor = 'var(--eureka-frozen)'; bgColor = 'rgba(249,115,22,0.1)'; }
          if (event.stage === 'COGNITION') { borderColor = 'var(--eureka-cognitive)'; bgColor = 'rgba(6,182,212,0.1)'; }

          return {
            id: event.id,
            position: { x: 250, y: index * 120 + 50 },
            data: { 
              label: (
                <div className="p-2 w-48 text-left">
                  <div className="text-[10px] font-bold text-text-muted mb-1">{event.stage}</div>
                  <div className="text-xs text-text-primary whitespace-normal">{event.description}</div>
                  <div className="text-[9px] text-text-muted mt-2 mt-auto font-mono">{event.actor}</div>
                </div>
              ) 
            },
            sourcePosition: Position.Bottom,
            targetPosition: Position.Top,
            style: {
              background: bgColor,
              border: `1px solid ${borderColor}`,
              borderRadius: '8px',
              color: 'var(--eureka-text-primary)'
            }
          };
        });

        const newEdges: Edge[] = dec.timeline.slice(0, -1).map((event, index) => ({
          id: `e-${event.id}-${dec.timeline[index + 1].id}`,
          source: event.id,
          target: dec.timeline[index + 1].id,
          animated: true,
          style: { stroke: 'var(--eureka-text-muted)' }
        }));

        setNodes(newNodes);
        setEdges(newEdges);
      }
    });
  }, []);

  if (!decision) return <div className="p-6 text-text-muted">Loading Decision Pipeline...</div>;

  return (
    <div className="flex h-full flex-col">
      <div className="p-6 border-b border-white/5">
        <h1 className="text-2xl font-semibold tracking-tight">Technical Pipeline View</h1>
        <p className="text-sm text-text-muted mt-1">Full state machine execution path visualization.</p>
      </div>
      <div className="flex-1 bg-surface relative">
        <ReactFlow 
          nodes={nodes} 
          edges={edges} 
          nodeTypes={nodeTypes}
          fitView
          className="dark"
        >
          <Background color="var(--eureka-text-muted)" gap={16} size={1} />
          <Controls className="bg-surface-elevated border-white/10" showInteractive={false} />
        </ReactFlow>
      </div>
    </div>
  );
}