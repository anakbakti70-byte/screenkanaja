import React, { useEffect, useRef } from 'react';
import { createChart, ColorType, LineStyle, CandlestickData, IChartApi, ISeriesApi } from 'lightweight-charts';

interface PatternChartProps {
    data: any; // Standard Professional API Object
    metadata?: any;
}

export const PatternChart: React.FC<PatternChartProps> = ({ data, metadata }) => {
    const chartContainerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<IChartApi | null>(null);
    const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
    const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);
    const aoSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);

    useEffect(() => {
        if (!chartContainerRef.current) return;

        const container = chartContainerRef.current;
        container.innerHTML = '';

        const chart = createChart(container, {
            layout: { background: { type: ColorType.Solid, color: '#0f172a' }, textColor: '#94a3b8' },
            grid: {
                vertLines: { color: 'rgba(51, 65, 85, 0.1)', style: LineStyle.Dotted },
                horzLines: { color: 'rgba(51, 65, 85, 0.1)', style: LineStyle.Dotted },
            },
            width: container.clientWidth,
            height: 600,
            timeScale: { timeVisible: true, secondsVisible: false, borderColor: '#1e293b' },
            rightPriceScale: { borderColor: '#1e293b' },
        });

        chartRef.current = chart;

        // 1. Candle Series
        const candlestickSeries = chart.addCandlestickSeries({
            upColor: '#10b981', downColor: '#ef4444', borderVisible: true,
            wickUpColor: '#10b981', wickDownColor: '#ef4444', borderColor: '#1e293b'
        });
        candleSeriesRef.current = candlestickSeries;

        // 2. Volume Series (Histogram)
        const volumeSeries = chart.addHistogramSeries({
            priceFormat: { type: 'volume' },
            priceScaleId: 'volume-scale',
        });
        volumeSeriesRef.current = volumeSeries;

        chart.priceScale('volume-scale').applyOptions({
            scaleMargins: { top: 0.7, bottom: 0.1 }, // Put volume at the bottom 30%
        });

        // 3. Awesome Oscillator Series (Black Line)
        const aoSeries = chart.addLineSeries({
            color: '#000000', lineWidth: 2, title: 'AO', priceScaleId: 'ao-scale'
        });
        aoSeriesRef.current = aoSeries;

        chart.priceScale('ao-scale').applyOptions({
            scaleMargins: { top: 0.85, bottom: 0.02 }, // Put AO at the very bottom
            borderVisible: false,
        });

        const handleResize = () => chart.applyOptions({ width: container.clientWidth });
        window.addEventListener('resize', handleResize);

        return () => {
            window.removeEventListener('resize', handleResize);
            chart.remove();
        };
    }, []);

    useEffect(() => {
        if (!candleSeriesRef.current || !volumeSeriesRef.current || !aoSeriesRef.current || !data || !data.candles) return;

        const candles = data.candles;

        // Format Candles
        const formattedCandles = candles.map((c: any) => ({
            time: c.time as any,
            open: c.open, high: c.high, low: c.low, close: c.close
        }));

        // Format Volume with Color (Follows Candle Direction)
        const formattedVolume = candles.map((c: any) => ({
            time: c.time as any,
            value: c.volume,
            color: c.close >= c.open ? 'rgba(16, 185, 129, 0.4)' : 'rgba(239, 68, 68, 0.4)'
        }));

        // Format AO
        const formattedAO = candles
            .filter((c: any) => c.ao !== null)
            .map((c: any) => ({ time: c.time as any, value: c.ao }));

        candleSeriesRef.current.setData(formattedCandles);
        volumeSeriesRef.current.setData(formattedVolume);
        aoSeriesRef.current.setData(formattedAO);

        // Markers for Patterns
        if (metadata && metadata.metadata && metadata.metadata.pivots) {
            const markers: any[] = [];
            Object.entries(metadata.metadata.pivots).forEach(([key, p]: [string, any]) => {
                const targetCandle = candles.find((c: any, idx: number) => idx === p.idx);
                if (targetCandle) {
                    markers.push({
                        time: targetCandle.time, position: 'belowBar',
                        color: '#f59e0b', shape: 'arrowUp', text: key.toUpperCase()
                    });
                }
            });
            candleSeriesRef.current.setMarkers(markers);
        }

        chartRef.current?.timeScale().fitContent();
    }, [data, metadata]);

    return (
        <div className="w-full h-full relative group">
            <div ref={chartContainerRef} className="w-full h-full" />

            {/* Info Overlays */}
            <div className="absolute top-4 left-6 pointer-events-none z-10 space-y-2">
                <div className="flex items-center gap-4 bg-slate-950/40 backdrop-blur-md px-3 py-1.5 rounded-lg border border-white/5">
                    <div className="flex items-center gap-1.5">
                        <div className="w-3 h-3 rounded bg-emerald-500/60" />
                        <span className="text-[10px] font-black text-slate-300 uppercase">Volume</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                        <div className="w-3 h-0.5 bg-black" />
                        <span className="text-[10px] font-black text-slate-300 uppercase">AO (Bill Williams)</span>
                    </div>
                </div>
            </div>
        </div>
    );
};
