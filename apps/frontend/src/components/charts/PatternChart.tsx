import React, { useEffect, useRef, useState } from 'react';
import { createChart, ColorType, LineStyle, IChartApi, ISeriesApi } from 'lightweight-charts';
import { LayoutGrid, BarChart2, Zap, Settings, X, Eye, EyeOff } from 'lucide-react';

interface PatternChartProps {
    data: any;
    metadata?: any;
    interactive?: boolean;
}

export const PatternChart: React.FC<PatternChartProps> = ({ data, metadata, interactive = false }) => {
    const chartContainerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<IChartApi | null>(null);
    const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
    const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);
    const aoSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
    const priceLinesRef = useRef<any[]>([]);

    const [showVolume, setShowVolume] = useState(true);
    const [showAO, setShowAO] = useState(true);
    const [layout, setLayout] = useState<'standard' | 'expanded'>('standard');

    useEffect(() => {
        if (!chartContainerRef.current) return;

        const container = chartContainerRef.current;
        container.innerHTML = '';

        const chart = createChart(container, {
            layout: {
                background: { type: ColorType.Solid, color: '#0f172a' },
                textColor: '#94a3b8',
                fontSize: 10,
                fontFamily: 'Inter, sans-serif'
            },
            grid: {
                vertLines: { color: 'rgba(51, 65, 85, 0.1)', style: LineStyle.Dotted },
                horzLines: { color: 'rgba(51, 65, 85, 0.1)', style: LineStyle.Dotted },
            },
            width: container.clientWidth,
            height: 600,
            timeScale: {
                timeVisible: true,
                secondsVisible: false,
                borderColor: '#1e293b',
                barSpacing: 6
            },
            rightPriceScale: {
                borderColor: '#1e293b',
                autoScale: true,
                scaleMargins: { top: 0.1, bottom: 0.3 }
            },
        });

        chartRef.current = chart;

        // 1. Candle Series (Main Pane)
        const candlestickSeries = chart.addCandlestickSeries({
            upColor: '#10b981', downColor: '#ef4444', borderVisible: true,
            wickUpColor: '#10b981', wickDownColor: '#ef4444', borderColor: '#1e293b'
        });
        candleSeriesRef.current = candlestickSeries;

        // 2. Volume Series (Overlay at bottom of Main Pane)
        const volumeSeries = chart.addHistogramSeries({
            priceFormat: { type: 'volume' },
            priceScaleId: 'volume-scale',
        });
        volumeSeriesRef.current = volumeSeries;

        chart.priceScale('volume-scale').applyOptions({
            scaleMargins: { top: 0.8, bottom: 0 },
            visible: showVolume
        });

        // 3. Awesome Oscillator Series (Separate bottom Pane)
        const aoSeries = chart.addLineSeries({
            color: '#22d3ee', lineWidth: 2, title: 'AO', priceScaleId: 'ao-scale'
        });
        aoSeriesRef.current = aoSeries;

        chart.priceScale('ao-scale').applyOptions({
            scaleMargins: { top: 0.85, bottom: 0.05 },
            borderVisible: false,
            visible: showAO
        });

        const handleResize = () => chart.applyOptions({ width: container.clientWidth });
        window.addEventListener('resize', handleResize);

        return () => {
            window.removeEventListener('resize', handleResize);
            chart.remove();
        };
    }, [showVolume, showAO]); // Re-create if visibility changes to adjust margins

    useEffect(() => {
        const candles = data?.history_candles || data?.candles;

        if (!candleSeriesRef.current || !volumeSeriesRef.current || !aoSeriesRef.current || !data || !candles) {
            return;
        }

        const parseTime = (t: any) => typeof t === 'string' ? Math.floor(new Date(t).getTime() / 1000) : t;

        // Clean & Format Data
        const formattedCandles = candles.map((c: any) => ({
            time: parseTime(c.time),
            open: c.open, high: c.high, low: c.low, close: c.close
        })).filter((v:any, i:any, a:any) => a.findIndex((t:any) => t.time === v.time) === i).sort((a:any, b:any) => a.time - b.time);

        const formattedVolume = candles.map((c: any) => ({
            time: parseTime(c.time),
            value: c.volume,
            color: c.close >= c.open ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)'
        })).filter((v:any, i:any, a:any) => a.findIndex((t:any) => t.time === v.time) === i).sort((a:any, b:any) => a.time - b.time);

        const formattedAO = candles.map((c: any) => ({
            time: parseTime(c.time),
            value: typeof c.ao === 'number' ? c.ao : 0
        })).filter((v:any, i:any, a:any) => a.findIndex((t:any) => t.time === v.time) === i).sort((a:any, b:any) => a.time - b.time);

        candleSeriesRef.current.setData(formattedCandles);
        if (showVolume) volumeSeriesRef.current.setData(formattedVolume);
        if (showAO) aoSeriesRef.current.setData(formattedAO);

        // --- Price Lines (Entry, SL, TP) ---
        // Clean up previous lines
        priceLinesRef.current.forEach(line => {
            candleSeriesRef.current?.removePriceLine(line);
        });
        priceLinesRef.current = [];

        if (metadata) {
            const entry = metadata.entry_price;
            const sl = metadata.stop_loss;
            const tp = metadata.take_profit || metadata.tp_short;

            if (entry) {
                const line = candleSeriesRef.current.createPriceLine({
                    price: entry,
                    color: '#3b82f6',
                    lineWidth: 2,
                    lineStyle: LineStyle.Solid,
                    axisLabelVisible: true,
                    title: 'ENTRY',
                });
                priceLinesRef.current.push(line);
            }
            if (sl) {
                const line = candleSeriesRef.current.createPriceLine({
                    price: sl,
                    color: '#ef4444',
                    lineWidth: 2,
                    lineStyle: LineStyle.Dashed,
                    axisLabelVisible: true,
                    title: 'STOP LOSS',
                });
                priceLinesRef.current.push(line);
            }
            if (tp) {
                const line = candleSeriesRef.current.createPriceLine({
                    price: tp,
                    color: '#10b981',
                    lineWidth: 2,
                    lineStyle: LineStyle.Dashed,
                    axisLabelVisible: true,
                    title: 'TAKE PROFIT',
                });
                priceLinesRef.current.push(line);
            }
        }

        // Markers Logic
        const markers: any[] = [];

        // 1. Pivots (W1-W5)
        if (metadata?.metadata?.pivots) {
            Object.entries(metadata.metadata.pivots).forEach(([key, p]: [string, any]) => {
                const targetTime = parseTime(candles[p.idx]?.time);
                if (targetTime) {
                    markers.push({
                        time: targetTime, position: 'belowBar',
                        color: '#f59e0b', shape: 'arrowUp', text: key
                    });
                }
            });
        }

        // 2. Backtest Trades
        if (data?.trades) {
            data.trades.forEach((t: any) => {
                markers.push({
                    time: parseTime(t.entry_ts), position: 'belowBar',
                    color: '#10b981', shape: 'arrowUp', text: `BUY ${t.lots ?? ''}L`
                });
                // FIX: sebelumnya warna exit SELALU merah (#ef4444) apapun hasilnya,
                // termasuk saat TAKE PROFIT dengan pnl positif -- menyesatkan secara
                // visual. Sekarang warna mengikuti hasil pnl riil per trade.
                const isProfit = typeof t.pnl === 'number' ? t.pnl >= 0 : t.reason === 'TAKE PROFIT';
                markers.push({
                    time: parseTime(t.exit_ts), position: 'aboveBar',
                    color: isProfit ? '#10b981' : '#ef4444',
                    shape: 'arrowDown',
                    text: `SELL (${t.reason}${typeof t.pnl === 'number' ? `, ${t.pnl >= 0 ? '+' : ''}${Math.round(t.pnl).toLocaleString()}` : ''})`
                });
            });
        }

        if (markers.length > 0) {
            markers.sort((a, b) => a.time - b.time);
            candleSeriesRef.current.setMarkers(markers);
        }

        chartRef.current?.timeScale().fitContent();
    }, [data, metadata, showVolume, showAO]);

    return (
        <div className="w-full h-full relative group">
            {/* Control Bar */}
            {interactive && (
                <div className="absolute top-4 right-6 z-20 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <div className="flex bg-slate-900/80 backdrop-blur-md border border-slate-700 rounded-xl overflow-hidden p-1 shadow-2xl">
                        <button
                            onClick={() => setShowVolume(!showVolume)}
                            className={`p-2 rounded-lg transition-all ${showVolume ? 'bg-blue-600 text-white' : 'text-slate-400 hover:bg-slate-800'}`}
                            title="Toggle Volume"
                        >
                            <BarChart2 className="w-4 h-4" />
                        </button>
                        <button
                            onClick={() => setShowAO(!showAO)}
                            className={`p-2 rounded-lg transition-all ${showAO ? 'bg-cyan-600 text-white' : 'text-slate-400 hover:bg-slate-800'}`}
                            title="Toggle Awesome Oscillator"
                        >
                            <Zap className="w-4 h-4" />
                        </button>
                        <div className="w-px bg-slate-700 mx-1 my-1" />
                        <button
                            onClick={() => setLayout(layout === 'standard' ? 'expanded' : 'standard')}
                            className="p-2 rounded-lg text-slate-400 hover:bg-slate-800 hover:text-white transition-all"
                            title="Switch Layout"
                        >
                            <LayoutGrid className="w-4 h-4" />
                        </button>
                    </div>
                </div>
            )}

            <div ref={chartContainerRef} className="w-full h-full" />

            {/* Info Labels */}
            <div className="absolute top-4 left-6 pointer-events-none z-10 space-y-2">
                <div className="flex flex-wrap items-center gap-3 bg-slate-950/40 backdrop-blur-md px-3 py-1.5 rounded-lg border border-white/5">
                    <div className="flex items-center gap-1.5">
                        <div className="w-2.5 h-2.5 rounded-sm bg-emerald-500" />
                        <span className="text-[9px] font-black text-slate-300 uppercase tracking-tighter">IDX Realtime</span>
                    </div>
                    {showVolume && (
                        <div className="flex items-center gap-1.5">
                            <div className="w-2.5 h-2.5 rounded-sm bg-emerald-500/30" />
                            <span className="text-[9px] font-black text-slate-400 uppercase tracking-tighter">Volume</span>
                        </div>
                    )}
                    {showAO && (
                        <div className="flex items-center gap-1.5">
                            <div className="w-2.5 h-0.5 bg-cyan-400" />
                            <span className="text-[9px] font-black text-slate-400 uppercase tracking-tighter">AO</span>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};