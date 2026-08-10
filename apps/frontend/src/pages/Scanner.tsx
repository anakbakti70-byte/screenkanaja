import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { Search, Filter, Play, Download, ChevronRight, TrendingUp, TrendingDown, Info, AlertCircle, Zap, Calendar, Loader2, MessageSquare, Target, ShieldAlert } from 'lucide-react';
import axios from 'axios';
import { useAuth } from '../hooks/AuthContext';
import { useScannerAutoRefresh } from '../hooks/useScannerAutoRefresh';
import { PatternChart } from '../components/charts/PatternChart';
import { StockChart } from '../components/charts/StockChart';

interface ScanResult {
    symbol: string;
    timeframe: string;
    method: string;
    status: string;
    entry_price: number | null;
    stop_loss: number | null;
    tp_short: number | null;
    tp_far: number | null;
    risk_reward: number | null;
    score: number;
    metadata: any;
    created_at: string;
}

const Scanner: React.FC = () => {
    const { token } = useAuth();
    const [market, setMarket] = useState('idx');
    const [timeframe, setTimeframe] = useState('1d');
    const [search, setSearch] = useState('');
    const [selectedResult, setSelectedResult] = useState<ScanResult | null>(null);
    const [candles, setCandles] = useState<any[]>([]);
    const [candlesLoading, setCandlesLoading] = useState(false);

    const { results, loading } = useScannerAutoRefresh(token, market, timeframe);
    const [topSetups, setTopSetups] = useState<ScanResult[]>([]);

    useEffect(() => {
        const fetchSidebarData = async () => {
            if (!token) return;
            try {
                const topRes = await axios.get('/api/scanner/results', {
                    params: { market, timeframe, limit: 5, sort_by: 'score', latest_only: true },
                    headers: { Authorization: `Bearer ${token}` }
                });
                setTopSetups(topRes.data);
            } catch (err) {
                console.error(err);
            }
        };
        fetchSidebarData();
    }, [token, market, timeframe, results]);

    useEffect(() => {
        if (selectedResult) {
            const fetchCandles = async () => {
                setCandlesLoading(true);
                try {
                    const res = await axios.get(`/api/stocks/${selectedResult.symbol}/candles`, {
                        params: { timeframe },
                        headers: { Authorization: `Bearer ${token}` }
                    });
                    setCandles(res.data);
                } catch (err) {
                    console.error("Failed to fetch candles", err);
                } finally {
                    setCandlesLoading(false);
                }
            };
            fetchCandles();

            // Real-time chart polling every 30s
            const interval = setInterval(fetchCandles, 30000);
            return () => clearInterval(interval);
        }
    }, [selectedResult, timeframe, token]);

    const filteredResults = results.filter(r => {
        const matchesSearch = r.symbol.toLowerCase().includes(search.toLowerCase()) ||
                              r.method.toLowerCase().includes(search.toLowerCase());
        return matchesSearch;
    });

    return (
        <Layout>
            <div className="p-8 max-w-7xl mx-auto space-y-8">
                <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                        <h1 className="text-3xl font-bold text-white mb-2 tracking-tight">Market Scanner</h1>
                        <p className="text-slate-400 text-sm">Real-time Divergence Detection based on final.md strategy.</p>
                    </div>
                    <div className="flex flex-col md:flex-row gap-3">
                        <div className="flex items-center gap-2 px-4 py-2 bg-blue-600/10 text-blue-500 rounded-xl border border-blue-500/20 text-xs font-bold shadow-lg">
                            <ShieldAlert className="w-4 h-4" />
                            Rule Accuracy: {">"}95%
                        </div>
                        <div className="flex items-center gap-2 px-4 py-2 bg-emerald-600/10 text-emerald-500 rounded-xl border border-emerald-500/20 text-xs font-bold">
                            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
                            Live Analysis Active
                        </div>
                    </div>
                </header>

                {/* Analysis Area */}
                {selectedResult && (
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 animate-in fade-in slide-in-from-top-4 duration-500">
                        <div className="lg:col-span-2 space-y-6">
                            <div className="bg-slate-900 border border-slate-800 rounded-3xl overflow-hidden shadow-2xl relative min-h-[500px]">
                                {candlesLoading ? (
                                    <div className="absolute inset-0 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm z-20">
                                        <Loader2 className="animate-spin text-blue-500 w-12 h-12" />
                                    </div>
                                ) : (
                                    <PatternChart data={candles} metadata={selectedResult} />
                                )}
                                <button
                                    onClick={() => setSelectedResult(null)}
                                    className="absolute top-4 right-4 bg-slate-950/80 text-white p-2 rounded-full hover:bg-red-500 transition-all z-30 border border-white/10"
                                >
                                    <AlertCircle className="w-5 h-5 rotate-45" />
                                </button>
                            </div>
                        </div>

                        <div className="lg:col-span-1 space-y-6">
                            <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-2xl relative overflow-hidden">
                                <h2 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
                                    <Target className="w-5 h-5 text-blue-500" /> Plan Analysis
                                </h2>

                                <div className="space-y-4">
                                    <div className="flex justify-between items-center p-3 bg-slate-950/50 rounded-xl border border-slate-800">
                                        <span className="text-xs text-slate-500 font-bold uppercase">Symbol</span>
                                        <span className="text-lg font-bold text-white">{selectedResult.symbol}</span>
                                    </div>
                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="p-3 bg-emerald-500/5 rounded-xl border border-emerald-500/20">
                                            <div className="text-[10px] text-emerald-500/70 font-bold uppercase mb-1">Entry</div>
                                            <div className="text-lg font-bold text-emerald-500">Rp {selectedResult.entry_price?.toLocaleString()}</div>
                                        </div>
                                        <div className="p-3 bg-red-500/5 rounded-xl border border-red-500/20">
                                            <div className="text-[10px] text-red-500/70 font-bold uppercase mb-1">Stop Loss</div>
                                            <div className="text-lg font-bold text-red-500">Rp {selectedResult.stop_loss?.toLocaleString()}</div>
                                        </div>
                                    </div>
                                    <div className="p-3 bg-blue-500/5 rounded-xl border border-blue-500/20">
                                        <div className="text-[10px] text-blue-400/70 font-bold uppercase mb-1">Target Profit (Fib 0.6)</div>
                                        <div className="text-lg font-bold text-blue-400">Rp {selectedResult.tp_short?.toLocaleString()}</div>
                                    </div>
                                </div>
                            </div>

                            {selectedResult.metadata?.explanation && (
                                <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-2xl">
                                    <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                                        <MessageSquare className="w-5 h-5 text-purple-500" /> Analisis AI (Llama 70B)
                                    </h2>
                                    <div className="text-xs text-slate-300 leading-relaxed max-h-[250px] overflow-y-auto scrollbar-hide">
                                        {selectedResult.metadata.explanation}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 bg-slate-900/50 p-6 rounded-3xl border border-slate-800">
                    <div className="space-y-2">
                        <label className="text-xs font-bold text-slate-500 ml-1 uppercase">Market</label>
                        <select value={market} onChange={(e) => setMarket(e.target.value)} className="w-full bg-slate-950 border border-slate-800 text-slate-200 px-4 py-3 rounded-xl outline-none focus:ring-2 focus:ring-blue-500">
                            <option value="idx">IDX (Indonesia)</option>
                            <option value="us">US Market</option>
                        </select>
                    </div>
                    <div className="space-y-2">
                        <label className="text-xs font-bold text-slate-500 ml-1 uppercase">Timeframe</label>
                        <select value={timeframe} onChange={(e) => setTimeframe(e.target.value)} className="w-full bg-slate-950 border border-slate-800 text-slate-200 px-4 py-3 rounded-xl outline-none focus:ring-2 focus:ring-blue-500">
                            <option value="1d">1 Day</option>
                            <option value="1h">1 Hour</option>
                            <option value="15m">15 Minutes</option>
                        </select>
                    </div>
                    <div className="space-y-2">
                        <label className="text-xs font-bold text-slate-500 ml-1 uppercase">Search</label>
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                            <input type="text" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Symbol or Strategy..." className="w-full bg-slate-950 border border-slate-800 text-slate-200 pl-10 pr-4 py-3 rounded-xl outline-none" />
                        </div>
                    </div>
                </div>

                <div className="flex flex-col lg:flex-row gap-8 items-start">
                    <aside className="w-full lg:w-80 space-y-6">
                        <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl">
                            <h2 className="font-bold text-white uppercase tracking-wider text-xs mb-6 flex items-center gap-2">
                                <Zap className="w-4 h-4 text-amber-500" /> Top Potential
                            </h2>
                            <div className="space-y-3">
                                {topSetups.map((setup, i) => (
                                    <div key={i} className="flex items-center justify-between p-3 bg-slate-950/50 hover:bg-slate-800 transition-all rounded-2xl cursor-pointer border border-slate-800/50" onClick={() => setSelectedResult(setup)}>
                                        <div className="flex flex-col">
                                            <span className="text-sm font-bold text-white">{setup.symbol}</span>
                                            <span className="text-[9px] text-slate-500 uppercase">{setup.method?.split(' ')[0]}</span>
                                        </div>
                                        <span className="text-xs font-bold text-emerald-500 bg-emerald-500/10 px-2 py-1 rounded-lg">{setup.score?.toFixed(0)}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </aside>

                    <div className="flex-1 w-full">
                        <div className="bg-slate-900 border border-slate-800 rounded-3xl overflow-hidden shadow-xl">
                            <div className="overflow-x-auto">
                                <table className="w-full text-left">
                                    <thead className="bg-slate-950/50 text-slate-500 text-xs uppercase tracking-widest font-black">
                                        <tr>
                                            <th className="px-6 py-5">Emiten</th>
                                            <th className="px-6 py-5">Strategi</th>
                                            <th className="px-6 py-5">Price</th>
                                            <th className="px-6 py-5">Status</th>
                                            <th className="px-6 py-5 text-right">Detected</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-800">
                                        {loading ? (
                                            <tr><td colSpan={5} className="py-24 text-center"><Loader2 className="animate-spin inline-block text-blue-500 w-8 h-8" /></td></tr>
                                        ) : filteredResults.length === 0 ? (
                                            <tr><td colSpan={5} className="py-24 text-center text-slate-500 italic">No signals found.</td></tr>
                                        ) : filteredResults.map((res, i) => (
                                            <tr
                                                key={i}
                                                className={`hover:bg-slate-800/40 cursor-pointer transition-all ${selectedResult?.symbol === res.symbol && selectedResult?.method === res.method ? 'bg-blue-600/10 border-l-4 border-l-blue-500' : ''}`}
                                                onClick={() => setSelectedResult(res)}
                                            >
                                                <td className="px-6 py-5">
                                                    <div className="font-black text-white text-lg">{res.symbol}</div>
                                                </td>
                                                <td className="px-6 py-5">
                                                    <div className="text-sm font-bold text-blue-400">{res.method}</div>
                                                </td>
                                                <td className="px-6 py-5">
                                                    <div className="text-sm font-bold text-slate-200">Rp {res.entry_price?.toLocaleString()}</div>
                                                    <div className="text-[10px] text-slate-500">RR: {res.risk_reward?.toFixed(1)}</div>
                                                </td>
                                                <td className="px-6 py-5">
                                                    <span className={`px-3 py-1.5 rounded-full text-[10px] font-black tracking-widest ${res.status === 'READY' ? 'bg-emerald-500/10 text-emerald-500' : 'bg-blue-500/10 text-blue-500'}`}>
                                                        {res.status}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-5 text-right">
                                                    <div className="text-xs font-bold text-slate-400">{new Date(res.created_at).toLocaleTimeString()}</div>
                                                </td>
                                            </tr>
                                        ))}
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

export default Scanner;
