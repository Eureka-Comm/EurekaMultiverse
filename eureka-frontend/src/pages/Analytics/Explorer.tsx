import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { LineChart, Search, Filter } from "lucide-react";
import ReactECharts from 'echarts-for-react';

export default function Explorer() {
  const chartOption = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    legend: { data: ['Utility', 'Cost', 'Risk'], textStyle: { color: 'rgba(255,255,255,0.7)' }, bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '10%', containLabel: true },
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      { start: 0, end: 100, handleIcon: 'M10.7,11.9v-1.3H9.3v1.3c-4.9,0.3-8.8,4.4-8.8,9.4c0,5,3.9,9.1,8.8,9.4v1.3h1.3v-1.3c4.9-0.3,8.8-4.4,8.8-9.4C19.5,16.3,15.6,12.2,10.7,11.9z M13.3,24.4H6.7V23h6.6V24.4z M13.3,19.6H6.7v-1.4h6.6V19.6z', handleSize: '80%', handleStyle: { color: '#fff', shadowBlur: 3, shadowColor: 'rgba(0, 0, 0, 0.6)', shadowOffsetX: 2, shadowOffsetY: 2 } }
    ],
    xAxis: { type: 'category', boundaryGap: false, data: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'], axisLabel: { color: 'rgba(255,255,255,0.5)' } },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } }, axisLabel: { color: 'rgba(255,255,255,0.5)' } },
    series: [
      { name: 'Utility', type: 'line', smooth: true, data: [120, 132, 101, 134, 90, 230, 210, 201, 234, 190, 230, 220], itemStyle: { color: 'var(--eureka-scientific)' } },
      { name: 'Cost', type: 'line', smooth: true, data: [220, 182, 191, 234, 290, 330, 310, 312, 301, 334, 390, 330], itemStyle: { color: 'var(--eureka-text-muted)' } },
      { name: 'Risk', type: 'line', smooth: true, data: [150, 232, 201, 154, 190, 330, 410, 300, 250, 200, 150, 120], itemStyle: { color: 'var(--eureka-frozen)' } }
    ]
  };

  return (
    <div className="flex flex-col h-full p-8 bg-canvas">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-text">Data Explorer</h1>
          <p className="text-text-muted mt-1 text-sm">Interactive timeseries and dimensional analysis of decision factors.</p>
        </div>
        <Badge variant="neutral" className="bg-surface border-border">DEMO DATA</Badge>
      </div>

      <div className="flex gap-4 mb-6">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted" />
          <input 
            type="text" 
            placeholder="Filter datasets..." 
            className="w-full bg-surface border border-border rounded-md py-2 pl-10 pr-4 text-sm text-text focus:outline-none focus:border-cognitive transition-colors"
          />
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-surface-elevated border border-border rounded-md text-sm text-text hover:bg-surface-elevated/80 transition-colors">
          <Filter className="h-4 w-4" /> Dimensions
        </button>
      </div>

      <Card className="bg-surface-elevated border-border flex-1 flex flex-col">
        <CardHeader className="border-b border-border">
          <CardTitle className="text-sm uppercase tracking-widest text-text-muted flex items-center gap-2">
            <LineChart className="h-4 w-4" />
            Historical Context (Zoom/Pan Enabled)
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4 flex-1">
          <ReactECharts option={chartOption} style={{ height: '100%', width: '100%' }} />
        </CardContent>
      </Card>
    </div>
  );
}