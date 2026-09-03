import React, { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Activity, Zap, ShieldAlert, Network as NetworkIcon } from 'lucide-react';
import { useUIStore } from '../../store/uiStore';

// Generate mock massive dataset for a 2030-vibe intelligence network
const generateNetworkData = () => {
  const nodes = [];
  const edges = [];
  const categories = [
    { name: 'Cognitive Node' },
    { name: 'Scientific Data' },
    { name: 'Governance Rule' },
    { name: 'Human Interface' },
  ];

  // 150 nodes
  for (let i = 0; i < 150; i++) {
    const categoryIdx = Math.floor(Math.random() * 4);
    nodes.push({
      id: i.toString(),
      name: `Node-${i.toString().padStart(3, '0')}`,
      symbolSize: Math.random() * 20 + 5,
      x: null,
      y: null,
      value: Math.random() * 100,
      category: categoryIdx,
      label: {
        show: i % 10 === 0,
      }
    });
  }

  // 250 edges
  for (let i = 0; i < 250; i++) {
    edges.push({
      source: Math.floor(Math.random() * 150).toString(),
      target: Math.floor(Math.random() * 150).toString(),
      lineStyle: {
        width: Math.random() * 2 + 0.5,
        opacity: Math.random() * 0.5 + 0.1
      }
    });
  }

  return { nodes, edges, categories };
};

export function Network() {
  const { nodes, edges, categories } = useMemo(() => generateNetworkData(), []);

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      formatter: '{b}'
    },
    color: [
      'var(--eureka-cognitive)', 
      'var(--eureka-scientific)', 
      'var(--eureka-governance)', 
      'var(--eureka-human)'
    ],
    series: [
      {
        type: 'graph',
        layout: 'force',
        nodes: nodes,
        links: edges,
        categories: categories,
        roam: true,
        label: {
          position: 'right',
          formatter: '{b}',
          color: 'var(--eureka-text-secondary)',
          fontSize: 10,
          fontFamily: 'monospace'
        },
        force: {
          repulsion: 150,
          edgeLength: [50, 150]
        },
        itemStyle: {
          borderColor: 'var(--eureka-canvas)',
          borderWidth: 1,
          shadowBlur: 10,
          shadowColor: 'rgba(255, 255, 255, 0.2)'
        },
        lineStyle: {
          color: 'source',
          curveness: 0.3
        },
        emphasis: {
          focus: 'adjacency',
          lineStyle: {
            width: 5
          }
        }
      }
    ]
  };

  return (
    <div className="flex flex-col h-full w-full p-6 gap-6 overflow-hidden">
      <div className="flex items-center justify-between shrink-0">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2 text-text-muted">
            <NetworkIcon className="w-4 h-4" />
            <span className="text-xs uppercase tracking-widest font-mono">Analytics / Topology</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-text-primary">Intelligence Network</h1>
        </div>
        
        <div className="flex gap-4">
          <Badge variant="outline" className="border-cognitive/30 text-cognitive">
            <Zap className="w-3 h-3 mr-1" /> 150 Active Nodes
          </Badge>
          <Badge variant="outline" className="border-scientific/30 text-scientific">
            <Activity className="w-3 h-3 mr-1" /> 250 Connections
          </Badge>
          <Badge variant="outline" className="border-governance/30 text-governance">
            <ShieldAlert className="w-3 h-3 mr-1" /> Governance Sync: OK
          </Badge>
        </div>
      </div>

      <div className="flex-1 grid grid-cols-4 gap-6 min-h-0">
        <Card className="col-span-3 h-full bg-surface-elevated/50 border-border/50 backdrop-blur-sm overflow-hidden relative group">
          <div className="absolute inset-0 z-0 opacity-20 group-hover:opacity-10 transition-opacity pointer-events-none" 
               style={{ backgroundImage: 'radial-gradient(circle at center, var(--eureka-cognitive) 0%, transparent 70%)' }} />
          <ReactECharts 
            option={option} 
            style={{ height: '100%', width: '100%' }}
            theme="dark"
            opts={{ renderer: 'canvas' }}
          />
        </Card>

        <div className="col-span-1 flex flex-col gap-4 overflow-y-auto pr-2 custom-scrollbar">
          <Card className="p-4 bg-surface-elevated border-border">
            <h3 className="text-sm font-mono text-text-secondary uppercase tracking-wider mb-4">Node Distribution</h3>
            <div className="space-y-4">
              {[
                { name: 'Cognitive Core', color: 'bg-cognitive', count: 35 },
                { name: 'Scientific Data', color: 'bg-scientific', count: 65 },
                { name: 'Governance Rules', color: 'bg-governance', count: 40 },
                { name: 'Human Interfaces', color: 'bg-human', count: 10 },
              ].map(stat => (
                <div key={stat.name}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-text-primary">{stat.name}</span>
                    <span className="text-text-muted font-mono">{stat.count}</span>
                  </div>
                  <div className="h-1.5 w-full bg-surface-glass rounded-full overflow-hidden">
                    <div className={`h-full ${stat.color}`} style={{ width: `${(stat.count / 150) * 100}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </Card>

          <Card className="p-4 bg-surface-elevated border-border flex-1">
            <h3 className="text-sm font-mono text-text-secondary uppercase tracking-wider mb-4">System Anomalies</h3>
            <div className="space-y-3">
              {[1, 2, 3].map(i => (
                <div key={i} className="p-3 bg-surface-glass rounded border border-border/50 hover:border-blocked/30 transition-colors cursor-pointer group">
                  <div className="flex items-center gap-2 mb-1">
                    <div className="w-2 h-2 rounded-full bg-blocked animate-pulse" />
                    <span className="text-xs font-mono text-blocked">ANOMALY-{Math.floor(Math.random() * 1000)}</span>
                  </div>
                  <p className="text-xs text-text-secondary line-clamp-2">High latency detected in semantic vector retrieval from scientific nodes in sector 7G.</p>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
