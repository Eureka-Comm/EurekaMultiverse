import React, { useRef, useEffect, useState } from 'react';
import * as d3 from 'd3';
import type { CanonicalWorkState } from '../../domain/canonicalSchema';

/**
 * ACTION — operational explanation DAG.
 *
 * Upgrades the original D3 force graph of action_plan dependencies into an
 * operational explanation: each action node exposes
 * What→Why→Who→Inputs→Expected Output→Evidence→Dependency→Status from the REAL
 * action_plan.actions[]. Clicking a node shows its full explanation. Only real
 * fields; when the plan is empty the parent renders DATA PENDING.
 */
interface Props {
  state: CanonicalWorkState;
  /** Detailed operational explanation (rendered beside the graph). */
  detailed?: boolean;
}

interface NodeDatum {
  id: string;
  label: string;
  owner: string;
  status: string;
  description: string;
  inputs: string[];
  expectedOutputs: string[];
  deps: string[];
  prerequisites: string[];
  constraints: string[];
  criteria: string[];
  provenance: string[];
}

interface LinkDatum {
  source: string | NodeDatum;
  target: string | NodeDatum;
}

const statusColor = (s: string) =>
  s === 'SUCCEEDED' ? '#059669' : s === 'FAILED' ? '#e11d48' : s === 'FAIL_CLOSED' ? '#e11d48' : '#6366f1';

function ValueList({ label, items }: { label: string; items: string[] }) {
  if (!items?.length) return null;
  return (
    <div className="text-xs">
      <div className="text-[9px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-0.5">{label}</div>
      <ul className="space-y-0.5 pl-2 border-l border-[var(--eureka-spatial-hairline)]">
        {items.map((v, i) => (
          <li key={i} className="text-[10px] text-[var(--eureka-text-section)] break-words">{v}</li>
        ))}
      </ul>
    </div>
  );
}

function ActionDetail({ action, plan, execResult }: { action: NodeDatum | null; plan: any; execResult: any }) {
  if (!action) {
    return (
      <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3 text-[10px] text-[var(--eureka-text-micro)]">
        Click an action node to see its operational explanation (What → Why → Who → Inputs → Expected Output → Evidence → Dependency → Status).
      </div>
    );
  }
  return (
    <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3 space-y-2">
      <div className="flex items-center justify-between">
        <div className="text-[11px] font-mono text-[var(--eureka-text-display)]">{action.id}</div>
        <span className="px-2 py-0.5 rounded text-[9px] font-mono uppercase" style={{ color: statusColor(action.status), border: `1px solid ${statusColor(action.status)}` }}>
          {action.status}
        </span>
      </div>
      <div className="text-xs text-[var(--eureka-text-section)] leading-relaxed">{action.label}</div>

      <div className="text-xs"><span className="text-[9px] uppercase tracking-wider text-[var(--eureka-text-label)]">Why: </span><span className="text-[var(--eureka-text-section)]">{plan?.rationale || 'The prescribed alternative drives this action.'}</span></div>
      <div className="text-xs"><span className="text-[9px] uppercase tracking-wider text-[var(--eureka-text-label)]">Who: </span><span className="text-[var(--eureka-text-section)]">{action.owner || '—'}</span></div>

      <div className="grid grid-cols-2 gap-3">
        <ValueList label="Inputs" items={action.inputs} />
        <ValueList label="Expected outputs" items={action.expectedOutputs} />
        <ValueList label="Prerequisites" items={action.prerequisites} />
        <ValueList label="Dependencies" items={action.deps} />
        <ValueList label="Constraints" items={action.constraints} />
        <ValueList label="Acceptance criteria" items={action.criteria} />
      </div>
      <ValueList label="Evidence / provenance" items={action.provenance} />
      {execResult?.status && (
        <div className="text-xs">
          <span className="text-[9px] uppercase tracking-wider text-[var(--eureka-text-label)]">Execution: </span>
          <span className="text-[var(--eureka-text-section)]">{execResult.status}</span>
        </div>
      )}
    </div>
  );
}

