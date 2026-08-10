import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { Play, Activity, CheckCircle2, TrendingUp, BarChart, Wallet, Plus, Loader2, Search, Target, ShieldAlert, ArrowUpRight, X, Zap } from 'lucide-react';
import axios from 'axios';
import { useAuth } from '../hooks/AuthContext';
import { PatternChart } from '../components/charts/PatternChart';

const Backtest: React.FC = () => {
    const { token, user, updateUser } = useAuth();
    const [isRunning, setIsRunning] = useState(false);
    const [symbol, setSymbol] = useState('GOTO');
    const [availableSymbols, setAvailableSymbols] = useState<any[]>([]);
    const [timeframe, setTimeframe] = useState('1d');
    const [initialCapital, setInitialCapital] = useState(100000000);
    const [riskPerTrade, setRiskPerTrade] = useState(10);
    const [results, setResults] = useState<any>(null);
    const [balance, setBalance] = useState(0);
    const [searchQuery, setSearchQuery] = useState('');
    const [showDropdown, setShowDropdown] = useState(false);
    const [suggestedStocks, setSuggestedStocks] = useState<any[]>([]);
    const [topUniverse, setTopUniverse] = useState<any[]>([]);

    useEffect(() => {
        if (user) setBalance(user.balance);
        fetchSuggestions();
        fetchTopUniverse();
    }, [user]);

    const fetchTopUniverse = async () => {
        try {
            // Get some top liquid stocks from master as default picks
            const res = await axios.get('/api/backtest/symbols', {
                headers: { Authorization: `Bearer ${token}` }
            });
            setTopUniverse(res.data.slice(0, 8)); // Top 8 for quick access
        } catch (err) {
            console.error("Failed to fetch universe", err);
        }
    };

    const fetchSuggestions = async () => {
        try {
            // Get stocks that have active signals recently as suggestions
            const res = await axios.get('/api/scanner/results', {
                params: { limit: 12, latest_only: true },
                headers: { Authorization: `Bearer ${token}` }
            });
            setSuggestedStocks(res.data);
        } catch (err) {
            console.error("Failed to fetch suggestions", err);
        }
    };

    useEffect(() => {
        const delayDebounceFn = setTimeout(() => {
            if (searchQuery) fetchSymbols(searchQuery);
            else if (showDropdown) fetchSymbols('');
        }, 300);
        return () => clearTimeout(delayDebounceFn);
    }, [searchQuery, token, showDropdown]);

    const fetchSymbols = async (query: string) => {
        try {
            const res = await axios.get('/api/backtest/symbols', {
                params: { query },
                headers: { Authorization: `Bearer ${token}` }
            });
            setAvailableSymbols(res.data);
        } catch (err) {
            console.error("Failed to fetch symbols", err);
        }
    };

    const runSimulation = async () => {
        setIsRunning(true);
        setResults(null);
        try {
            const res = await axios.post('/api/backtest/run', {
                symbol,
                timeframe,
                initial_capital: initialCapital,
                risk_per_trade: riskPerTrade
            }, {
                headers: { Authorization: `Bearer ${token}` }
            });
            setResults(res.data);
            // Scroll to results
            setTimeout(() => {
                window.scrollTo({ top: 500, behavior: 'smooth' });
            }, 100);
        } catch (err) {
            console.error("Backtest failed", err);
            alert("Simulation failed. Check console or try a more liquid stock.");
        } finally {
            setIsRunning(false);
        }
    };

    const selectSymbol = (s: any) => {
        setSymbol(s.symbol);
        setSearchQuery('');
        setShowDropdown(false);
    };

    const updateBalance = async () => {
        const newBalanceStr = prompt("Update Trading Capital (IDR):", balance.toString());
        if (newBalanceStr) {
            const amount = parseFloat(newBalanceStr);
            if (isNaN(amount)) return;
            try {
                await axios.post(`/api/backtest/balance/update?amount=${amount}`, {}, {
                    headers: { Authorization: `Bearer ${token}` }
                });
                if (user) updateUser({ ...user, balance: amount });
                setBalance(amount);
            } catch (err) {
                console.error(err);
            }
        }
    };

    return (
        <Layout>
            <div className="p-8 max-w-7xl mx-auto space-y-8 pb-20">
                <header className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                    <div>
                        <h1 className="text-4xl font-black text-white mb-2 tracking-tighter">Backtesting Engine</h1>
                        <p className="text-slate-400 text-sm font-medium uppercase tracking-widest">Metode CTG Algorithm v2.0</p>
                    </div>

                    <div className="flex items-center gap-4 bg-slate-900 border border-slate-800 p-5 rounded-[2.5rem] shadow-2xl">
                        <div className="p-3 bg-blue-600/20 rounded-2xl">
                            <Wallet className="w-6 h-6 text-blue-500" />
                        </div>
                        <div>
                            <div className="text-[10px] text-slate-500 font-black uppercase tracking-tighter">Trading Capital</div>
                            <div className="text-2xl font-black text-white leading-none">Rp {balance?.toLocaleString()}</div>
                        </div>
                        <button
                            onClick={updateBalance}
                            className="p-2 bg-slate-800 hover:bg-blue-600 text-white rounded-full transition-all"
                        >
                            <Plus className="w-5 h-5" />
                        </button>
                    </div>
                </header>

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                    {/* Left Controls */}
                    <div className="lg:col-span-4 space-y-6">
                        <div className="bg-slate-900 border border-slate-800 rounded-[2.5rem] p-8 shadow-2xl space-y-8 sticky top-8">
                            <div>
                                <h2 className="text-xl font-black text-white mb-6 flex items-center gap-2">
                                    <Target className="w-6 h-6 text-blue-500" /> Configure Strategy
                                </h2>

                                <div className="space-y-6">
                                    <div className="relative">
                                        <label className="block text-xs font-black text-slate-500 uppercase tracking-widest mb-3">Select Emiten (IDX)</label>

                                        {/* Quick Pick Section */}
                                        <div className="space-y-6 mb-8">
                                            {/* From Active Signals */}
                                            {suggestedStocks.length > 0 && (
                                                <div>
                                                    <div className="text-[10px] font-black text-slate-600 uppercase tracking-[0.2em] mb-3 flex items-center gap-2">
                                                        <Zap className="w-3 h-3 text-amber-500" /> Pattern Found
                                                    </div>
                                                    <div className="grid grid-cols-4 gap-2">
                                                        {suggestedStocks.map((s) => (
                                                            <button
                                                                key={s.symbol}
                                                                onClick={() => setSymbol(s.symbol)}
                                                                className={`p-2 rounded-xl text-[10px] font-black transition-all border ${
                                                                    symbol === s.symbol
                                                                    ? 'bg-blue-600 border-blue-500 text-white shadow-lg'
                                                                    : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-600'
                                                                }`}
                                                            >
                                                                {s.symbol}
                                                            </button>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}

                                            {/* From Master Universe */}
                                            <div>
                                                <div className="text-[10px] font-black text-slate-600 uppercase tracking-[0.2em] mb-3 flex items-center gap-2">
                                                    <TrendingUp className="w-3 h-3 text-blue-500" /> Top Universe
                                                </div>
                                                <div className="grid grid-cols-4 gap-2">
                                                    {topUniverse.map((s) => (
                                                        <button
                                                            key={s.symbol}
                                                            onClick={() => setSymbol(s.symbol)}
                                                            className={`p-2 rounded-xl text-[10px] font-black transition-all border ${
                                                                symbol === s.symbol
                                                                ? 'bg-blue-600 border-blue-500 text-white'
                                                                : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-600'
                                                            }`}
                                                        >
                                                            {s.symbol}
                                                        </button>
                                                    ))}
                                                </div>
                                            </div>
                                        </div>

                                        <div className="relative group">
                                            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                                            <input
                                                type="text"
                                                placeholder="Cari Kode Saham..."
                                                value={searchQuery}
                                                onFocus={() => setShowDropdown(true)}
                                                onChange={(e) => setSearchQuery(e.target.value)}
                                                className="w-full bg-slate-950 border border-slate-800 text-white pl-12 pr-4 py-4 rounded-2xl outline-none focus:ring-2 focus:ring-blue-500 transition-all font-bold"
                                            />
                                            {showDropdown && (
                                                <div className="absolute top-full left-0 right-0 mt-2 bg-slate-900 border border-slate-800 rounded-3xl overflow-hidden z-50 shadow-2xl max-h-60 overflow-y-auto">
                                                    <div className="p-2 border-b border-slate-800 flex justify-between items-center bg-slate-950/50">
                                                        <span className="text-[10px] font-black text-slate-500 ml-2">AVAILABLE IN DB</span>
                                                        <button onClick={() => setShowDropdown(false)} className="p-1 hover:bg-slate-800 rounded-full"><X className="w-3 h-3 text-slate-500" /></button>
                                                    </div>
                                                    {availableSymbols.map((s) => (
                                                        <div
                                                            key={s.symbol}
                                                            onClick={() => selectSymbol(s)}
                                                            className="p-5 hover:bg-blue-600 transition-all cursor-pointer flex justify-between items-center border-b border-slate-800 last:border-0 group"
                                                        >
                                                            <div className="flex flex-col">
                                                                <span className="font-black text-white text-lg group-hover:text-white">{s.symbol}</span>
                                                                <span className="text-[10px] text-slate-400 group-hover:text-blue-100 font-bold uppercase truncate max-w-[150px]">{s.company_name}</span>
                                                            </div>
                                                            <div className="text-right">
                                                                <div className="text-xs font-black text-white group-hover:text-white">Rp {s.last_price?.toLocaleString()}</div>
                                                                <div className="text-[8px] text-emerald-500 font-black group-hover:text-blue-200 uppercase tracking-tighter">READY</div>
                                                            </div>
                                                        </div>
                                                    ))}
                                                    {availableSymbols.length === 0 && <div className="p-8 text-center text-xs text-slate-500 font-bold">No stocks found matching criteria</div>}
                                                </div>
                                            )}
                                        </div>
                                        <div className="mt-4 flex gap-2">
                                            <span className="bg-blue-600 text-white text-[10px] font-black px-4 py-1.5 rounded-full shadow-lg shadow-blue-500/20">{symbol}</span>
                                            <span className="bg-slate-800 text-slate-400 text-[10px] font-black px-4 py-1.5 rounded-full border border-slate-700 uppercase tracking-widest">IDX MARKET</span>
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="block text-xs font-black text-slate-500 uppercase tracking-widest mb-3 ml-1">Timeframe</label>
                                            <select
                                                value={timeframe}
                                                onChange={(e) => setTimeframe(e.target.value)}
                                                className="w-full bg-slate-950 border border-slate-800 text-white p-4 rounded-2xl outline-none font-bold"
                                            >
                                                <option value="1d">Daily (Long)</option>
                                                <option value="1h">1 Hour (Swing)</option>
                                                <option value="15m">15 Min (Day)</option>
                                            </select>
                                        </div>
                                        <div>
                                            <label className="block text-xs font-black text-slate-500 uppercase tracking-widest mb-3 ml-1">Risk %</label>
                                            <input
                                                type="number"
                                                value={riskPerTrade}
                                                onChange={(e) => setRiskPerTrade(Number(e.target.value))}
                                                className="w-full bg-slate-950 border border-slate-800 text-white p-4 rounded-2xl outline-none font-bold"
                                            />
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <button
                                onClick={runSimulation}
                                disabled={isRunning}
                                className="w-full flex items-center justify-center gap-3 py-5 bg-blue-600 hover:bg-blue-700 text-white rounded-3xl font-black transition-all shadow-xl shadow-blue-500/30 disabled:opacity-50"
                            >
                                {isRunning ? <Loader2 className="w-6 h-6 animate-spin" /> : <Play className="w-6 h-6 fill-current" />}
                                {isRunning ? 'CALCULATING CTG RUMUS...' : 'START SIMULATION'}
                            </button>

                            <div className="p-5 bg-blue-500/5 border border-blue-500/10 rounded-3xl">
                                <div className="flex items-center gap-2 text-blue-400 mb-2">
                                    <ShieldAlert className="w-4 h-4" />
                                    <span className="text-[10px] font-black uppercase tracking-widest">CTG Compliance</span>
                                </div>
                                <p className="text-[9px] text-slate-500 leading-relaxed font-bold uppercase">
                                    Algoritma menjalankan simulasi bar-demi-bar sesuai rumus §3-§5. Akurasi target {">"}95%.
                                </p>
                            </div>
                        </div>
                    </div>

                    {/* Right Results */}
                    <div className="lg:col-span-8 space-y-8">
                        {results ? (
                            <div className="animate-in fade-in slide-in-from-bottom-8 duration-700 space-y-8">
                                {/* Result Chart - The Elegant One */}
                                <div className="bg-slate-900 border border-slate-800 rounded-[3rem] overflow-hidden shadow-2xl relative min-h-[600px] w-full">
                                    <div className="absolute top-8 left-8 z-10 bg-slate-950/40 backdrop-blur-md p-4 rounded-2xl border border-white/5">
                                        <h2 className="text-2xl font-black text-white flex items-center gap-3 uppercase tracking-tighter">
                                            <TrendingUp className="w-8 h-8 text-emerald-500" /> {symbol} Simulation Map
                                        </h2>
                                        <p className="text-[10px] text-slate-400 font-bold uppercase tracking-[0.3em] mt-1">Visual Execution History</p>
                                    </div>
                                    <div className="h-full w-full">
                                        <PatternChart data={results.candles} trades={results.trades} />
                                    </div>
                                    <div className="absolute bottom-8 right-8 bg-slate-950/80 backdrop-blur-md px-6 py-3 rounded-2xl border border-white/5 flex gap-6">
                                        <div className="flex items-center gap-2">
                                            <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                                            <span className="text-[9px] font-black text-white uppercase tracking-widest">Entry Points</span>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
                                            <span className="text-[9px] font-black text-white uppercase tracking-widest">Profit Exits</span>
                                        </div>
                                    </div>
                                </div>

                                {/* Performance Grid */}
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                    {[
                                        { label: 'Net Profit', value: `Rp ${results.metrics.net_profit.toLocaleString()}`, sub: 'PROFIT REALIZED', color: results.metrics.net_profit >= 0 ? 'text-emerald-500' : 'text-red-500', icon: TrendingUp },
                                        { label: 'Win Rate', value: results.metrics.win_rate, sub: `${results.metrics.wins} WINS / ${results.metrics.losses} LOSS`, color: 'text-blue-500', icon: CheckCircle2 },
                                        { label: 'Trades', value: results.metrics.total_trades, sub: 'SAMPLE SIZE', color: 'text-purple-500', icon: Activity },
                                        { label: 'Efficiency', value: results.metrics.efficiency || '0.0%', sub: 'FORMULA HIT RATE', color: 'text-amber-500', icon: ShieldAlert },
                                    ].map((stat, i) => (
                                        <div key={i} className="bg-slate-900 border border-slate-800 p-6 rounded-[2rem] shadow-xl hover:scale-[1.02] transition-all">
                                            <div className={`p-2 w-fit rounded-xl bg-slate-950 border border-slate-800 mb-4 ${stat.color}`}>
                                                <stat.icon className="w-5 h-5" />
                                            </div>
                                            <div className={`text-2xl font-black ${stat.color} mb-1 tracking-tighter`}>{stat.value}</div>
                                            <div className="text-[9px] text-slate-500 font-black uppercase tracking-widest">{stat.label}</div>
                                            <div className="text-[8px] text-slate-700 font-black mt-3 tracking-tighter">{stat.sub}</div>
                                        </div>
                                    ))}
                                </div>

                                {/* Execution List */}
                                <div className="bg-slate-900 border border-slate-800 rounded-[3rem] overflow-hidden shadow-2xl">
                                    <div className="p-10 border-b border-slate-800 flex items-center justify-between">
                                        <div>
                                            <h2 className="font-black text-white uppercase tracking-widest text-lg">Execution Log</h2>
                                            <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest mt-1">Detailed history of all trades</p>
                                        </div>
                                        <span className="text-[10px] font-black text-blue-500 bg-blue-500/10 px-5 py-2 rounded-full border border-blue-500/20 uppercase tracking-widest animate-pulse">Live API Data</span>
                                    </div>
                                    <div className="overflow-x-auto">
                                        <table className="w-full text-left">
                                            <thead className="bg-slate-950/50 text-slate-500 uppercase text-[10px] font-black tracking-widest">
                                                <tr>
                                                    <th className="px-10 py-6">Emiten / Date</th>
                                                    <th className="px-10 py-6">Formula Mode</th>
                                                    <th className="px-10 py-6">Execution</th>
                                                    <th className="px-10 py-6 text-right">P&L (IDR)</th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-slate-800">
                                                {results.trades.map((trade: any, i: number) => (
                                                    <tr key={i} className="hover:bg-slate-800/40 transition-all group">
                                                        <td className="px-10 py-8">
                                                            <div className="font-black text-white text-xl">{trade.symbol}</div>
                                                            <div className="text-[10px] text-slate-500 font-bold uppercase tracking-tighter mt-1">
                                                                {new Date(trade.entry_ts).toLocaleDateString()}
                                                            </div>
                                                        </td>
                                                        <td className="px-10 py-8">
                                                            <div className="text-[11px] font-black text-blue-400 bg-blue-400/5 px-4 py-2 rounded-xl border border-blue-400/10 inline-block uppercase">
                                                                {trade.strategy}
                                                            </div>
                                                        </td>
                                                        <td className="px-10 py-8">
                                                            <span className={`px-4 py-2 rounded-xl text-[10px] font-black tracking-widest uppercase border ${trade.reason === 'TAKE PROFIT' ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20' : 'bg-red-500/10 text-red-500 border-red-500/20'}`}>
                                                                {trade.reason}
                                                            </span>
                                                            <div className="text-[9px] text-slate-600 font-bold uppercase mt-3 ml-1">{trade.lots} Lots @ Rp {trade.entry_price.toLocaleString()}</div>
                                                        </td>
                                                        <td className="px-10 py-8 text-right">
                                                            <div className={`text-2xl font-black ${trade.pnl >= 0 ? 'text-emerald-500' : 'text-red-500'} tracking-tighter`}>
                                                                {trade.pnl >= 0 ? '+' : ''}{trade.pnl.toLocaleString()}
                                                            </div>
                                                            <div className={`text-[10px] font-black ${trade.pnl >= 0 ? 'text-emerald-500/70' : 'text-red-500/70'} uppercase mt-1`}>
                                                                ROI: {trade.pnl_pct.toFixed(2)}%
                                                            </div>
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <div className="flex flex-col items-center justify-center h-full min-h-[700px] bg-slate-900/50 border border-dashed border-slate-800 rounded-[4rem]">
                                <div className="text-center space-y-8 opacity-40">
                                    <div className="relative inline-block">
                                        <div className="w-32 h-32 bg-blue-500/10 rounded-full flex items-center justify-center animate-pulse">
                                            <Activity className="w-16 h-16 text-slate-600" />
                                        </div>
                                        <div className="absolute -top-2 -right-2 w-12 h-12 bg-slate-950 rounded-full flex items-center justify-center border-4 border-slate-900">
                                            <ShieldAlert className="w-6 h-6 text-blue-500" />
                                        </div>
                                    </div>
                                    <div>
                                        <h3 className="text-3xl font-black text-white uppercase tracking-tighter">Simulation Ready</h3>
                                        <p className="text-sm text-slate-500 font-bold uppercase tracking-[0.2em] mt-3">Select stock from DB and run CTG Algorithm</p>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </Layout>
    );
};

export default Backtest;
