import ReactECharts from 'echarts-for-react';
import { useAnalyticalStore } from '../../store/analyticalStore';
import { useMemo } from 'react';

export function DecisionPhaseSpace() {
  const { alternatives, selectedEntityId, selectEntity } = useAnalyticalStore();

  const option = useMemo(() => {
    const data = alternatives.map(a => ({
      name: a.title,
      value: [a.risk, a.utility, a.confidence, a.id],
      itemStyle: {
        color: a.id === selectedEntityId 
          ? 'var(--eureka-signal-cognitive)' 
          : a.status === 'SELECTED' 
            ? 'var(--eureka-signal-scientific)' 
            : 'var(--eureka-text-muted)'
      }
    }));

    return {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'item',
        formatter: (params: any) => {
          return `<div style="font-family: monospace; font-size: 10px; background: var(--eureka-surface); border: 1px solid var(--eureka-spatial-hairline); padding: 8px;">
            <div style="color: var(--eureka-text-primary); font-weight: bold; margin-bottom: 4px;">${params.data.name}</div>
            <div>Risk: ${params.value[0].toFixed(2)}</div>
            <div>Utility: ${params.value[1].toFixed(2)}</div>
            <div>Confidence: ${(params.value[2] * 100).toFixed(0)}%</div>
          </div>`;
        },
        backgroundColor: 'transparent',
        borderColor: 'transparent',
        shadowBlur: 0
      },
      grid: { left: '10%', right: '5%', bottom: '15%', top: '15%' },
      xAxis: {
        type: 'value',
        name: 'RISK',
        nameLocation: 'middle',
        nameGap: 25,
        nameTextStyle: { color: 'var(--eureka-text-technical)', fontFamily: 'monospace', fontSize: 10 },
        splitLine: { show: true, lineStyle: { color: 'var(--eureka-spatial-hairline)', type: 'dashed' } },
        axisLabel: { color: 'var(--eureka-text-muted)', fontFamily: 'monospace', fontSize: 9 }
      },
      yAxis: {
        type: 'value',
        name: 'UTILITY',
        nameLocation: 'middle',
        nameGap: 35,
        nameTextStyle: { color: 'var(--eureka-text-technical)', fontFamily: 'monospace', fontSize: 10 },
        splitLine: { show: true, lineStyle: { color: 'var(--eureka-spatial-hairline)' } },
        axisLabel: { color: 'var(--eureka-text-muted)', fontFamily: 'monospace', fontSize: 9 }
      },
      series: [
        {
          type: 'scatter',
          symbolSize: (data: any) => data[2] * 30, // Size by confidence
          data: data,
          itemStyle: {
            shadowBlur: 10,
            shadowColor: 'rgba(0,0,0,0.5)'
          },
          label: {
            show: true,
            formatter: '{b}',
            position: 'right',
            color: 'var(--eureka-text-technical)',
            fontFamily: 'monospace',
            fontSize: 9
          }
        },
        // Feasible region representation (background polygon or simple line)
        {
           type: 'line',
           markLine: {
             silent: true,
             lineStyle: { color: 'var(--eureka-signal-authority)', type: 'dashed' },
             label: { formatter: 'Risk Boundary', position: 'insideStartTop', color: 'var(--eureka-signal-authority)', fontFamily: 'monospace', fontSize: 9 },
             data: [ { xAxis: 0.30 } ] // Example from constraint CN-01
           }
        }
      ]
    };
  }, [alternatives, selectedEntityId]);

  const onEvents = {
    click: (params: any) => {
      if (params.componentType === 'series' && params.seriesType === 'scatter') {
        const id = params.data.value[3];
        selectEntity(id, 'ALTERNATIVE');
      }
    }
  };

  return (
    <div className="w-full h-full min-h-[300px] border border-[var(--eureka-spatial-hairline)] bg-surface relative overflow-hidden flex flex-col p-2">
      <div className="absolute inset-0 fabric-grid-bg opacity-30 pointer-events-none" />
      <ReactECharts 
        option={option} 
        style={{ height: '100%', width: '100%' }} 
        onEvents={onEvents}
        notMerge={true}
      />
    </div>
  );
}
