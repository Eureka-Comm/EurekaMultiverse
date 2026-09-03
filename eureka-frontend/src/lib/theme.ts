export const EUREKA_THEME = {
  colors: {
    canvas: "#030304",
    surface: "#0a0a0d",
    surfaceElevated: "#111116",
    surfaceSelected: "#16161c",
    surfaceActive: "#1c1c24",
    
    signals: {
      cognitive: "#2e8fff",
      semantic: "#00b4d8",
      scientific: "#8a4fff",
      ranking: "#6366f1",
      authority: "#10b981",
      freeze: "#f59e0b",
      action: "#059669",
      warning: "#ea580c",
      blocked: "#e11d48",
    },
    
    spatial: {
      hairline: "rgba(255, 255, 255, 0.08)",
      grid: "rgba(255, 255, 255, 0.03)",
    },
    
    text: {
      display: "#ffffff",
      section: "#e4e4e7",
      label: "#a1a1aa",
      metric: "#f4f4f5",
      technical: "#71717a",
      micro: "#52525b",
    }
  }
};

/**
 * Base ECharts theme configuration tailored to the EUREKA Fabric aesthetics.
 * Uses high-end scientific instrument styling (no library defaults).
 */
export const getEChartsTheme = () => {
  return {
    color: [
      EUREKA_THEME.colors.signals.cognitive,
      EUREKA_THEME.colors.signals.scientific,
      EUREKA_THEME.colors.signals.semantic,
      EUREKA_THEME.colors.signals.ranking,
    ],
    backgroundColor: 'transparent',
    textStyle: {
      fontFamily: '"Inter", system-ui, sans-serif',
      color: EUREKA_THEME.colors.text.label,
    },
    title: {
      textStyle: {
        color: EUREKA_THEME.colors.text.section,
        fontSize: 14,
        fontWeight: 500,
      }
    },
    line: {
      itemStyle: {
        borderWidth: 2,
      },
      lineStyle: {
        width: 2,
      },
      symbolSize: 6,
      symbol: 'circle',
      smooth: true
    },
    scatter: {
      itemStyle: {
        borderWidth: 1,
        borderColor: EUREKA_THEME.colors.spatial.hairline,
      }
    },
    categoryAxis: {
      axisLine: {
        show: true,
        lineStyle: {
          color: EUREKA_THEME.colors.spatial.hairline,
        }
      },
      axisTick: {
        show: false,
      },
      axisLabel: {
        show: true,
        color: EUREKA_THEME.colors.text.technical,
      },
      splitLine: {
        show: false,
      }
    },
    valueAxis: {
      axisLine: {
        show: false,
      },
      axisTick: {
        show: false,
      },
      axisLabel: {
        show: true,
        color: EUREKA_THEME.colors.text.technical,
      },
      splitLine: {
        show: true,
        lineStyle: {
          color: EUREKA_THEME.colors.spatial.grid,
          type: 'dashed'
        }
      }
    },
    tooltip: {
      backgroundColor: EUREKA_THEME.colors.surfaceElevated,
      borderColor: EUREKA_THEME.colors.spatial.hairline,
      textStyle: {
        color: EUREKA_THEME.colors.text.metric,
      },
      padding: [8, 12],
      backdropFilter: 'blur(8px)',
      borderRadius: 4
    }
  };
};
