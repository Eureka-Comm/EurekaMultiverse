import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { BarChart3, ArrowRight } from "lucide-react";
import ReactECharts from 'echarts-for-react';

export default function Evaluations() {
  const chartOption = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'value', boundaryGap: [0, 0.01], splitLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } }, axisLabel: { color: 'rgba(255,255,255,0.5)' } },
    yAxis: { type: 'category', data: ['ALT-D', 'ALT-C', 'ALT-A', 'ALT-B'], axisLabel: { color: 'rgba(255,255,255,0.8)' } },
    series: [
      {
        name: 'Truth Value',
        type: 'bar',
        data: [0.35, 0.61, 0.84, 0.91],
        itemStyle: { color: 'var(--eureka-scientific)' },
      }
    ]
  };

  return (
    <div className="flex flex-col h-full p-8 bg-canvas">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-text">Scientific Evaluation</h1>
          <p className="text-text-muted mt-1 text-sm">Truth value assessment of alternatives against the objective predicate.</p>
        </div>
        <Badge variant="neutral" className="bg-surface border-border">DEMO DATA</Badge>
      </div>

      <div className="grid grid-cols-2 gap-6 flex-1">
        <Card className="bg-surface-elevated border-border flex flex-col">
          <CardHeader className="border-b border-border">
            <CardTitle className="text-sm uppercase tracking-widest text-text-muted flex items-center gap-2">
              <BarChart3 className="h-4 w-4" />
              Utility Distribution
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1 p-4 relative">
             <ReactECharts option={chartOption} style={{ height: '100%', width: '100%', minHeight: '300px' }} />
          </CardContent>
        </Card>

        <div className="space-y-4">
          {[
            { id: 'ALT-B', score: 0.91, pass: true },
            { id: 'ALT-A', score: 0.84, pass: true },
            { id: 'ALT-C', score: 0.61, pass: false },
            { id: 'ALT-D', score: 0.35, pass: false }
          ].map((alt) => (
            <Card key={alt.id} className="bg-surface border-border hover:border-text-muted transition-colors cursor-pointer">
              <CardContent className="p-4 flex items-center justify-between">
                <div>
                  <h3 className="font-mono text-lg font-bold text-text">{alt.id}</h3>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs text-text-muted uppercase">Utility</span>
                    <span className="font-mono text-scientific">{alt.score.toFixed(2)}</span>
                  </div>
                </div>
                <div>
                  {alt.pass ? 
                    <Badge variant="scientific">SATISFIES PREDICATE</Badge> : 
                    <Badge variant="neutral" className="border-border">FAILS PREDICATE</Badge>
                  }
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}