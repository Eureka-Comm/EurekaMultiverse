import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { GitCompare, Filter } from "lucide-react";
import ReactECharts from 'echarts-for-react';

export default function Scenarios() {
  const radarOption = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item' },
    legend: { data: ['Scenario A (Aggressive)', 'Scenario B (Conservative)'], textStyle: { color: 'rgba(255,255,255,0.7)' }, bottom: 0 },
    radar: {
      indicator: [
        { name: 'Cost Efficiency', max: 100 },
        { name: 'Speed to Market', max: 100 },
        { name: 'Risk Mitigation', max: 100 },
        { name: 'Compliance', max: 100 },
        { name: 'Scalability', max: 100 },
        { name: 'Innovation', max: 100 }
      ],
      axisName: { color: 'rgba(255,255,255,0.6)' },
      splitLine: { lineStyle: { color: ['rgba(255,255,255,0.1)'] } },
      splitArea: { show: false },
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.2)' } }
    },
    series: [
      {
        name: 'Scenario Comparison',
        type: 'radar',
        data: [
          {
            value: [80, 95, 40, 60, 90, 85],
            name: 'Scenario A (Aggressive)',
            itemStyle: { color: 'var(--eureka-cognitive)' },
            areaStyle: { color: 'rgba(var(--eureka-cognitive-rgb), 0.3)' }
          },
          {
            value: [60, 50, 95, 90, 70, 40],
            name: 'Scenario B (Conservative)',
            itemStyle: { color: 'var(--eureka-scientific)' },
            areaStyle: { color: 'rgba(var(--eureka-scientific-rgb), 0.3)' }
          }
        ]
      }
    ]
  };

  return (
    <div className="flex flex-col h-full p-8 bg-canvas">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-text">Scenario Analysis</h1>
          <p className="text-text-muted mt-1 text-sm">Compare predicted outcomes of different alternative paths.</p>
        </div>
        <Badge variant="neutral" className="bg-surface border-border">DEMO DATA</Badge>
      </div>

      <div className="grid grid-cols-3 gap-6 flex-1">
        <Card className="bg-surface-elevated border-border col-span-2 flex flex-col">
          <CardHeader className="border-b border-border">
            <CardTitle className="text-sm uppercase tracking-widest text-text-muted flex items-center gap-2">
              <GitCompare className="h-4 w-4" />
              Multidimensional Comparison
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 flex-1">
            <ReactECharts option={radarOption} style={{ height: '100%', width: '100%' }} />
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card className="bg-surface border-border">
            <CardHeader className="border-b border-border">
              <CardTitle className="text-sm uppercase tracking-widest text-text-muted">Scenario A</CardTitle>
            </CardHeader>
            <CardContent className="p-4">
              <p className="text-sm text-text-secondary mb-4">Focuses on rapid deployment and maximizing throughput, accepting higher risk margins.</p>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-text-muted">Expected Utility</span>
                  <span className="font-mono text-cognitive">0.82</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-text-muted">Risk Profile</span>
                  <span className="font-mono text-frozen">High (0.18)</span>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-surface border-border">
            <CardHeader className="border-b border-border">
              <CardTitle className="text-sm uppercase tracking-widest text-text-muted">Scenario B</CardTitle>
            </CardHeader>
            <CardContent className="p-4">
              <p className="text-sm text-text-secondary mb-4">Strict adherence to compliance and minimal risk, sacrificing speed to market.</p>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-text-muted">Expected Utility</span>
                  <span className="font-mono text-scientific">0.65</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-text-muted">Risk Profile</span>
                  <span className="font-mono text-text">Low (0.02)</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}