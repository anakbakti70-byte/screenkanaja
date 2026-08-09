import React, { useState } from 'react';
import Layout from '../components/Layout';
import { Play, Calendar, BarChart, PieChart, Activity, AlertCircle, CheckCircle2, TrendingUp, ArrowUpRight, ArrowDownRight } from 'lucide-react';

import axios from 'axios';
import { useAuth } from '../hooks/AuthContext';

const Backtest: React.FC = () => {
    const { token } = useAuth();
    const [isRunning, setIsRunning] = useState(false);
    const [symbol, setSymbol] = useState('BBCA.JK');
    const [timeframe, setTimeframe] = useState('1d');
    const [initialCapital, setInitialCapital] = useState(10000000);
    const [results, setResults] = useState<any>(null);

    const runSimulation = async () => {
        setIsRunning(true);
        try {
            const res = await axios.post('/api/backtest/run', {
                symbol,
                timeframe,
                initial_capital: initialCapital
            }, {
                headers: { Authorization: `Bearer ${token}` }
            });
            setResults(res.data);
        } catch (err) {
            console.error("Backtest failed", err);
            alert("Backtest failed. See console for details.");
        } finally {
            setIsRunning(false);
        }
    };

    const stats = results ? [
        { label: 'Total Trades', value: results.metrics.total_trades, icon: Activity, color: 'text-blue-500' },
        { label: 'Win Rate', value: results.metrics.win_rate, icon: CheckCircle2, color: 'text-emerald-500' },
        { label: 'Net Profit', value: `Rp ${results.metrics.total_profit.toLocaleString()}`, icon: TrendingUp, color: results.metrics.total_profit >= 0 ? 'text-emerald-500' : 'text-red-500' },
        { label: 'Final Capital', value: `Rp ${results.metrics.final_capital.toLocaleString()}`, icon: AlertCircle, color: 'text-blue-500' },
    ] : [
        { label: 'Total Trades', value: '-', icon: Activity, color: 'text-slate-500' },
        { label: 'Win Rate', value: '-', icon: CheckCircle2, color: 'text-slate-500' },
        { label: 'Net Profit', value: '-', icon: TrendingUp, color: 'text-slate-500' },
        { label: 'Final Capital', value: '-', icon: AlertCircle, color: 'text-slate-500' },
    ];

    return (
        <Layout>
            <div className="p-8 max-w-7xl mx-auto space-y-8">
                <header>
                    <h1 className="text-3xl font-bold text-white mb-2">Backtesting Engine</h1>
                    <p className="text-slate-400">Uji strategi trading Anda menggunakan data historis sebelum terjun ke pasar.</p>
                </header>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    {/* Settings Panel */}
                    <div className="lg:col-span-1 space-y-6">
                        <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl space-y-6">
                            <h2 className="text-lg font-bold text-white flex items-center gap-2">
                                <Activity className="w-5 h-5 text-blue-500" /> Parameters
                            </h2>

                            <div className="space-y-4">
                                <div>
                                    <label className="block text-sm font-medium text-slate-500 mb-2">Strategy</label>
                                    <select className="w-full bg-slate-950 border border-slate-800 text-slate-200 px-4 py-3 rounded-xl outline-none focus:ring-2 focus:ring-blue-500">
                                        <option>Combined Strategies (Default)</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-slate-500 mb-2">Stock Symbol</label>
                                    <input
                                        type="text"
                                        value={symbol}
                                        onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                                        placeholder="E.g. BBRI.JK"
                                        className="w-full bg-slate-950 border border-slate-800 text-slate-200 px-4 py-3 rounded-xl outline-none focus:ring-2 focus:ring-blue-500"
                                    />
                                </div>
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-sm font-medium text-slate-500 mb-2">Timeframe</label>
                                        <select
                                            value={timeframe}
                                            onChange={(e) => setTimeframe(e.target.value)}
                                            className="w-full bg-slate-950 border border-slate-800 text-sm text-slate-200 px-4 py-3 rounded-xl"
                                        >
                                            <option value="1d">1 Day</option>
                                            <option value="1h">1 Hour</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-slate-500 mb-2">Initial Capital</label>
                                        <input
                                            type="number"
                                            value={initialCapital}
                                            onChange={(e) => setInitialCapital(Number(e.target.value))}
                                            className="w-full bg-slate-950 border border-slate-800 text-sm text-slate-200 px-4 py-3 rounded-xl"
                                        />
                                    </div>
                                </div>
                            </div>

                            <button
                                onClick={runSimulation}
                                disabled={isRunning}
                                className="w-full flex items-center justify-center gap-2 py-4 bg-blue-600 hover:bg-blue-700 text-white rounded-2xl font-bold transition-all shadow-lg shadow-blue-500/25 disabled:opacity-50"
                            >
                                <Play className={`w-5 h-5 ${isRunning ? 'animate-spin' : ''}`} />
                                {isRunning ? 'Running Simulation...' : 'Start Backtest'}
                            </button>
                        </div>
                    </div>

                    {/* Results Display */}
                    <div className="lg:col-span-2 space-y-6">
                        {/* Stats Cards */}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            {stats.map((stat, i) => (
                                <div key={i} className="bg-slate-900 border border-slate-800 p-5 rounded-3xl shadow-sm">
                                    <div className={`p-2 w-fit rounded-lg bg-slate-950 border border-slate-800 mb-3 ${stat.color}`}>
                                        <stat.icon className="w-5 h-5" />
                                    </div>
                                    <div className="text-2xl font-bold text-white mb-1">{stat.value}</div>
                                    <div className="text-xs text-slate-500 font-medium">{stat.label}</div>
                                </div>
                            ))}
                        </div>

                        {/* Chart Placeholder */}
                        <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl min-h-[300px] flex flex-col">
                            <div className="flex items-center justify-between mb-8">
                                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                                    <BarChart className="w-5 h-5 text-blue-500" /> Equity Curve
                                </h2>
                                <div className="flex gap-2">
                                    <span className="flex items-center gap-1 text-xs text-emerald-500 font-bold bg-emerald-500/10 px-2 py-1 rounded-lg">
                                        <ArrowUpRight className="w-3 h-3" /> Growth
                                    </span>
                                </div>
                            </div>

                            <div className="flex-1 border-b border-l border-slate-800/50 relative flex items-end justify-between px-4 pb-2 h-48">
                                {/* Dynamic Equity Chart Simulation */}
                                {results && results.equity_curve && results.equity_curve.length > 0 ? (() => {
                                    const balances = results.equity_curve.map((p: any) => p.balance);
                                    const minBalance = Math.min(...balances);
                                    const maxBalance = Math.max(...balances);
                                    const range = maxBalance - minBalance || 1;

                                    // Sample up to 30 points to show a smooth curve without killing performance
                                    const step = Math.max(1, Math.floor(results.equity_curve.length / 30));

                                    return results.equity_curve.filter((_: any, i: number) => i % step === 0).map((point: any, i: number) => {
                                        const height = ((point.balance - minBalance) / range) * 100;
                                        return (
                                            <div
                                                key={i}
                                                className="w-[3%] bg-blue-600/30 border-t-2 border-blue-500 rounded-t-sm transition-all duration-500 hover:bg-blue-400 group relative"
                                                style={{ height: `${Math.max(5, height)}%` }}
                                            >
                                                {/* Tooltip */}
                                                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block z-50 bg-slate-800 text-white text-[9px] py-1 px-2 rounded whitespace-nowrap border border-slate-700 shadow-xl">
                                                    Rp {point.balance.toLocaleString()}
                                                </div>
                                            </div>
                                        );
                                    });
                                })() : (
                                    [40, 45, 42, 50, 55, 52, 60, 68, 65, 75, 82, 90].map((h, i) => (
                                        <div key={i} className="w-[6%] bg-slate-800/20 border-t-2 border-slate-700 rounded-t-sm" style={{ height: `${h}%` }}></div>
                                    ))
                                )}
                                <div className="absolute inset-0 flex items-center justify-center opacity-10 pointer-events-none">
                                    <TrendingUp className="w-40 h-40 text-blue-500" />
                                </div>
                            </div>
                            <div className="flex justify-between mt-4 px-2 text-[10px] font-bold text-slate-600">
                                <span>START</span><span>MID</span><span>END</span>
                            </div>
                        </div>

                        {/* Trade History Preview */}
                        <div className="bg-slate-900 border border-slate-800 rounded-3xl overflow-hidden shadow-xl">
                            <div className="p-5 border-b border-slate-800 flex items-center gap-2">
                                <PieChart className="w-5 h-5 text-blue-500" />
                                <h2 className="text-lg font-bold text-white">Recent Simulated Trades</h2>
                            </div>
                            <div className="overflow-x-auto">
                                <table className="w-full text-left text-sm">
                                    <thead className="bg-slate-950/50 text-slate-500">
                                        <tr>
                                            <th className="px-6 py-3">Date</th>
                                            <th className="px-6 py-3">Type</th>
                                            <th className="px-6 py-3">Price</th>
                                            <th className="px-6 py-3">Quantity</th>
                                            <th className="px-6 py-3 text-right">P&L</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-800">
                                        {!results ? (
                                            <tr>
                                                <td colSpan={5} className="px-6 py-8 text-center text-slate-500 italic">No simulation results yet.</td>
                                            </tr>
                                        ) : results.trades.length === 0 ? (
                                            <tr>
                                                <td colSpan={5} className="px-6 py-8 text-center text-slate-500">No trades executed during this period.</td>
                                            </tr>
                                        ) : (
                                            results.trades.map((trade: any, i: number) => (
                                                <tr key={i} className="hover:bg-slate-800/20">
                                                    <td className="px-6 py-3 text-slate-400">{new Date(trade.date).toLocaleDateString()}</td>
                                                    <td className="px-6 py-3">
                                                        <span className={`font-bold ${trade.type === 'BUY' ? 'text-blue-500' : 'text-emerald-500'}`}>
                                                            {trade.type}
                                                        </span>
                                                    </td>
                                                    <td className="px-6 py-3 text-slate-300">{trade.price.toLocaleString()}</td>
                                                    <td className="px-6 py-3 text-slate-300">{trade.qty}</td>
                                                    <td className={`px-6 py-3 text-right font-bold ${trade.pnl >= 0 ? 'text-emerald-500' : trade.pnl < 0 ? 'text-red-500' : 'text-slate-500'}`}>
                                                        {trade.pnl ? `${trade.pnl >= 0 ? '+' : ''}${trade.pnl.toLocaleString()}` : '-'}
                                                    </td>
                                                </tr>
                                            ))
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </Layout>
    );
};

export default Backtest;
