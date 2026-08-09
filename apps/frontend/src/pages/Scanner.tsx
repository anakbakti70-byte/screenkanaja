import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { Search, Filter, Play, Download, ChevronRight, TrendingUp, TrendingDown, Info, AlertCircle, Zap, Calendar } from 'lucide-react';
import axios from 'axios';
import { useAuth } from '../hooks/AuthContext';

interface ScanResult {
    symbol: str;
    timeframe: str;
    strategy_name: str;
    status: str;
    entry_price: number | null;
    stop_loss: number | null;
    take_profit: number | null;
    risk_reward: number | null;
    score: number;
    metadata: any;
    timestamp: string;
}

const Scanner: React.FC = () => {
    const { token } = useAuth();
    const [isScanning, setIsScanning] = useState(false);
    const [results, setResults] = useState<ScanResult[]>([]);
    const [market, setMarket] = useState('idx');
    const [timeframe, setTimeframe] = useState('1d');
    const [indicator, setIndicator] = useState('all');
    const [search, setSearch] = useState('');
    const [loading, setLoading] = useState(true);
    const [topSetups, setTopSetups] = useState<ScanResult[]>([]);
    const [recentIpos, setRecentIpos] = useState<any[]>([]);
    const [allStocks, setAllStocks] = useState<any[]>([]);
    const [stockSearch, setStockSearch] = useState('');

    const fetchResults = async () => {
        try {
            setLoading(true);
            const [resultsRes, topRes, ipoRes, allRes] = await Promise.all([
                axios.get('/api/scanner/results', {
                    params: { market, timeframe, latest_only: true },
                    headers: { Authorization: `Bearer ${token}` }
                }),
                axios.get('/api/scanner/results', {
                    params: { market, timeframe, limit: 5, sort_by: 'score', latest_only: true },
                    headers: { Authorization: `Bearer ${token}` }
                }),
                axios.get('/api/stocks/ipo', {
                    headers: { Authorization: `Bearer ${token}` }
                }),
                axios.get('/api/stocks/', {
                    headers: { Authorization: `Bearer ${token}` }
                })
            ]);

            setResults(resultsRes.data);
            setTopSetups(topRes.data);
            setRecentIpos(ipoRes.data);
            setAllStocks(allRes.data);
        } catch (err) {
            console.error("Failed to fetch scanner data", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchResults();

        // Auto-refresh data every 60 seconds
        const interval = setInterval(fetchResults, 60000);
        return () => clearInterval(interval);
    }, [market, timeframe]);

    const filteredResults = results.filter(r => {
        const matchesSearch = r.symbol.toLowerCase().includes(search.toLowerCase()) ||
                              r.strategy_name.toLowerCase().includes(search.toLowerCase());

        if (!matchesSearch) return false;

        if (indicator === 'rsi_macd') {
            const inds = r.metadata?.indicators || [];
            return inds.includes('RSI') && inds.includes('MACD');
        }
        if (indicator === 'rsi') {
            return (r.metadata?.indicators || []).includes('RSI');
        }
        if (indicator === 'macd') {
            return (r.metadata?.indicators || []).includes('MACD');
        }

        return true;
    });

    return (
        <Layout>
            <div className="p-8 max-w-7xl mx-auto space-y-8">
                <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                        <h1 className="text-3xl font-bold text-white mb-2">Market Scanner</h1>
                        <p className="text-slate-400">Temukan peluang trading berdasarkan parameter teknikal Anda.</p>
                    </div>
                    <div className="flex gap-3">
                        <button className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl border border-slate-700 transition-all">
                            <Download className="w-4 h-4" /> Export
                        </button>
                        <div className="flex items-center gap-2 px-4 py-2 bg-blue-600/10 text-blue-500 rounded-xl border border-blue-500/20 text-xs font-bold animate-pulse">
                            <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                            Auto-Scanning Active
                        </div>
                    </div>
                </header>

                {/* Filters Grid */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-6 bg-slate-900/50 p-6 rounded-3xl border border-slate-800">
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-slate-500 ml-1">Market</label>
                        <select
                            value={market}
                            onChange={(e) => setMarket(e.target.value)}
                            className="w-full bg-slate-950 border border-slate-800 text-slate-200 px-4 py-3 rounded-xl outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                        >
                            <option value="idx">IDX (Indonesia)</option>
                            <option value="us">US Market (Nasdaq/SPY)</option>
                        </select>
                    </div>
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-slate-500 ml-1">Timeframe</label>
                        <select
                            value={timeframe}
                            onChange={(e) => setTimeframe(e.target.value)}
                            className="w-full bg-slate-950 border border-slate-800 text-slate-200 px-4 py-3 rounded-xl outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                        >
                            <option value="1d">1 Day</option>
                            <option value="4h">4 Hours</option>
                            <option value="1h">1 Hour</option>
                            <option value="15m">15 Minutes</option>
                        </select>
                    </div>
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-slate-500 ml-1">Indicator</label>
                        <select
                            value={indicator}
                            onChange={(e) => setIndicator(e.target.value)}
                            className="w-full bg-slate-950 border border-slate-800 text-slate-200 px-4 py-3 rounded-xl outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                        >
                            <option value="all">Multi-Indicator (Default)</option>
                            <option value="rsi_macd">RSI + MACD (Combo)</option>
                            <option value="rsi">RSI Only</option>
                            <option value="macd">MACD Only</option>
                        </select>
                    </div>
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-slate-500 ml-1">Min Score</label>
                        <select className="w-full bg-slate-950 border border-slate-800 text-slate-200 px-4 py-3 rounded-xl outline-none focus:ring-2 focus:ring-blue-500 transition-all">
                            <option>Any Score</option>
                            <option>Score {'>'} 50</option>
    <option>Score {'>'} 75</option>
                        </select>
                    </div>
                </div>

                <div className="flex flex-col lg:flex-row gap-8 items-start">
                    {/* Sidebar: Market Overview */}
                    <aside className="w-full lg:w-80 space-y-6">
                        {/* 1. Recent IPOs (Realtime from IDX) */}
                        <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl">
                            <div className="flex items-center gap-2 mb-6">
                                <TrendingUp className="w-5 h-5 text-emerald-500" />
                                <h2 className="font-bold text-white uppercase tracking-wider text-xs">Recent IPOs (IDX)</h2>
                            </div>
                            <div className="space-y-4">
                                {recentIpos.length === 0 ? (
                                    <p className="text-xs text-slate-500 italic">No IPO data. Run sync_universe.</p>
                                ) : (
                                    recentIpos.map((ipo, i) => (
                                        <div key={i} className="flex justify-between items-center p-3 bg-slate-950/50 rounded-2xl border border-slate-800/50 hover:border-emerald-500/30 transition-all">
                                            <div>
                                                <div className="text-xs font-bold text-white">{ipo.symbol}</div>
                                                <div className="text-[9px] text-slate-500 uppercase">{new Date(ipo.listing_date).toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' })}</div>
                                            </div>
                                            <div className="bg-emerald-500/10 text-emerald-500 text-[8px] font-bold px-1.5 py-0.5 rounded uppercase">New</div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>

                        {/* 2. Top Ranked Saham */}
                        <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl">
                            <div className="flex items-center gap-2 mb-6">
                                <Zap className="w-5 h-5 text-amber-500" />
                                <h2 className="font-bold text-white uppercase tracking-wider text-xs">Top Rated Setups</h2>
                            </div>
                            <div className="space-y-3">
                                {topSetups.length === 0 ? (
                                    <p className="text-xs text-slate-500 italic">No setups found.</p>
                                ) : (
                                    topSetups.map((setup, i) => (
                                        <div key={i} className="flex items-center justify-between p-2 hover:bg-slate-800/30 rounded-xl transition-all">
                                            <div className="flex items-center gap-3">
                                                <div className="w-7 h-7 rounded-lg bg-blue-600/20 flex items-center justify-center font-bold text-blue-500 text-[10px]">
                                                    {setup.symbol.charAt(0)}
                                                </div>
                                                <div className="text-xs font-bold text-white">{setup.symbol}</div>
                                            </div>
                                            <div className="text-xs font-bold text-emerald-500">{setup.score.toFixed(0)}%</div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>

                        {/* 3. Daftar Semua Saham (Searchable) */}
                        <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl max-h-[500px] flex flex-col">
                            <div className="flex items-center gap-2 mb-4">
                                <Filter className="w-5 h-5 text-blue-500" />
                                <h2 className="font-bold text-white uppercase tracking-wider text-xs">Daftar Saham</h2>
                            </div>
                            <div className="relative mb-4">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
                                <input
                                    type="text"
                                    value={stockSearch}
                                    onChange={(e) => setStockSearch(e.target.value)}
                                    placeholder="Cari kode saham..."
                                    className="w-full bg-slate-950 border border-slate-800 text-[10px] text-slate-300 pl-9 pr-3 py-2 rounded-xl outline-none focus:ring-1 focus:ring-blue-500"
                                />
                            </div>
                            <div className="flex-1 overflow-y-auto space-y-2 pr-2 custom-scrollbar">
                                {allStocks
                                    .filter(s => s.symbol.toLowerCase().includes(stockSearch.toLowerCase()))
                                    .slice(0, 50) // Show first 50
                                    .map((stock, i) => (
                                        <div key={i} className="flex items-center justify-between p-2 rounded-lg hover:bg-slate-800/50 cursor-pointer group">
                                            <span className="text-xs font-medium text-slate-400 group-hover:text-white">{stock.symbol}</span>
                                            <span className="text-[9px] text-slate-600 truncate max-w-[120px]">{stock.company_name}</span>
                                        </div>
                                    ))
                                }
                            </div>
                        </div>
                    </aside>

                    {/* Main Content Area */}
                    <div className="flex-1 w-full space-y-8">
                        <div className="bg-slate-900 border border-slate-800 rounded-3xl overflow-hidden shadow-xl">
                            <div className="p-6 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                                <div className="flex items-center gap-3">
                                    <h2 className="text-lg font-bold text-white">Live Scan Results</h2>
                                    <span className="bg-blue-600/20 text-blue-500 text-xs font-bold px-2.5 py-1 rounded-lg">
                                        {filteredResults.length} Setups
                                    </span>
                                </div>
                                <div className="relative">
                                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                                    <input
                                        type="text"
                                        value={search}
                                        onChange={(e) => setSearch(e.target.value)}
                                        placeholder="Search setup results..."
                                        className="bg-slate-950 border border-slate-800 text-sm text-slate-300 pl-10 pr-4 py-2 rounded-xl outline-none focus:ring-2 focus:ring-blue-500"
                                    />
                                </div>
                            </div>

                            <div className="overflow-x-auto">
                                <table className="w-full text-left">
                                    <thead>
                                        <tr className="text-slate-500 text-xs uppercase tracking-wider bg-slate-950/50">
                                            <th className="px-6 py-4 font-bold">Symbol</th>
                                            <th className="px-6 py-4 font-bold">Strategy</th>
                                            <th className="px-6 py-4 font-bold">Price</th>
                                            <th className="px-6 py-4 font-bold">R:R</th>
                                            <th className="px-6 py-4 font-bold">Score</th>
                                            <th className="px-6 py-4 font-bold">Status</th>
                                            <th className="px-6 py-4 font-bold text-right">Time</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-800">
                                        {loading ? (
                                            <tr>
                                                <td colSpan={7} className="px-6 py-12 text-center text-slate-500">
                                                    <div className="flex flex-col items-center gap-3">
                                                        <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                                                        <p className="font-medium">Loading results...</p>
                                                    </div>
                                                </td>
                                            </tr>
                                        ) : filteredResults.length === 0 ? (
                                            <tr>
                                                <td colSpan={7} className="px-6 py-12 text-center text-slate-500 italic">
                                                    Belum ada hasil untuk filter ini. Klik "Run Scanner" untuk mencari peluang.
                                                </td>
                                            </tr>
                                        ) : (
                                            filteredResults.map((res, i) => (
                                                <tr key={i} className="hover:bg-slate-800/30 transition-colors group">
                                                    <td className="px-6 py-4">
                                                        <div className="flex items-center gap-3">
                                                            <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center text-xs font-bold text-slate-300">
                                                                {res.symbol.charAt(0)}
                                                            </div>
                                                            <span className="font-bold text-white">{res.symbol}</span>
                                                        </div>
                                                    </td>
                                                    <td className="px-6 py-4">
                                                        <span className="text-slate-300 font-medium">{res.strategy_name.replace('_', ' ')}</span>
                                                    </td>
                                                    <td className="px-6 py-4 font-medium text-slate-400">
                                                        {res.entry_price ? res.entry_price.toLocaleString() : '-'}
                                                    </td>
                                                    <td className="px-6 py-4">
                                                        <span className={`font-bold ${res.risk_reward && res.risk_reward > 2 ? 'text-emerald-500' : 'text-slate-400'}`}>
                                                            {res.risk_reward ? `1:${res.risk_reward.toFixed(1)}` : '-'}
                                                        </span>
                                                    </td>
                                                    <td className="px-6 py-4">
                                                        <div className="flex items-center gap-2">
                                                            <div className="w-full max-w-[60px] bg-slate-800 h-1.5 rounded-full overflow-hidden">
                                                                <div
                                                                    className={`h-full rounded-full ${res.score > 70 ? 'bg-emerald-500' : res.score > 40 ? 'bg-amber-500' : 'bg-red-500'}`}
                                                                    style={{ width: `${res.score}%` }}
                                                                ></div>
                                                            </div>
                                                            <span className="text-xs font-bold text-slate-400">{res.score.toFixed(0)}</span>
                                                        </div>
                                                    </td>
                                                    <td className="px-6 py-4">
                                                        <span className={`px-2.5 py-1 rounded-lg text-[10px] font-bold uppercase ${
                                                            res.status === 'READY' ? 'bg-emerald-500/10 text-emerald-500' :
                                                            res.status === 'WAIT_CONFIRMATION' ? 'bg-blue-500/10 text-blue-500' : 'bg-slate-800 text-slate-400'
                                                        }`}>
                                                            {res.status.replace('_', ' ')}
                                                        </span>
                                                    </td>
                                                    <td className="px-6 py-4 text-right text-xs text-slate-500 font-medium">
                                                        {new Date(res.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                                    </td>
                                                </tr>
                                            ))
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        <div className="bg-blue-600/10 border border-blue-500/30 p-4 rounded-2xl flex gap-3 items-start">
                            <Info className="w-5 h-5 text-blue-500 mt-0.5" />
                            <p className="text-sm text-blue-300 leading-relaxed">
                                <strong>Tips:</strong> Gunakan "Run Scanner" untuk memperbarui data. Strategi <strong>Correction</strong> akan aktif otomatis jika ada Bullish Divergence yang sudah mencapai target.
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </Layout>
    );
};

export default Scanner;
