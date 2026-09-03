import { useEffect, useState } from "react";
import ReactECharts from "echarts-for-react";
import { Card, CardHeader, CardTitle, CardContent } from "../../components/ui/Card";
import { DemoDecisionRepository } from "../../infrastructure/adapters/DemoDecisionRepository";
import { type DecisionViewModel } from "../../domain/models";
import { BarChart2, ScatterChart } from "lucide-react";

const repo = new DemoDecisionRepository();

export default function Dashboard() {
  const [decision, setDecision] = useState<DecisionViewModel | null>(null);

  useEffect(() => {
    repo.getDecision("case-001").then(setDecision);
  }, []);

  if (!decision) return <div className="p-6 text-text-muted">Loading Analytics Engine...</div>;

  const alts = decision.alternatives;
  
  // Scatter Plot: Risk vs ROI
  const scatterOptions = {
    backgroundColor: 'transparent',
    textStyle: { fontFamily: 'var(--font-sans)', color: 'var(--eureka-text-secondary)' },
    tooltip: {
      trigger: 'item',
      backgroundColor: 'var(--eureka-surface-elevated)',
      borderColor: 'rgba(255,255,255,0.1)',
      textStyle: { color: 'var(--eureka-text-primary)' },
      formatter: function (params: any) {
        return `${params.name}<br/>Risk: ${params.value[0]}<br/>ROI: ${params.value[1]}`;
      }
    },
    xAxis: { 
      type: 'value', 
      name: 'Risk', 
      nameLocation: 'middle', 
      nameGap: 30,
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } },
      axisLabel: { color: 'var(--eureka-text-muted)' }
    },
    yAxis: { 
      type: 'value', 
      name: 'Expected ROI',
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } },
      axisLabel: { color: 'var(--eureka-text-muted)' }
    },
    series: [
      {
        symbolSize: 20,
        data: alts.map(a => ({
          name: a.name,
          value: [a.data.risk, a.data.expectedROI],
          itemStyle: { 
            color: a.data.risk > 0.5 ? 'var(--eureka-blocked)' : 'var(--eureka-scientific)',
            shadowBlur: 10,
            shadowColor: a.data.risk > 0.5 ? 'rgba(239,68,68,0.5)' : 'rgba(139,92,246,0.5)'
          }
        })),
        type: 'scatter'
      }
    ]
  };

  // Bar Chart: Cost Comparison
  const barOptions = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: 'var(--eureka-surface-elevated)',
      borderColor: 'rgba(255,255,255,0.1)',
      textStyle: { color: 'var(--eureka-text-primary)' }
    },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      data: alts.map(a => a.name),
      axisLabel: { color: 'var(--eureka-text-muted)' }
    },
    yAxis: {
      type: 'value',
      name: 'Cost ($)',
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } },
      axisLabel: { color: 'var(--eureka-text-muted)' }
    },
    series: [
      {
        name: 'Cost',
        type: 'bar',
        barWidth: '40%',
        data: alts.map(a => ({
          value: a.data.cost,
          itemStyle: { color: 'var(--eureka-cognitive)', borderRadius: [4, 4, 0, 0] }
        }))
      }
    ]
  };

  return (
    <div className="flex h-full flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Analytics Dashboard</h1>
          <p className="text-sm text-text-muted mt-1">Advanced data exploration using Apache ECharts.</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6 flex-1">
        <Card className="bg-surface-elevated/30 border-white/5 flex flex-col">
          <CardHeader className="border-b border-white/5 pb-4">
            <CardTitle className="text-lg flex items-center gap-2">
              <ScatterChart className="h-5 w-5 text-scientific" />
              Risk vs Return (Phase Space)
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1 p-4">
            <ReactECharts option={scatterOptions} style={{ height: '100%', width: '100%', minHeight: '350px' }} theme="dark" />
          </CardContent>
        </Card>

        <Card className="bg-surface-elevated/30 border-white/5 flex flex-col">
          <CardHeader className="border-b border-white/5 pb-4">
            <CardTitle className="text-lg flex items-center gap-2">
              <BarChart2 className="h-5 w-5 text-cognitive" />
              Capital Requirements
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1 p-4">
            <ReactECharts option={barOptions} style={{ height: '100%', width: '100%', minHeight: '350px' }} theme="dark" />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}