import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { Share2 } from "lucide-react";
import ReactECharts from 'echarts-for-react';

export default function Networks() {
  const graphOption = {
    backgroundColor: 'transparent',
    tooltip: {},
    animationDurationUpdate: 1500,
    animationEasingUpdate: 'quinticInOut',
    series: [
      {
        type: 'graph',
        layout: 'force',
        symbolSize: 40,
        roam: true,
        label: { show: true, color: '#fff' },
        edgeSymbol: ['circle', 'arrow'],
        edgeSymbolSize: [4, 10],
        edgeLabel: { fontSize: 10 },
        force: { repulsion: 1000, edgeLength: 150 },
        data: [
          { name: 'Objective', itemStyle: { color: 'var(--eureka-cognitive)' } },
          { name: 'AF-249', itemStyle: { color: 'var(--eureka-scientific)' } },
          { name: 'Constraint 1', itemStyle: { color: 'var(--eureka-text-muted)' } },
          { name: 'Constraint 2', itemStyle: { color: 'var(--eureka-text-muted)' } },
          { name: 'Human Auth', itemStyle: { color: 'var(--eureka-governance)' } },
          { name: 'Rule_Set_A', itemStyle: { color: 'var(--eureka-text-muted)' } },
          { name: 'Actioner', itemStyle: { color: 'var(--eureka-authorized)' } }
        ],
        links: [
          { source: 'Objective', target: 'Constraint 1' },
          { source: 'Objective', target: 'Constraint 2' },
          { source: 'Objective', target: 'AF-249' },
          { source: 'Constraint 1', target: 'Rule_Set_A' },
          { source: 'AF-249', target: 'Human Auth' },
          { source: 'Human Auth', target: 'Actioner' }
        ],
        lineStyle: { opacity: 0.9, width: 2, curveness: 0.2, color: 'var(--eureka-border)' }
      }
    ]
  };

  return (
    <div className="flex flex-col h-full p-8 bg-canvas">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-text">Entity Networks</h1>
          <p className="text-text-muted mt-1 text-sm">Force-directed graphs of decision lineage and authority dependencies.</p>
        </div>
        <Badge variant="neutral" className="bg-surface border-border">DEMO DATA</Badge>
      </div>

      <Card className="bg-surface-elevated border-border flex-1 flex flex-col">
        <CardHeader className="border-b border-border">
          <CardTitle className="text-sm uppercase tracking-widest text-text-muted flex items-center gap-2">
            <Share2 className="h-4 w-4" />
            Dependency Topology
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0 flex-1">
          <ReactECharts option={graphOption} style={{ height: '100%', width: '100%', minHeight: '500px' }} />
        </CardContent>
      </Card>
    </div>
  );
}