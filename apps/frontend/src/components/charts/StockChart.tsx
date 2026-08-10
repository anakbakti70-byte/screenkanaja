import React, { useEffect, useRef } from 'react';

interface StockChartProps {
    symbol: string;
    market?: string;
    theme?: 'light' | 'dark';
}

declare global {
    interface Window {
        TradingView: any;
    }
}

export const StockChart: React.FC<StockChartProps> = ({ symbol, market = 'idx', theme = 'dark' }) => {
    const containerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const containerId = `tv-chart-${symbol.replace(/[^a-zA-Z0-9]/g, '-')}`;

        const loadScript = () => {
            return new Promise((resolve) => {
                if (window.TradingView) {
                    resolve(true);
                    return;
                }
                const script = document.createElement('script');
                script.src = 'https://s3.tradingview.com/tv.js';
                script.async = true;
                script.onload = () => resolve(true);
                document.head.appendChild(script);
            });
        };

        const initWidget = async () => {
            await loadScript();

            if (window.TradingView && containerRef.current) {
                containerRef.current.innerHTML = '';
                const innerDiv = document.createElement('div');
                innerDiv.id = containerId;
                innerDiv.style.height = '100%';
                innerDiv.style.width = '100%';
                containerRef.current.appendChild(innerDiv);

                const cleanSymbol = symbol.split('.')[0].toUpperCase();
                const tvSymbol = market.toLowerCase() === 'idx' ? `IDX:${cleanSymbol}` : cleanSymbol;

                new window.TradingView.widget({
                    "autosize": true,
                    "symbol": tvSymbol,
                    "interval": "D",
                    "timezone": "Asia/Jakarta",
                    "theme": theme,
                    "style": "1",
                    "locale": "id",
                    "toolbar_bg": theme === 'dark' ? "#1e293b" : "#f1f5f9",
                    "enable_publishing": false,
                    "hide_top_toolbar": false,
                    "hide_legend": false,
                    "save_image": false,
                    "container_id": containerId,
                    "backgroundColor": theme === 'dark' ? "#0f172a" : "#ffffff",
                    "gridColor": "rgba(30, 41, 59, 0.1)",
                    "studies": [
                        "RSI@tv-basicstudies",
                        "MACD@tv-basicstudies",
                        "AwesomeOscillator@tv-basicstudies"
                    ],
                });
            }
        };

        initWidget();

        return () => {
            if (containerRef.current) {
                containerRef.current.innerHTML = '';
            }
        };
    }, [symbol, market, theme]);

    return (
        <div ref={containerRef} className="w-full h-full bg-slate-900 rounded-3xl overflow-hidden border border-slate-800 shadow-2xl" style={{ minHeight: '500px' }} />
    );
};