export default function ActionDependencyGraph({ state, detailed = false }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(640);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    const measure = () => {
      if (containerRef.current) setWidth(containerRef.current.clientWidth || 640);
    };
    measure();
    if (typeof ResizeObserver !== 'undefined') {
      const ro = new ResizeObserver(measure);
      if (containerRef.current) ro.observe(containerRef.current);
      return () => ro.disconnect();
    }
    return undefined;
  }, []);

  useEffect(() => {
    const plan = (state as any).action_plan;
    const actions: any[] = plan?.actions || [];
    const executionState = (state as any).execution_state;
    const execResult = executionState?.result;
    const succeeded: string[] = execResult?.successful_actions || [];
    const failed: string[] = execResult?.failed_actions || [];
    const container = containerRef.current;
    if (!actions.length || !container) return () => undefined;

    const height = Math.max(360, actions.length * 62);

    // Build nodes from REAL action fields.
    const nodes: NodeDatum[] = actions.map((a) => ({
      id: a.action_id,
      label: a.description || a.action_id,
      owner: a.owner || '',
      status: failed.includes(a.action_id)
        ? 'FAILED'
        : succeeded.includes(a.action_id)
          ? 'SUCCEEDED'
          : isPlanned(a),
      description: a.description || '',
      inputs: a.inputs || [],
      expectedOutputs: a.expected_outputs || [],
      deps: a.dependencies || [],
      prerequisites: a.prerequisites || [],
      constraints: a.constraints || [],
      criteria: a.acceptance_criteria || [],
      provenance: a.provenance || [],
    }));

    function isPlanned(action: any): string {
      const s = action.status || action.validation_status;
      return s || 'PLANNED';
    }

    const nodeIds = new Set(nodes.map((n) => n.id));

    const links: LinkDatum[] = [];
    actions.forEach((a) => {
      (a.dependencies || []).forEach((dep: string) => {
        if (nodeIds.has(dep) && nodeIds.has(a.action_id)) {
          links.push({ source: dep, target: a.action_id });
        }
      });
    });

    d3.select(container).selectAll('*').remove();

    // Arrow marker for dependency direction
    const defs = d3.select(container).append('svg').attr('width', 0).attr('height', 0).append('defs');
    defs.append('marker').attr('id', 'd3-arrow')
      .attr('viewBox', '0 -5 10 10').attr('refX', 16).attr('refY', 0)
      .attr('markerWidth', 7).attr('markerHeight', 7).attr('orient', 'auto')
      .append('path').attr('d', 'M0,-5L10,0L0,5').attr('fill', '#B3AFA5');

    const svg = d3
      .select(container)
      .append('svg')
      .attr('width', width)
      .attr('height', height)
      .attr('viewBox', `0 0 ${width} ${height}`)
      .style('display', 'block');

    const g = svg.append('g');

    const simulation = d3
      .forceSimulation(nodes as any)
      .force('link', d3.forceLink(links as any).id((d: any) => d.id).distance(96).strength(0.7))
      .force('charge', d3.forceManyBody().strength(-430))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('x', d3.forceX(width / 2).strength(0.06))
      .force('y', d3.forceY(height / 2).strength(0.06))
      .force('collide', d3.forceCollide().radius(26).strength(0.9));

    const color = d3.scaleOrdinal<string>().domain(['SUCCEEDED', 'FAILED', 'PLANNED'])
      .range(['#059669', '#e11d48', '#6366f1']);

    const link = g
      .append('g')
      .selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke', '#B3AFA5')
      .attr('stroke-opacity', 0.7)
      .attr('stroke-width', 1.5)
      .attr('marker-end', 'url(#d3-arrow)');

    const node = g
      .append('g')
      .selectAll('circle')
      .data(nodes)
      .join('circle')
      .attr('r', (d: any) => (d.status === 'SUCCEEDED' ? 11 : 9))
      .attr('fill', (d) => color(d.status))
      .attr('stroke', '#FFFFFF')
      .attr('stroke-width', 2)
      .attr('cursor', 'pointer')
      .on('click', (_ev: any, d: any) => setSelectedId(d.id))
      .call((selection: any) => {
        const drag: any = d3
          .drag()
          .on('start', (event: any, d: any) => {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on('drag', (event: any, d: any) => {
            d.fx = event.x;
            d.fy = event.y;
          })
          .on('end', (event: any, d: any) => {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          });
        selection.call(drag);
      });

    // Label: main id (dark, bold) + owner (faint) below the node.
    const labelMain = g.append('g').selectAll('text').data(nodes).join('text')
      .attr('text-anchor', 'middle')
      .attr('fill', '#14140F')
      .attr('font-size', 10)
      .attr('font-weight', 600)
      .attr('font-family', 'sans-serif')
      .attr('pointer-events', 'none')
      .text((d: any) => d.id);
    const labelOwner = g.append('g').selectAll('text').data(nodes).join('text')
      .attr('text-anchor', 'middle')
      .attr('fill', '#6B6B63')
      .attr('font-size', 8)
      .attr('font-family', 'sans-serif')
      .attr('pointer-events', 'none')
      .text((d: any) => (d.owner || '').replace('EM ', '') || '—');

    simulation.on('tick', () => {
      link
        .attr('x1', (d: any) => d.source.x)
        .attr('y1', (d: any) => d.source.y)
        .attr('x2', (d: any) => d.target.x)
        .attr('y2', (d: any) => d.target.y);
      node.attr('cx', (d: any) => d.x).attr('cy', (d: any) => d.y);
      labelMain.attr('x', (d: any) => d.x).attr('y', (d: any) => d.y + 24);
      labelOwner.attr('x', (d: any) => d.x).attr('y', (d: any) => d.y + 36);
    });

    return () => {
      simulation.stop();
      d3.select(container).selectAll('*').remove();
    };
  }, [state, width]);

  const plan = (state as any).action_plan;
  const actions: any[] = plan?.actions || [];
  if (!actions.length) return null;

  const selectedNode = actions.find((a) => a.action_id === selectedId);
  const selectedDetail: NodeDatum | null = selectedNode
    ? {
        id: selectedNode.action_id,
        label: selectedNode.description || selectedNode.action_id,
        owner: selectedNode.owner || '',
        status: (selectedNode.validation_status || selectedNode.status || 'PLANNED'),
        description: selectedNode.description || '',
        inputs: selectedNode.inputs || [],
        expectedOutputs: selectedNode.expected_outputs || [],
        deps: selectedNode.dependencies || [],
        prerequisites: selectedNode.prerequisites || [],
        constraints: selectedNode.constraints || [],
        criteria: selectedNode.acceptance_criteria || [],
        provenance: selectedNode.provenance || [],
      }
    : null;

  const execResult = (state as any).execution_state?.result;

  return (
    <div className="space-y-3">
      <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)]">
        Operative action plan · {actions.length} action{actions.length === 1 ? '' : 's'} · click a node to explain
      </div>
      <div className="flex items-center gap-3 text-[9px] uppercase tracking-wider text-[var(--eureka-text-label)]">
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#059669]"></span>Completada</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#e11d48]"></span>Fallida</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#6366f1]"></span>Planificada</span>
        <span className="ml-2">→ dependencia</span>
      </div>
      <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-2">
        <div ref={containerRef} className="w-full" style={{ overflow: 'hidden' }} />
      </div>
      {detailed && <ActionDetail action={selectedDetail} plan={plan} execResult={execResult} />}
    </div>
  );
}
