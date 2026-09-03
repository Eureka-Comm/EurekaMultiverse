import ReactECharts from 'echarts-for-react';
import { useAnalyticalStore } from '../../store/analyticalStore';
import { useMemo } from 'react';

export function ScientificSurface() {
  const { alternatives, selectedEntityId, selectEntity } = useAnalyticalStore();

  const option = useMemo(() => {
    // Generate data for utility curves/distributions based on alternatives
    
    // Base normal distribution function for confidence visualization
    const generateDistribution = (mean: number, variance: number) => {
       const points = [];
       for (let x = 0; x <= 1; x += 0.02) {
          const exponent = -Math.pow(x - mean, 2) / (2 * variance);
          const y = (1 / Math.sqrt(2 * Math.PI * variance)) * Math.exp(exponent);
          points.push([x, y]);
       }
       return points;
    };

    const series = alternatives.map(a => {
       const isSelected = a.id === selectedEntityId;
       const color = isSelected 
         ? 'var(--eureka-signal-cognitive)' 
         : a.status === 'SELECTED' ? 'var(--eureka-signal-scientific)' : 'var(--eureka-spatial-hairline)';
         
       return {
         name: a.title,
         type: 'line',
         smooth: true,
         showSymbol: false,
         data: generateDistribution(a.utility, a.scientificMetrics.variance || 0.05),
         lineStyle: {
           width: isSelected ? 3 : 1,
           color: color
         },
         areaStyle: {
           color: color,
           opacity: isSelected ? 0.3 : 0.05
         },
         markLine: isSelected ? {
           data: [{ xAxis: a.utility, name: 'Mean Utility' }],
           label: { show: false },
           lineStyle: { type: 'dashed', color: color }
         } : undefined
       };
    });

    return {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'var(--eureka-surface-elevated)',
        borderColor: 'var(--eureka-spatial-hairline)',
        textStyle: { fontFamily: 'monospace', fontSize: 10, color: 'var(--eureka-text-technical)' }
      },
      grid: { left: '8%', right: '5%', bottom: '15%', top: '10%' },
      xAxis: {
        type: 'value',
        name: 'UTILITY SCORE',
        nameLocation: 'middle',
        nameGap: 25,
        nameTextStyle: { color: 'var(--eureka-text-technical)', fontFamily: 'monospace', fontSize: 9 },
        splitLine: { show: true, lineStyle: { color: 'var(--eureka-spatial-hairline)', type: 'dashed' } },
        axisLabel: { color: 'var(--eureka-text-muted)', fontFamily: 'monospace', fontSize: 9 }
      },
      yAxis: {
        type: 'value',
        name: 'PROBABILITY DENSITY',
        nameLocation: 'middle',
        nameGap: 30,
        nameTextStyle: { color: 'var(--eureka-text-technical)', fontFamily: 'monospace', fontSize: 9 },
        splitLine: { show: true, lineStyle: { color: 'var(--eureka-spatial-hairline)' } },
        axisLabel: { show: false }
      },
      series: series
    };
  }, [alternatives, selectedEntityId]);

  return (
    <div className="w-full h-full min-h-[300px] border border-[var(--eureka-spatial-hairline)] bg-surface relative overflow-hidden flex flex-col p-2">
      <div className="absolute inset-0 fabric-grid-bg opacity-30 pointer-events-none" />
      <div className="text-[10px] font-mono text-text-technical uppercase tracking-widest absolute top-2 left-2 z-10 pointer-events-none">
        Scientific Validation Surface
      </div>
      <ReactECharts 
        option={option} 
        style={{ height: '100%', width: '100%' }} 
        notMerge={true}
      />
    </div>
  );
}
