import React, { useEffect, useRef } from 'react';
import { createChart, ColorType, LineStyle, CandlestickData, LineData, IChartApi, ISeriesApi } from 'lightweight-charts';

interface PatternChartProps {
    data: any[];
    metadata?: any; // For Scanner (Single Signal)
    trades?: any[];  // For Backtest (Multiple Trades)
    colors?: {
        backgroundColor?: string;
        textColor?: string;
    };
}

export const PatternChart: React.FC<PatternChartProps> = (props) => {
    const {
        data,
        metadata,
        trades,
        colors: {
            backgroundColor = '#0f172a',
            textColor = '#94a3b8',
        } = {},
    } = props;

    const chartContainerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<IChartApi | null>(null);
    const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

    useEffect(() => {
        if (!chartContainerRef.current) return;

        const container = chartContainerRef.current;
        container.innerHTML = '';

        const chart = createChart(container, {
            layout: {
                background: { type: ColorType.Solid, color: backgroundColor },
                textColor,
            },
            grid: {
                vertLines: { color: 'rgba(30, 41, 59, 0.05)' },
                horzLines: { color: 'rgba(30, 41, 59, 0.05)' },
            },
            width: container.clientWidth,
            height: 500,
            timeScale: {
                timeVisible: true,
                secondsVisible: false,
                borderColor: '#1e293b',
            },
            rightPriceScale: {
                borderColor: '#1e293b',
            }
        });

        chartRef.current = chart;

        const candlestickSeries = chart.addCandlestickSeries({
            upColor: '#10b981',
            downColor: '#ef4444',
            borderVisible: false,
            wickUpColor: '#10b981',
            wickDownColor: '#ef4444',
        });
        candleSeriesRef.current = candlestickSeries;

        const handleResize = () => {
            if (chartRef.current) {
                chartRef.current.applyOptions({ width: container.clientWidth });
            }
        };

        window.addEventListener('resize', handleResize);

        return () => {
            window.removeEventListener('resize', handleResize);
            if (chartRef.current) {
                chartRef.current.remove();
                chartRef.current = null;
            }
        };
    }, [backgroundColor, textColor]);

    useEffect(() => {
        if (!candleSeriesRef.current || !chartRef.current || !data || data.length === 0) return;

        // 1. Format and deduplicate candles
        const formattedData: CandlestickData[] = data.map(item => ({
            time: (new Date(item.time).getTime() / 1000) as any,
            open: Number(item.open),
            high: Number(item.high),
            low: Number(item.low),
            close: Number(item.close),
        })).sort((a, b) => (a.time as number) - (b.time as number));

        const uniqueData = formattedData.filter((val, idx, self) =>
            idx === 0 || val.time !== self[idx - 1].time
        );

        candleSeriesRef.current.setData(uniqueData);

        const markers: any[] = [];

        // 2. Mode SCANNER (Single Pattern)
        if (metadata && metadata.pivots) {
            Object.entries(metadata.pivots).forEach(([key, p]: [string, any]) => {
                const targetTime = formattedData[p.idx]?.time;
                if (targetTime) {
                    markers.push({
                        time: targetTime,
                        position: 'belowBar',
                        color: '#f59e0b',
                        shape: 'arrowUp',
                        text: key.toUpperCase().replace('_', ' '),
                    });
                }
            });

            // Entry/SL/TP Lines
            const levels = [
                { price: metadata.entry_price, color: '#3b82f6', label: 'ENTRY' },
                { price: metadata.stop_loss, color: '#ef4444', label: 'SL' },
                { price: metadata.take_profit, color: '#10b981', label: 'TP' },
            ];

            levels.forEach(lvl => {
                if (lvl.price && candleSeriesRef.current) {
                    candleSeriesRef.current.createPriceLine({
                        price: Number(lvl.price),
                        color: lvl.color,
                        lineWidth: 2,
                        lineStyle: LineStyle.Dotted,
                        axisLabelVisible: true,
                        title: lvl.label,
                    });
                }
            });
        }

        // 3. Mode BACKTEST (Multiple Trades)
        if (trades && trades.length > 0) {
            trades.forEach(trade => {
                // Entry Marker
                markers.push({
                    time: new Date(trade.entry_ts).getTime() / 1000,
                    position: 'belowBar',
                    color: '#3b82f6',
                    shape: 'arrowUp',
                    text: 'BUY',
                });
                // Exit Marker
                markers.push({
                    time: new Date(trade.exit_ts).getTime() / 1000,
                    position: 'aboveBar',
                    color: trade.pnl >= 0 ? '#10b981' : '#ef4444',
                    shape: 'arrowDown',
                    text: trade.reason,
                });
            });
        }

        if (markers.length > 0) {
            candleSeriesRef.current.setMarkers(markers.sort((a, b) => (a.time as number) - (b.time as number)));
        }

        chartRef.current.timeScale().fitContent();

    }, [data, metadata, trades]);

    return (
        <div className="w-full bg-slate-900 border border-slate-800 rounded-3xl overflow-hidden shadow-2xl relative min-h-[500px]">
            <div ref={chartContainerRef} className="w-full h-full" />
        </div>
    );
};
