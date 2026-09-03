import { Card, CardHeader, CardTitle } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { Lock, GitCommit, GitBranch } from "lucide-react";
import ReactFlow, { Background, Controls, type Node, type Edge, Position } from "reactflow";
import "reactflow/dist/style.css";

const initialNodes: Node[] = [
  { id: 'obj', position: { x: 300, y: 50 }, data: { label: 'OBJECTIVE PREDICATE' }, style: { background: 'var(--eureka-cognitive)', color: '#000', border: 'none', borderRadius: '4px', padding: '10px', width: 200 }, sourcePosition: Position.Bottom },
  { id: 'and1', position: { x: 300, y: 150 }, data: { label: 'AND' }, style: { background: 'var(--eureka-surface-elevated)', color: 'var(--eureka-text)', border: '1px solid var(--eureka-border)', borderRadius: '50%', width: 50, height: 50, display: 'flex', alignItems: 'center', justifyContent: 'center' }, sourcePosition: Position.Bottom, targetPosition: Position.Top },
  
  { id: 'target', position: { x: 100, y: 250 }, data: { label: 'MAX(Efficiency)' }, style: { background: 'var(--eureka-surface-elevated)', color: 'var(--eureka-text)', border: '1px solid var(--eureka-border)', borderRadius: '4px', padding: '10px' }, sourcePosition: Position.Bottom, targetPosition: Position.Top },
  { id: 'c1', position: { x: 300, y: 250 }, data: { label: 'Risk <= 0.15' }, style: { background: 'var(--eureka-scientific)', color: '#000', border: 'none', borderRadius: '4px', padding: '10px' }, sourcePosition: Position.Bottom, targetPosition: Position.Top },
  
  { id: 'or1', position: { x: 500, y: 250 }, data: { label: 'OR' }, style: { background: 'var(--eureka-surface-elevated)', color: 'var(--eureka-text)', border: '1px solid var(--eureka-border)', borderRadius: '50%', width: 50, height: 50, display: 'flex', alignItems: 'center', justifyContent: 'center' }, sourcePosition: Position.Bottom, targetPosition: Position.Top },
  
  { id: 'optA', position: { x: 420, y: 350 }, data: { label: 'Option A' }, style: { background: 'var(--eureka-surface-elevated)', color: 'var(--eureka-text-muted)', border: '1px dashed var(--eureka-border)', borderRadius: '4px', padding: '10px' }, targetPosition: Position.Top },
  { id: 'optB', position: { x: 580, y: 350 }, data: { label: 'Option B' }, style: { background: 'var(--eureka-surface-elevated)', color: 'var(--eureka-text-muted)', border: '1px dashed var(--eureka-border)', borderRadius: '4px', padding: '10px' }, targetPosition: Position.Top },
];

const initialEdges: Edge[] = [
  { id: 'e1', source: 'obj', target: 'and1', type: 'smoothstep', style: { stroke: 'var(--eureka-text-muted)' } },
  { id: 'e2', source: 'and1', target: 'target', type: 'smoothstep', style: { stroke: 'var(--eureka-text-muted)' } },
  { id: 'e3', source: 'and1', target: 'c1', type: 'smoothstep', style: { stroke: 'var(--eureka-scientific)' } },
  { id: 'e4', source: 'and1', target: 'or1', type: 'smoothstep', style: { stroke: 'var(--eureka-text-muted)' } },
  { id: 'e5', source: 'or1', target: 'optA', type: 'smoothstep', style: { stroke: 'var(--eureka-text-muted)', strokeDasharray: '5,5' } },
  { id: 'e6', source: 'or1', target: 'optB', type: 'smoothstep', style: { stroke: 'var(--eureka-text-muted)', strokeDasharray: '5,5' } },
];

export default function Predicate() {
  return (
    <div className="flex flex-col h-full p-8 bg-canvas">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-text">Predicate Graph</h1>
          <p className="text-text-muted mt-1 text-sm">Visual representation of the ACFL logical structure.</p>
        </div>
        <Badge variant="neutral" className="bg-surface border-border">DEMO DATA</Badge>
      </div>

      <Card className="bg-surface border-border flex-1 flex flex-col overflow-hidden">
        <CardHeader className="border-b border-border bg-surface-elevated">
          <CardTitle className="text-sm uppercase tracking-widest text-text-muted flex items-center gap-2">
            <GitBranch className="h-4 w-4" />
            Logical Dependency Tree
          </CardTitle>
        </CardHeader>
        <div className="flex-1 relative bg-canvas/50">
          <ReactFlow 
            nodes={initialNodes} 
            edges={initialEdges} 
            fitView 
            attributionPosition="bottom-right"
            className="dark"
          >
            <Background color="var(--eureka-border)" gap={20} size={1} />
            <Controls showInteractive={false} className="bg-surface-elevated border-border fill-text" />
          </ReactFlow>
        </div>
      </Card>
    </div>
  );
}