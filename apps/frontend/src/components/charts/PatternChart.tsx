import React, { useEffect, useRef, useState } from 'react';
import { createChart, ColorType, LineStyle, IChartApi, ISeriesApi, SeriesMarker } from 'lightweight-charts';
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
    const rsiSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);

    const priceLinesRef = useRef<any[]>([]);
    const extraSeriesRef = useRef<any[]>([]);
    const lastSymbolRef = useRef<string | null>(null);

    const [showVolume, setShowVolume] = useState(true);
    const [showAO, setShowAO] = useState(true);
    const [showRSI, setShowRSI] = useState(false);

    // --- 1. INITIALIZE BASE CHART ---
    useEffect(() => {
        if (!chartContainerRef.current) return;

        const chart = createChart(chartContainerRef.current, {
            layout: {
                background: { type: ColorType.Solid, color: '#0f172a' },
                textColor: '#94a3b8',
                fontSize: 10,
                fontFamily: 'Inter, system-ui, sans-serif'
            },
            grid: {
                vertLines: { color: 'rgba(30, 41, 59, 0.1)', style: LineStyle.Dotted },
                horzLines: { color: 'rgba(30, 41, 59, 0.1)', style: LineStyle.Dotted },
            },
            width: chartContainerRef.current.clientWidth,
            height: chartContainerRef.current.clientHeight || 600,
            timeScale: {
                timeVisible: true,
                borderColor: '#1e293b',
                barSpacing: 10,
            },
            rightPriceScale: {
                borderColor: '#1e293b',
                autoScale: true,
                scaleMargins: { top: 0.1, bottom: 0.3 }
            },
        });

        chartRef.current = chart;

        candleSeriesRef.current = chart.addCandlestickSeries({
            upColor: '#10b981', downColor: '#ef4444', borderVisible: false,
            wickUpColor: '#10b981', wickDownColor: '#ef4444'
        });

        volumeSeriesRef.current = chart.addHistogramSeries({
            priceFormat: { type: 'volume' },
            priceScaleId: 'volume-scale',
        });
        chart.priceScale('volume-scale').applyOptions({
            scaleMargins: { top: 0.82, bottom: 0 },
            visible: true
        });

        aoSeriesRef.current = chart.addLineSeries({
            color: '#22d3ee', lineWidth: 2, title: 'AO', priceScaleId: 'ao-scale'
        });
        chart.priceScale('ao-scale').applyOptions({
            scaleMargins: { top: 0.85, bottom: 0.02 },
            borderVisible: false,
            visible: true
        });

        rsiSeriesRef.current = chart.addLineSeries({
            color: '#fbbf24', lineWidth: 2, title: 'RSI', priceScaleId: 'rsi-scale'
        });
        chart.priceScale('rsi-scale').applyOptions({
            scaleMargins: { top: 0.85, bottom: 0.02 },
            borderVisible: false,
            visible: false
        });

        const handleResize = () => {
            if (chartContainerRef.current && chartRef.current) {
                chartRef.current.applyOptions({
                    width: chartContainerRef.current.clientWidth,
                    height: chartContainerRef.current.clientHeight
                });
            }
        };
        window.addEventListener('resize', handleResize);

        return () => {
            window.removeEventListener('resize', handleResize);
            chart.remove();
        };
    }, []);

    // --- 2. UPDATE VISIBILITY (LIVE TOGGLE) ---
    useEffect(() => {
        if (!chartRef.current) return;
        chartRef.current.priceScale('volume-scale').applyOptions({ visible: showVolume });
        chartRef.current.priceScale('ao-scale').applyOptions({ visible: showAO });
        chartRef.current.priceScale('rsi-scale').applyOptions({ visible: showRSI });
    }, [showVolume, showAO, showRSI]);

    // --- 3. SYNC DATA & METADATA ---
    useEffect(() => {
        const candles = data?.history_candles || data?.candles;
        if (!candleSeriesRef.current || !data || !candles || candles.length === 0) return;

        const currentSymbol = metadata?.symbol || data?.symbol;
        const isNewSymbol = lastSymbolRef.current !== currentSymbol;
        lastSymbolRef.current = currentSymbol;

        const parseTime = (t: any) => typeof t === 'string' ? Math.floor(new Date(t).getTime() / 1000) : t;

        // Auto-Indicator Switching (Only on first load of a signal)
        if (isNewSymbol && metadata?.metadata?.indicator) {
            if (metadata.metadata.indicator === 'RSI') { setShowRSI(true); setShowAO(false); }
            else { setShowAO(true); setShowRSI(false); }
        }

        // Set Main Candle Data
        const formatted = candles.map((c: any) => ({
            time: parseTime(c.time),
            open: c.open, high: c.high, low: c.low, close: c.close
        })).sort((a:any, b:any) => a.time - b.time);

        candleSeriesRef.current.setData(formatted);

        // Set Indicators
        if (volumeSeriesRef.current) {
            volumeSeriesRef.current.setData(candles.map((c: any) => ({
                time: parseTime(c.time),
                value: c.volume,
                color: c.close >= c.open ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)'
            })));
        }

        if (aoSeriesRef.current) {
            aoSeriesRef.current.setData(candles.map((c: any) => ({
                time: parseTime(c.time),
                value: typeof c.ao === 'number' ? c.ao : 0
            })));
        }

        if (rsiSeriesRef.current) {
            rsiSeriesRef.current.setData(candles.map((c: any) => ({
                time: parseTime(c.time),
                value: typeof c.rsi === 'number' ? c.rsi : 50
            })));
        }

        // --- 4. DRAW OVERLAYS (PIVOTS, LINES) ---
        priceLinesRef.current.forEach(l => candleSeriesRef.current?.removePriceLine(l));
        priceLinesRef.current = [];
        extraSeriesRef.current.forEach(s => chartRef.current?.removeSeries(s));
        extraSeriesRef.current = [];

        const markers: SeriesMarker<any>[] = [];
        const scannerTotal = metadata?.metadata?.historical_bars_used || candles.length;
        const offset = scannerTotal - candles.length;
        const getChartIdx = (idx: number) => idx - offset;

        if (metadata) {
            // Price Target & SL Lines
            if (metadata.entry_price) {
                priceLinesRef.current.push(candleSeriesRef.current.createPriceLine({
                    price: metadata.entry_price, color: '#3b82f6', lineWidth: 2, lineStyle: LineStyle.Solid, title: 'ENTRY'
                }));
            }
            if (metadata.stop_loss) {
                priceLinesRef.current.push(candleSeriesRef.current.createPriceLine({
                    price: metadata.stop_loss, color: '#ef4444', lineWidth: 2, lineStyle: LineStyle.Dashed, title: 'SL'
                }));
            }
            const tp = metadata.take_profit || metadata.tp_short;
            if (tp) {
                priceLinesRef.current.push(candleSeriesRef.current.createPriceLine({
                    price: tp, color: '#10b981', lineWidth: 2, lineStyle: LineStyle.Dashed, title: 'TP'
                }));
            }

            // ZigZag Structural Path
            const pivots = metadata.metadata?.pivots;
            if (pivots && chartRef.current) {
                const points = Object.entries(pivots)
                    .map(([key, p]: [string, any]) => {
                        const cIdx = getChartIdx(p.idx);
                        if (candles[cIdx]) {
                            const t = parseTime(candles[cIdx].time);
                            markers.push({ time: t, position: 'belowBar', color: '#f59e0b', shape: 'arrowUp', text: key });
                            return { time: t, value: p.price };
                        }
                        return null;
                    })
                    .filter((p): p is {time: any, value: number} => p !== null);

                if (points.length > 1) {
                    const zigzag = chartRef.current.addLineSeries({
                        color: 'rgba(245, 158, 11, 0.3)', lineWidth: 2, lastValueVisible: false, priceLineVisible: false
                    });
                    zigzag.setData(points);
                    extraSeriesRef.current.push(zigzag);
                }
            }

            // Current Entry Candle Marker
            if (metadata.entry_candle_index !== undefined) {
                const t = parseTime(candles[getChartIdx(metadata.entry_candle_index)]?.time);
                if (t) markers.push({ time: t, position: 'aboveBar', color: '#3b82f6', shape: 'arrowDown', text: 'BUY' });
            }
        }

        // Backtest Trade Execution Markers
        if (data.trades) {
            data.trades.forEach((t: any) => {
                markers.push({ time: parseTime(t.entry_ts), position: 'belowBar', color: '#10b981', shape: 'arrowUp', text: 'B' });
                markers.push({ time: parseTime(t.exit_ts), position: 'aboveBar', color: t.pnl >= 0 ? '#10b981' : '#ef4444', shape: 'arrowDown', text: 'S' });
            });
        }

        if (markers.length > 0) {
            markers.sort((a, b) => a.time - b.time);
            candleSeriesRef.current.setMarkers(markers);
        }

        // Only auto-fit once per symbol to prevent annoying jumping during live updates
        if (isNewSymbol) {
            chartRef.current.timeScale().fitContent();
        }

    }, [data, metadata]);

    return (
        <div className="w-full h-full relative group">
            {interactive && (
                <div className="absolute top-4 right-6 z-20 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <div className="flex bg-slate-900/90 backdrop-blur-md border border-slate-700 rounded-xl p-1 shadow-2xl">
                        <button onClick={() => setShowVolume(!showVolume)} className={`p-2 rounded-lg transition-all ${showVolume ? 'bg-blue-600 text-white' : 'text-slate-400 hover:bg-slate-800'}`} title="Volume"><BarChart2 className="w-4 h-4" /></button>
                        <button onClick={() => setShowAO(!showAO)} className={`p-2 rounded-lg transition-all ${showAO ? 'bg-cyan-600 text-white' : 'text-slate-400 hover:bg-slate-800'}`} title="AO"><Zap className="w-4 h-4" /></button>
                        <button onClick={() => setShowRSI(!showRSI)} className={`p-2 rounded-lg transition-all ${showRSI ? 'bg-amber-600 text-white' : 'text-slate-400 hover:bg-slate-800'}`} title="RSI"><Eye className="w-4 h-4" /></button>
                    </div>
                </div>
            )}
            <div ref={chartContainerRef} className="w-full h-full" />
            <div className="absolute top-4 left-6 pointer-events-none z-10 flex gap-3 bg-slate-950/40 backdrop-blur-sm px-3 py-1.5 rounded-lg border border-white/5">
                <div className="flex items-center gap-1.5"><div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" /><span className="text-[10px] font-black text-slate-300 uppercase tracking-tighter">IDX REALTIME</span></div>
            </div>
        </div>
    );
};
