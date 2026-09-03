import { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { useAnalyticalStore } from '../../store/analyticalStore';

export function DecisionField() {
  const containerRef = useRef<HTMLDivElement>(null);
  const { decisionContext, alternatives, evidence, constraints, edges, selectEntity, selectedEntityId } = useAnalyticalStore();

  useEffect(() => {
    if (!containerRef.current) return;
    
    const width = containerRef.current.clientWidth;
    const height = containerRef.current.clientHeight;
    
    // Clear previous
    d3.select(containerRef.current).selectAll('*').remove();
    
    const svg = d3.select(containerRef.current)
      .append('svg')
      .attr('width', width)
      .attr('height', height)
      .attr('viewBox', [0, 0, width, height]);
      
    // Build Graph Data
    const nodes: any[] = [
       { id: decisionContext.id, type: 'OBJECTIVE', title: 'Objective', radius: 30, fx: width/2, fy: height/2 }
    ];
    
    alternatives.forEach(a => nodes.push({ ...a, radius: a.status === 'SELECTED' ? 25 : 15 }));
    evidence.forEach(e => nodes.push({ ...e, radius: 10 }));
    constraints.forEach(c => nodes.push({ ...c, radius: 12 }));
    
    const links = edges.map(e => ({ source: e.source, target: e.target, type: e.type }));
    
    // Simulation
    const simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id((d: any) => d.id).distance(100))
      .force('charge', d3.forceManyBody().strength(-200))
      .force('collide', d3.forceCollide().radius((d: any) => d.radius + 10))
      .force('radial', d3.forceRadial(150, width/2, height/2).strength(0.1));

    // Draw links
    const link = svg.append('g')
      .selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke', 'var(--eureka-spatial-hairline)')
      .attr('stroke-width', 1)
      .attr('stroke-dasharray', d => d.type === 'CONSTRAINS' ? '4,4' : 'none');

    // Draw nodes
    const node = svg.append('g')
      .selectAll('g')
      .data(nodes)
      .join('g')
      .attr('cursor', 'pointer')
      .on('click', (event, d) => {
         selectEntity(d.id, d.type);
         event.stopPropagation();
      });

    // Outer glow for selected
    node.append('circle')
      .attr('r', d => d.radius + 6)
      .attr('fill', 'none')
      .attr('stroke', d => d.id === selectedEntityId ? 'var(--eureka-signal-cognitive)' : 'none')
      .attr('stroke-width', 1)
      .attr('opacity', 0.5);

    // Main circle
    node.append('circle')
      .attr('r', d => d.radius)
      .attr('fill', d => {
        if (d.type === 'OBJECTIVE') return 'var(--eureka-surface-elevated)';
        if (d.type === 'ALTERNATIVE') return d.status === 'SELECTED' ? 'var(--eureka-signal-cognitive)' : 'var(--eureka-surface-elevated)';
        if (d.type === 'CONSTRAINT') return 'var(--eureka-signal-authority)';
        return 'var(--eureka-surface)';
      })
      .attr('stroke', d => {
        if (d.type === 'ALTERNATIVE') return d.status === 'SELECTED' ? 'var(--eureka-signal-cognitive)' : 'var(--eureka-spatial-hairline)';
        return 'var(--eureka-spatial-hairline)';
      })
      .attr('stroke-width', 2);

    // Labels
    node.append('text')
      .text(d => d.type === 'OBJECTIVE' ? 'OBJ' : d.title.substring(0, 10))
      .attr('text-anchor', 'middle')
      .attr('dy', d => d.radius + 12)
      .attr('font-size', '9px')
      .attr('font-family', 'monospace')
      .attr('fill', 'var(--eureka-text-technical)');

    simulation.on('tick', () => {
      link
        .attr('x1', (d: any) => d.source.x)
        .attr('y1', (d: any) => d.source.y)
        .attr('x2', (d: any) => d.target.x)
        .attr('y2', (d: any) => d.target.y);

      node.attr('transform', (d: any) => `translate(${d.x},${d.y})`);
    });

    // Deselect on bg click
    svg.on('click', () => {
      selectEntity(null);
    });

    return () => {
      simulation.stop();
    };
  }, [decisionContext, alternatives, evidence, constraints, edges, selectedEntityId, selectEntity]);

  return (
    <div className="w-full h-full border border-[var(--eureka-spatial-hairline)] bg-surface relative overflow-hidden flex items-center justify-center">
      <div className="absolute inset-0 fabric-grid-bg opacity-40 pointer-events-none" />
      <div ref={containerRef} className="w-full h-full z-10" />
    </div>
  );
}
