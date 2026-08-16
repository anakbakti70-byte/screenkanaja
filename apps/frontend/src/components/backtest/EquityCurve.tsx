import React, { useEffect, useRef } from 'react';
import { createChart, ColorType, IChartApi, ISeriesApi } from 'lightweight-charts';

interface EquityCurveProps {
    data: { time: string, value: number }[];
}

export const EquityCurve: React.FC<EquityCurveProps> = ({ data }) => {
    const chartContainerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<IChartApi | null>(null);
    const lineSeriesRef = useRef<ISeriesApi<"Area"> | null>(null);

    useEffect(() => {
        if (!chartContainerRef.current) return;

        const chart = createChart(chartContainerRef.current, {
            layout: {
                background: { type: ColorType.Solid, color: 'transparent' },
                textColor: '#94a3b8',
            },
            grid: {
                vertLines: { visible: false },
                horzLines: { color: 'rgba(51, 65, 85, 0.1)' },
            },
            width: chartContainerRef.current.clientWidth,
            height: 300,
            timeScale: {
                borderColor: 'rgba(51, 65, 85, 0.1)',
                timeVisible: true,
            },
            rightPriceScale: {
                borderColor: 'rgba(51, 65, 85, 0.1)',
                autoScale: true,
                scaleMargins: {
                    top: 0.1,
                    bottom: 0.1,
                },
            },
        });

        const areaSeries = chart.addAreaSeries({
            lineColor: '#3b82f6',
            topColor: 'rgba(59, 130, 246, 0.2)',
            bottomColor: 'rgba(59, 130, 246, 0.0)',
            lineWidth: 2,
        });

        lineSeriesRef.current = areaSeries;
        chartRef.current = chart;

        const handleResize = () => {
            if (chartContainerRef.current) {
                chart.applyOptions({ width: chartContainerRef.current.clientWidth });
            }
        };

        window.addEventListener('resize', handleResize);

        return () => {
            window.removeEventListener('resize', handleResize);
            chart.remove();
        };
    }, []);

    useEffect(() => {
        if (lineSeriesRef.current && data) {
            try {
                const formattedData = data
                    .filter(item => item.time && !isNaN(item.value))
                    .map(item => ({
                        time: typeof item.time === 'string'
                            ? Math.floor(new Date(item.time).getTime() / 1000)
                            : item.time,
                        value: Number(item.value)
                    }));

                // Ensure unique and sorted
                const uniqueData = formattedData.filter((v, i, a) => a.findIndex(t => t.time === v.time) === i);
                uniqueData.sort((a, b) => (a.time as number) - (b.time as number));

                if (uniqueData.length > 0) {
                    lineSeriesRef.current.setData(uniqueData as any);
                    chartRef.current?.timeScale().fitContent();
                }
            } catch (err) {
                console.error("Equity Curve render error:", err);
            }
        }
    }, [data]);

    return (
        <div className="w-full h-[300px] relative">
            <div ref={chartContainerRef} className="w-full h-full" />
        </div>
    );
};
