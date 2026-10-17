import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';

export interface TimeSeriesPoint {
  date: string;
  value: number;
}

export interface TimeSeriesAnomalyWindow {
  startDate: string;
  endDate: string;
  label?: string;
  color?: string;
}

interface TimeSeriesChartProps {
  title?: string;
  subtitle?: string;
  height?: string | number;
  series: Array<{
    name: string;
    data: Array<[string, number] | { value: [string, number]; [key: string]: unknown }>;
    color?: string;
    type?: 'line' | 'bar' | 'scatter';
    area?: boolean;
    dashed?: boolean;
  }>;
  anomalyWindows?: TimeSeriesAnomalyWindow[];
  forecastStartDate?: string;
  yAxisLabel?: string;
  yAxisMin?: number;
  yAxisMax?: number;
  loading?: boolean;
}

export const TimeSeriesChart: React.FC<TimeSeriesChartProps> = ({
  title,
  subtitle,
  height = 300,
  series,
  anomalyWindows = [],
  forecastStartDate,
  yAxisLabel,
  yAxisMin,
  yAxisMax,
  loading = false,
}) => {
  const chartRef = useRef<HTMLDivElement | null>(null);
  const chartInstance = useRef<echarts.EChartsType | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current, undefined, {
        renderer: 'canvas',
      });
    }

    const chart = chartInstance.current;

    if (loading) {
      chart.showLoading({
        text: 'Streaming Telemetry...',
        color: '#1DE9C0',
        textColor: '#3B1D5E',
        maskColor: 'rgba(250, 250, 254, 0.85)',
      });
      return;
    } else {
      chart.hideLoading();
    }

    // Construct markArea pieces for anomalies
    const markAreaPieces: Array<[
      { coord: [string, number | undefined]; itemStyle?: { color?: string } },
      { coord: [string, number | undefined] }
    ]> = [];

    // Add forecast shading if provided (Lilac tint)
    if (forecastStartDate) {
      markAreaPieces.push([
        {
          coord: [forecastStartDate, undefined],
          itemStyle: {
            color: 'rgba(201, 162, 245, 0.12)',
          },
        },
        {
          coord: ['9999-12-31', undefined],
        },
      ]);
    }

    // Add anomaly window shadings
    anomalyWindows.forEach((win) => {
      markAreaPieces.push([
        {
          coord: [win.startDate, undefined],
          itemStyle: {
            color: win.color || 'rgba(220, 38, 38, 0.15)',
          },
        },
        {
          coord: [win.endDate, undefined],
        },
      ]);
    });

    const defaultColors = ['#1DE9C0', '#7C3AED', '#0E7490', '#DC2626', '#D97706'];

    const echartsSeries = series.map((s, idx) => {
      const color = s.color || defaultColors[idx % defaultColors.length];
      return {
        name: s.name,
        type: s.type || 'line',
        smooth: true,
        showSymbol: false,
        lineStyle: {
          width: 2.2,
          color,
          type: s.dashed ? 'dashed' : 'solid',
        },
        itemStyle: {
          color,
        },
        areaStyle: s.area
          ? {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: color + '40' },
                { offset: 1, color: color + '00' },
              ]),
            }
          : undefined,
        data: s.data as unknown as echarts.SeriesOption['data'],
        markArea:
          idx === 0 && markAreaPieces.length > 0
            ? {
                silent: true,
                data: markAreaPieces as unknown as echarts.MarkAreaComponentOption['data'],
              }
            : undefined,
      };
    }) as unknown as echarts.SeriesOption[];

    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      title: title
        ? {
            text: title,
            subtext: subtitle,
            textStyle: {
              color: '#3B1D5E',
              fontSize: 13,
              fontWeight: 600,
              fontFamily: '"Plus Jakarta Sans", sans-serif',
            },
            subtextStyle: {
              color: '#6B5B84',
              fontSize: 11,
              fontFamily: '"Plus Jakarta Sans", sans-serif',
            },
            left: 0,
            top: 0,
          }
        : undefined,
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#FFFFFF',
        borderColor: '#E6E2F0',
        borderWidth: 1,
        textStyle: {
          color: '#3B1D5E',
          fontSize: 11,
          fontFamily: '"JetBrains Mono", monospace',
        },
        padding: [10, 14],
        shadowColor: 'rgba(59, 29, 94, 0.08)',
        shadowBlur: 10,
      },
      legend: {
        top: title ? 2 : 0,
        right: 0,
        textStyle: {
          color: '#6B5B84',
          fontSize: 11,
          fontFamily: '"Plus Jakarta Sans", sans-serif',
        },
        icon: 'circle',
      },
      grid: {
        top: title ? 52 : 24,
        left: '2%',
        right: '3%',
        bottom: '8%',
        containLabel: true,
      },
      xAxis: {
        type: 'time',
        axisLine: { lineStyle: { color: '#E6E2F0' } },
        axisLabel: {
          color: '#6B5B84',
          fontSize: 10,
          fontFamily: '"JetBrains Mono", monospace',
        },
        splitLine: { show: false },
      },
      yAxis: {
        type: 'value',
        name: yAxisLabel,
        min: yAxisMin,
        max: yAxisMax,
        nameTextStyle: {
          color: '#6B5B84',
          fontSize: 10,
          fontFamily: '"JetBrains Mono", monospace',
        },
        axisLine: { show: false },
        axisLabel: {
          color: '#6B5B84',
          fontSize: 10,
          fontFamily: '"JetBrains Mono", monospace',
        },
        splitLine: {
          lineStyle: {
            color: '#EDE9F5',
            type: 'dashed',
          },
        },
      },
      series: echartsSeries,
    };

    chart.setOption(option, true);

    const handleResize = () => chart.resize();
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [title, subtitle, series, anomalyWindows, forecastStartDate, yAxisLabel, yAxisMin, yAxisMax, loading]);

  useEffect(() => {
    return () => {
      chartInstance.current?.dispose();
      chartInstance.current = null;
    };
  }, []);

  return (
    <div className="w-full relative">
      <div ref={chartRef} style={{ width: '100%', height }} />
    </div>
  );
};
