import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import {
    Wallet, Briefcase, TrendingUp, TrendingDown, Clock, Search,
    ArrowUpCircle, ArrowDownCircle, RotateCcw, Trash2, Plus,
    X, ChevronRight, Info, AlertCircle, BarChart3, Loader2, Play, Zap
} from 'lucide-react';
import axios from 'axios';
import { useAuth } from '../hooks/AuthContext';
import { PatternChart } from '../components/charts/PatternChart';

// Utils
const floatToIDR = (val: number) => {
    if (!val) return "0";
    if (val >= 1_000_000_000_000) return (val / 1_000_000_000_000).toFixed(2) + " T";
    if (val >= 1_000_000_000) return (val / 1_000_000_000).toFixed(2) + " B";
    if (val >= 1_000_000) return (val / 1_000_000).toFixed(2) + " M";
    return val.toLocaleString();
};

interface Session {
    id: number;
    name: string;
    initial_balance: number;
    current_balance: number;
    status: string;
    created_at: string;
}

interface Position {
    id: number;
    symbol: string;
    avg_price: number;
    quantity: number;
    current_price: number;
    market_value: number;
    unrealized_pnl: number;
    unrealized_pnl_pct: number;
    stop_loss?: number;
    take_profit?: number;
}

const Backtest: React.FC = () => {
    const { token } = useAuth();
    const [sessions, setSessions] = useState<Session[]>([]);
    const [activeSession, setActiveSession] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [availableSymbols, setAvailableSymbols] = useState<any[]>([]);
    const [selectedSymbol, setSelectedSymbol] = useState<any>(null);
    const [showBuyModal, setShowBuyModal] = useState(false);
    const [showSellModal, setShowSellModal] = useState(false);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [buyLot, setBuyLot] = useState(1);
    const [buySL, setBuySL] = useState<number | ''>('');
    const [buyTP, setBuyTP] = useState<number | ''>('');
    const [sellLot, setSellLot] = useState(1);
    const [transactions, setTransactions] = useState<any[]>([]);
    const [newSessionName, setNewSessionName] = useState('');
    const [chartData, setChartData] = useState<any>(null);
    const [chartLoading, setChartLoading] = useState(false);
    const [lastSyncTime, setLastSyncTime] = useState<string>(new Date().toLocaleTimeString());

    useEffect(() => {
        if (token) {
            fetchSessions();

            // Heartbeat: Refresh active session every 2 seconds to reflect price movements and auto-trades
            const interval = setInterval(() => {
                if (activeSession?.session?.id) {
                    fetchSessionDetail(activeSession.session.id);
                    setLastSyncTime(new Date().toLocaleTimeString());
                }
            }, 2000);

            // Check for symbol in URL
            const urlParams = new URLSearchParams(window.location.search);
            const sym = urlParams.get('symbol');
            if (sym) {
                setSearchQuery(sym);
                fetchSymbols(sym);
            }

            return () => clearInterval(interval);
        }
    }, [token, activeSession?.session?.id]);

    const loadChart = async (symbol: string) => {
        setChartLoading(true);
        try {
            const res = await axios.get(`/api/stocks/${symbol}/candles`, {
                params: { timeframe: '1d' },
                headers: { Authorization: `Bearer ${token}` }
            });
            setChartData(res.data);
        } catch (err) {
            console.error("Failed to load chart:", err);
        } finally {
            setChartLoading(false);
        }
    };

    useEffect(() => {
        if (selectedSymbol) {
            loadChart(selectedSymbol.symbol);
        } else {
            setChartData(null);
        }
    }, [selectedSymbol]);

    const fetchSessions = async () => {
        try {
            setLoading(true);
            const res = await axios.get('/api/backtest/sessions', {
                headers: { Authorization: `Bearer ${token}` }
            });
            setSessions(res.data);
            if (res.data.length > 0 && !activeSession) {
                fetchSessionDetail(res.data[0].id);
            }
        } catch (err) { console.error(err); }
        finally { setLoading(false); }
    };

    const fetchSessionDetail = async (id: number) => {
        try {
            const res = await axios.get(`/api/backtest/sessions/${id}`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            setActiveSession(res.data);
            fetchTransactions(id);
        } catch (err) { console.error(err); }
    };

    const fetchTransactions = async (id: number) => {
        try {
            const res = await axios.get(`/api/backtest/transactions/${id}`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            setTransactions(res.data);
        } catch (err) { console.error(err); }
    };

    const fetchSymbols = async (query: string) => {
        try {
            const res = await axios.get('/api/backtest/symbols', {
                params: { query },
                headers: { Authorization: `Bearer ${token}` }
            });
            setAvailableSymbols(res.data);
        } catch (err) { console.error(err); }
    };

    useEffect(() => {
        const delayDebounceFn = setTimeout(() => {
            if (searchQuery) fetchSymbols(searchQuery);
        }, 300);
        return () => clearTimeout(delayDebounceFn);
    }, [searchQuery]);

    const handleCreateSession = async () => {
        try {
            const res = await axios.post('/api/backtest/sessions', {
                name: newSessionName || `Simulasi #${sessions.length + 1}`
            }, { headers: { Authorization: `Bearer ${token}` } });
            setSessions([res.data, ...sessions]);
            setActiveSession(null);
            fetchSessionDetail(res.data.id);
            setShowCreateModal(false);
            setNewSessionName('');
        } catch (err) { alert("Gagal membuat sesi."); }
    };

    const handleResetSession = async () => {
        if (!window.confirm("Reset simulator? Seluruh posisi dan histori akan dihapus.")) return;
        try {
            await axios.post(`/api/backtest/sessions/${activeSession.session.id}/reset`, {}, {
                headers: { Authorization: `Bearer ${token}` }
            });
            fetchSessionDetail(activeSession.session.id);
        } catch (err) { alert("Gagal meriset sesi."); }
    };

    const handleDeleteSession = async (id: number) => {
        if (!window.confirm("Hapus sesi ini secara permanen?")) return;
        try {
            await axios.delete(`/api/backtest/sessions/${id}`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            const newSessions = sessions.filter(s => s.id !== id);
            setSessions(newSessions);
            if (activeSession?.session.id === id) {
                setActiveSession(null);
                if (newSessions.length > 0) fetchSessionDetail(newSessions[0].id);
            }
        } catch (err) { alert("Gagal menghapus sesi."); }
    };

    const handleBuy = async () => {
        if (!selectedSymbol || !activeSession) return;
        try {
            await axios.post('/api/backtest/order', {
                session_id: activeSession.session.id,
                symbol: selectedSymbol.symbol,
                side: 'BUY',
                quantity: buyLot * 100,
                price: selectedSymbol.last_price,
                stop_loss: buySL || null,
                take_profit: buyTP || null
            }, { headers: { Authorization: `Bearer ${token}` } });
            setShowBuyModal(false);
            fetchSessionDetail(activeSession.session.id);
        } catch (err: any) { alert(err.response?.data?.detail || "Gagal melakukan pembelian."); }
    };

    const handleSell = async (pos?: Position) => {
        const symbol = pos ? pos.symbol : selectedSymbol.symbol;
        const qty = pos ? pos.quantity : (sellLot * 100);
        const price = pos ? pos.current_price : selectedSymbol.last_price;

        try {
            await axios.post('/api/backtest/order', {
                session_id: activeSession.session.id,
                symbol: symbol,
                side: 'SELL',
                quantity: qty,
                price: price
            }, { headers: { Authorization: `Bearer ${token}` } });
            setShowSellModal(false);
            fetchSessionDetail(activeSession.session.id);
        } catch (err: any) { alert(err.response?.data?.detail || "Gagal melakukan penjualan."); }
    };

    if (loading) return (
        <Layout>
            <div className="flex items-center justify-center min-h-screen">
                <Loader2 className="w-12 h-12 text-blue-500 animate-spin" />
            </div>
        </Layout>
    );

    return (
        <Layout>
            <div className="p-8 max-w-7xl mx-auto space-y-8 pb-32">
                <header className="flex flex-col md:flex-row md:items-end justify-between gap-6">
                    <div>
                        <h1 className="text-4xl font-black text-white mb-2 tracking-tighter uppercase italic">Virtual Trading Simulator</h1>
                        <div className="flex items-center gap-3">
                            <p className="text-slate-500 text-xs font-bold uppercase tracking-[0.3em] flex items-center gap-2">
                                Quantitative Strategy Validator <TrendingUp className="w-4 h-4 text-emerald-500" />
                            </p>
                            <div className="h-4 w-px bg-slate-800" />
                            <div className="flex items-center gap-2 bg-blue-500/10 px-2 py-1 rounded-md border border-blue-500/20">
                                <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
                                <span className="text-[9px] font-black text-blue-500 uppercase tracking-widest">Live Sync: {lastSyncTime}</span>
                            </div>
                        </div>
                    </div>
                    <div className="flex gap-4">
                        <button onClick={() => setShowCreateModal(true)} className="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white font-black text-[10px] uppercase tracking-widest rounded-2xl transition-all shadow-xl shadow-blue-900/20 flex items-center gap-2">
                            <Plus className="w-4 h-4" /> New Session
                        </button>
                    </div>
                </header>

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                    {/* Sidebar: Session & Search */}
                    <div className="lg:col-span-3 space-y-6">
                        {/* Session Selector */}
                        <div className="bg-slate-900 border border-slate-800 rounded-[2.5rem] p-6 shadow-2xl space-y-4">
                            <h2 className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-4 flex items-center gap-2">
                                <Clock className="w-3 h-3" /> Active Sessions
                            </h2>
                            <div className="space-y-2">
                                {sessions.map(s => (
                                    <div
                                        key={s.id}
                                        onClick={() => fetchSessionDetail(s.id)}
                                        className={`p-4 rounded-2xl cursor-pointer transition-all border flex items-center justify-between group ${activeSession?.session.id === s.id ? 'bg-blue-600/10 border-blue-600/50' : 'bg-slate-950/50 border-slate-800 hover:border-slate-700'}`}
                                    >
                                        <div className="truncate pr-2">
                                            <div className={`text-[11px] font-black uppercase ${activeSession?.session.id === s.id ? 'text-blue-400' : 'text-white'}`}>{s.name}</div>
                                            <div className="text-[9px] text-slate-500 font-bold mt-1">Rp {floatToIDR(s.current_balance)}</div>
                                        </div>
                                        <button onClick={(e) => { e.stopPropagation(); handleDeleteSession(s.id); }} className="p-2 opacity-0 group-hover:opacity-100 hover:text-red-500 transition-all">
                                            <Trash2 className="w-3.5 h-3.5" />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Search Stock */}
                        <div className="bg-slate-900 border border-slate-800 rounded-[2.5rem] p-6 shadow-2xl space-y-4">
                            <h2 className="text-[10px] font-black text-slate-500 uppercase tracking-widest flex items-center gap-2">
                                <Search className="w-3 h-3" /> Market Search
                            </h2>
                            <div className="relative">
                                <input
                                    type="text"
                                    placeholder="Search Ticker..."
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    className="w-full bg-slate-950 border border-slate-800 text-white pl-4 pr-4 py-3 rounded-xl outline-none focus:ring-1 focus:ring-blue-500 font-bold text-xs"
                                />
                            </div>
                            <div className="space-y-1 max-h-60 overflow-y-auto custom-scrollbar pr-1">
                                {availableSymbols.map(s => (
                                    <div
                                        key={s.symbol}
                                        onClick={() => setSelectedSymbol(s)}
                                        className={`p-3 rounded-xl cursor-pointer transition-all border flex items-center justify-between ${selectedSymbol?.symbol === s.symbol ? 'bg-emerald-500/10 border-emerald-500/50' : 'bg-slate-950/30 border-transparent hover:border-slate-800'}`}
                                    >
                                        <div>
                                            <div className="text-[11px] font-black text-white">{s.symbol}</div>
                                            <div className="text-[8px] text-slate-500 font-bold truncate max-w-[120px]">{s.company_name}</div>
                                        </div>
                                        <div className="text-right">
                                            <div className="text-[10px] font-black text-white">Rp {s.last_price?.toLocaleString()}</div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>

                    {/* Main Dashboard */}
                    <div className="lg:col-span-9 space-y-8">
                        {activeSession ? (
                            <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 space-y-8">
                                {/* Session Overview Cards */}
                                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                                    <div className="bg-slate-900 border border-slate-800 p-6 rounded-[2rem] shadow-xl relative overflow-hidden group">
                                        <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
                                            <TrendingUp className="w-20 h-20 text-white" />
                                        </div>
                                        <div className="text-[9px] text-slate-500 font-black uppercase tracking-widest mb-1">Total Equity</div>
                                        <div className="text-2xl font-black text-white tracking-tighter">Rp {floatToIDR(activeSession.total_equity)}</div>
                                        <div className={`text-[10px] font-bold mt-2 flex items-center gap-1 ${activeSession.total_equity >= activeSession.session.initial_balance ? 'text-emerald-500' : 'text-red-500'}`}>
                                            {activeSession.total_equity >= activeSession.session.initial_balance ? <ArrowUpCircle className="w-3 h-3" /> : <ArrowDownCircle className="w-3 h-3" />}
                                            {(((activeSession.total_equity / activeSession.session.initial_balance) - 1) * 100).toFixed(2)}%
                                        </div>
                                    </div>
                                    <div className="bg-slate-900 border border-slate-800 p-6 rounded-[2rem] shadow-xl">
                                        <div className="text-[9px] text-slate-500 font-black uppercase tracking-widest mb-1">Cash Balance</div>
                                        <div className="text-xl font-black text-white tracking-tighter">Rp {floatToIDR(activeSession.session.current_balance)}</div>
                                        <div className="text-[9px] text-slate-600 font-bold mt-2 uppercase tracking-tighter">Available to Invest</div>
                                    </div>
                                    <div className="bg-slate-900 border border-slate-800 p-6 rounded-[2rem] shadow-xl">
                                        <div className="text-[9px] text-slate-500 font-black uppercase tracking-widest mb-1">Stock Portfolio</div>
                                        <div className="text-xl font-black text-blue-400 tracking-tighter">Rp {floatToIDR(activeSession.total_market_value)}</div>
                                        <div className="text-[9px] text-slate-600 font-bold mt-2 uppercase tracking-tighter">{activeSession.portfolio.length} Open Positions</div>
                                    </div>
                                    <div className="bg-slate-900 border border-slate-800 p-6 rounded-[2rem] shadow-xl flex flex-col justify-center">
                                        <button onClick={handleResetSession} className="w-full py-4 bg-slate-800 hover:bg-amber-600/20 hover:text-amber-500 text-slate-400 rounded-2xl transition-all flex items-center justify-center gap-3 border border-slate-700 hover:border-amber-500/30 group">
                                            <RotateCcw className="w-4 h-4 group-hover:rotate-[-45deg] transition-transform" />
                                            <span className="text-[10px] font-black uppercase tracking-widest">Reset Session</span>
                                        </button>
                                    </div>
                                </div>

                                {/* Active Portfolio & Market Detail Chart */}
                                <div className="space-y-8">
                                    {selectedSymbol && (
                                        <div className="animate-in fade-in slide-in-from-top-4 duration-500 space-y-4">
                                            <div className="flex items-center justify-between bg-slate-900 border border-slate-800 p-6 rounded-[2.5rem] shadow-2xl">
                                                <div className="flex items-center gap-6">
                                                    <div className="p-4 bg-blue-500/10 rounded-3xl text-blue-500 border border-blue-500/20">
                                                        <BarChart3 className="w-8 h-8" />
                                                    </div>
                                                    <div>
                                                        <div className="flex items-center gap-3">
                                                            <h2 className="text-4xl font-black text-white tracking-tighter uppercase italic">{selectedSymbol.symbol}</h2>
                                                            <div className="flex gap-2">
                                                                <button onClick={() => setShowBuyModal(true)} className="px-6 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-black text-[10px] uppercase tracking-widest rounded-xl transition-all shadow-lg shadow-emerald-900/20">BUY</button>
                                                                <button onClick={() => setShowSellModal(true)} className="px-6 py-2 bg-red-600 hover:bg-red-500 text-white font-black text-[10px] uppercase tracking-widest rounded-xl transition-all shadow-lg shadow-red-900/20">SELL</button>
                                                            </div>
                                                        </div>
                                                        <p className="text-[10px] text-slate-500 font-bold uppercase mt-1 tracking-widest flex items-center gap-2">
                                                            Market Price: Rp {selectedSymbol.last_price?.toLocaleString()} | Live Analysis Chart
                                                        </p>
                                                    </div>
                                                </div>
                                                <button onClick={() => setSelectedSymbol(null)} className="p-4 bg-slate-800 hover:bg-red-600 text-white rounded-full transition-all">
                                                    <X className="w-6 h-6" />
                                                </button>
                                            </div>

                                            <div className="h-[600px] shadow-2xl relative bg-slate-950 rounded-[3rem] overflow-hidden border border-slate-800">
                                                {chartLoading && (
                                                    <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-slate-950/80 backdrop-blur-md">
                                                        <Loader2 className="w-12 h-12 text-blue-500 animate-spin mb-4" />
                                                        <span className="text-[10px] font-black text-blue-500 uppercase tracking-[0.3em]">Loading Market Context...</span>
                                                    </div>
                                                )}
                                                <PatternChart data={chartData} metadata={null} interactive={true} />
                                            </div>
                                        </div>
                                    )}

                                    {/* Active Portfolio */}
                                    <div className="bg-slate-900 border border-slate-800 rounded-[2.5rem] overflow-hidden shadow-2xl">
                                        <div className="p-8 border-b border-slate-800 bg-slate-950/20 flex items-center justify-between">
                                            <div className="flex items-center gap-4">
                                                <div className="p-3 bg-blue-600/10 rounded-2xl text-blue-400"><Briefcase className="w-6 h-6" /></div>
                                                <div>
                                                    <h2 className="text-xl font-black text-white uppercase tracking-tighter italic">Virtual Portfolio</h2>
                                                    <p className="text-[9px] text-slate-500 font-black uppercase tracking-widest mt-1">Real-time valuation based on market prices</p>
                                                </div>
                                            </div>
                                            <div className="flex gap-2">
                                                 <button
                                                    onClick={() => {
                                                        const sym = prompt("Masukkan Ticker untuk Auto-Backtest Strategy:");
                                                        if (sym) {
                                                            axios.post(`/api/backtest/sessions/${activeSession.session.id}/run-strategy`, {
                                                                symbol: sym,
                                                                timeframe: '1d',
                                                                risk_per_trade: 1.0
                                                            }, { headers: { Authorization: `Bearer ${token}` } })
                                                            .then(() => fetchSessionDetail(activeSession.session.id))
                                                            .catch(err => alert("Gagal menjalankan strategi."));
                                                        }
                                                    }}
                                                    className="px-4 py-2 bg-blue-600/20 text-blue-400 text-[9px] font-black rounded-xl border border-blue-600/20 hover:bg-blue-600 hover:text-white transition-all uppercase tracking-widest"
                                                >
                                                    Run Strategy
                                                </button>
                                            </div>
                                        </div>
                                        <div className="overflow-x-auto">
                                            <table className="w-full text-left">
                                                <thead className="bg-slate-950/50 text-[9px] font-black uppercase text-slate-500 tracking-widest">
                                                    <tr>
                                                        <th className="px-8 py-4">Symbol</th>
                                                        <th className="px-8 py-4 text-right">Avg Price</th>
                                                        <th className="px-8 py-4 text-right">Qty (Lot)</th>
                                                        <th className="px-8 py-4 text-right">Current</th>
                                                        <th className="px-8 py-4 text-right">Market Value</th>
                                                        <th className="px-8 py-4 text-right">Unrealized P&L</th>
                                                        <th className="px-8 py-4 text-center">Action</th>
                                                    </tr>
                                                </thead>
                                                <tbody className="divide-y divide-slate-800 font-bold">
                                                    {activeSession.portfolio.length === 0 ? (
                                                        <tr><td colSpan={7} className="px-8 py-20 text-center text-slate-600 font-black uppercase italic text-xs">Portfolio Kosong</td></tr>
                                                    ) : activeSession.portfolio.map((pos: Position) => (
                                                        <tr key={pos.id} className="hover:bg-blue-600/5 transition-all group">
                                                            <td className="px-8 py-6">
                                                                <div className="text-lg font-black text-white group-hover:text-blue-400 transition-colors">{pos.symbol}</div>
                                                            </td>
                                                            <td className="px-8 py-6 text-right text-xs text-slate-400">Rp {pos.avg_price?.toLocaleString()}</td>
                                                            <td className="px-8 py-6 text-right">
                                                                <div className="text-xs text-white">{pos.quantity.toLocaleString()}</div>
                                                                <div className="text-[9px] text-slate-500">{(pos.quantity / 100).toLocaleString()} Lot</div>
                                                            </td>
                                                            <td className="px-8 py-6 text-right text-xs text-white">Rp {pos.current_price?.toLocaleString()}</td>
                                                            <td className="px-8 py-6 text-right text-xs text-blue-400">Rp {pos.market_value?.toLocaleString()}</td>
                                                            <td className="px-8 py-6 text-right">
                                                                <div className={`text-xs ${pos.unrealized_pnl >= 0 ? 'text-emerald-500' : 'text-red-500'}`}>
                                                                    {pos.unrealized_pnl >= 0 ? '+' : ''}{pos.unrealized_pnl.toLocaleString()}
                                                                </div>
                                                                <div className={`text-[9px] ${pos.unrealized_pnl >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                                                                    {pos.unrealized_pnl_pct.toFixed(2)}%
                                                                </div>
                                                            </td>
                                                            <td className="px-8 py-6 text-center">
                                                                <button
                                                                    onClick={() => { setSelectedSymbol({symbol: pos.symbol, last_price: pos.current_price}); setSellLot(pos.quantity/100); setShowSellModal(true); }}
                                                                    className="px-5 py-2 bg-red-600/10 hover:bg-red-600 text-red-500 hover:text-white text-[9px] font-black rounded-xl transition-all uppercase border border-red-500/20"
                                                                >
                                                                    SELL
                                                                </button>
                                                            </td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>

                                    {/* Transaction History & Recent Activity */}
                                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 pb-20">
                                        <div className="bg-slate-900 border border-slate-800 rounded-[2.5rem] p-8 shadow-2xl h-full flex flex-col justify-center items-center text-center opacity-40">
                                            <Info className="w-12 h-12 text-blue-400 mb-4" />
                                            <h3 className="text-xl font-black text-white uppercase tracking-tighter">Trading Instruction</h3>
                                            <p className="text-[10px] text-slate-500 font-bold uppercase mt-2 max-w-xs leading-relaxed">
                                                Use the search bar on the left to find a stock. Select it to view the interactive chart and place virtual orders.
                                            </p>
                                        </div>

                                        <div className="bg-slate-900 border border-slate-800 rounded-[2.5rem] p-8 shadow-2xl h-full flex flex-col">
                                            <h3 className="text-[11px] font-black text-white uppercase tracking-widest mb-6 flex items-center gap-3">
                                                <Clock className="w-4 h-4 text-blue-500" /> Recent Transactions
                                            </h3>
                                            <div className="space-y-3 overflow-y-auto max-h-[400px] pr-2 custom-scrollbar flex-1">
                                                {transactions.length === 0 ? (
                                                    <div className="text-center py-10 text-slate-600 font-black uppercase text-[10px] italic">No transactions recorded</div>
                                                ) : transactions.map(t => (
                                                    <div key={t.id} className="bg-slate-950/50 border border-slate-800 p-4 rounded-2xl flex items-center justify-between">
                                                        <div className="flex items-center gap-4">
                                                            <div className={`p-2.5 rounded-xl ${t.side === 'BUY' ? 'bg-emerald-500/10 text-emerald-500' : 'bg-red-500/10 text-red-500'}`}>
                                                                {t.side === 'BUY' ? <ArrowUpCircle className="w-4 h-4" /> : <ArrowDownCircle className="w-4 h-4" />}
                                                            </div>
                                                            <div>
                                                                <div className="text-[11px] font-black text-white">{t.symbol} <span className="text-slate-500 text-[9px] ml-1">x{(t.quantity/100).toLocaleString()} Lot</span></div>
                                                                <div className="text-[8px] text-slate-600 font-bold uppercase mt-0.5">{new Date(t.ts).toLocaleString('id-ID', {day:'2-digit', month:'short', hour:'2-digit', minute:'2-digit'})}</div>
                                                            </div>
                                                        </div>
                                                        <div className="text-right">
                                                            <div className="text-[10px] font-black text-white">Rp {t.price?.toLocaleString()}</div>
                                                            {t.realized_pnl !== 0 && (
                                                                <div className={`text-[8px] font-black mt-0.5 ${t.realized_pnl >= 0 ? 'text-emerald-500' : 'text-red-500'}`}>
                                                                    {t.realized_pnl >= 0 ? '+' : ''}{t.realized_pnl?.toLocaleString()} ({t.realized_pnl_pct?.toFixed(2)}%)
                                                                </div>
                                                            )}
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <div className="flex flex-col items-center justify-center min-h-[600px] bg-slate-900/50 border border-dashed border-slate-800 rounded-[4rem] animate-pulse">
                                <Zap className="w-16 h-16 text-slate-700 mb-4" />
                                <h3 className="text-xl font-black text-slate-600 uppercase tracking-widest">Select or Create a Session to Start</h3>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* BUY MODAL */}
            {showBuyModal && selectedSymbol && activeSession && (
                <div className="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-slate-950/90 backdrop-blur-xl animate-in fade-in duration-300">
                    <div className="max-w-md w-full bg-slate-900 border border-slate-800 rounded-[3rem] shadow-2xl overflow-hidden animate-in zoom-in-95 duration-300">
                        <div className="p-8 border-b border-slate-800 bg-emerald-500/5 flex items-center justify-between">
                            <div>
                                <h3 className="text-2xl font-black text-white tracking-tighter">BELI {selectedSymbol.symbol}</h3>
                                <p className="text-[10px] text-slate-500 font-bold uppercase mt-1">Virtual Order Execution</p>
                            </div>
                            <button onClick={() => setShowBuyModal(false)} className="p-3 bg-slate-800 hover:bg-slate-700 text-white rounded-full transition-all">
                                <X className="w-5 h-5" />
                            </button>
                        </div>
                        <div className="p-8 space-y-6">
                            <div className="grid grid-cols-2 gap-4">
                                <div className="p-4 bg-slate-950/50 rounded-2xl border border-slate-800">
                                    <div className="text-[8px] text-slate-600 font-black uppercase mb-1">Market Price</div>
                                    <div className="text-sm font-black text-white">Rp {selectedSymbol.last_price?.toLocaleString()}</div>
                                </div>
                                <div className="p-4 bg-slate-950/50 rounded-2xl border border-slate-800">
                                    <div className="text-[8px] text-slate-600 font-black uppercase mb-1">Available Cash</div>
                                    <div className="text-sm font-black text-blue-400">Rp {floatToIDR(activeSession.session.current_balance)}</div>
                                </div>
                            </div>

                            <div className="space-y-4">
                                <div>
                                    <label className="block text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2">Jumlah Lot (1 Lot = 100 Lembar)</label>
                                    <div className="flex items-center gap-3">
                                        <button onClick={() => setBuyLot(Math.max(1, buyLot - 1))} className="p-3 bg-slate-800 hover:bg-slate-700 text-white rounded-xl transition-all">-</button>
                                        <input
                                            type="number"
                                            value={buyLot}
                                            onChange={(e) => setBuyLot(Math.max(1, parseInt(e.target.value) || 0))}
                                            className="flex-1 bg-slate-950 border border-slate-800 text-white py-3 rounded-xl outline-none focus:ring-1 focus:ring-emerald-500 font-black text-center text-lg"
                                        />
                                        <button onClick={() => setBuyLot(buyLot + 1)} className="p-3 bg-slate-800 hover:bg-slate-700 text-white rounded-xl transition-all">+</button>
                                    </div>
                                    <div className="flex justify-between mt-3 px-1">
                                        <button onClick={() => setBuyLot(10)} className="text-[9px] font-black text-slate-500 hover:text-white transition-all uppercase underline">10 Lot</button>
                                        <button onClick={() => setBuyLot(100)} className="text-[9px] font-black text-slate-500 hover:text-white transition-all uppercase underline">100 Lot</button>
                                        <button onClick={() => setBuyLot(1000)} className="text-[9px] font-black text-slate-500 hover:text-white transition-all uppercase underline">1k Lot</button>
                                        <button onClick={() => {
                                            const max = Math.floor(activeSession.session.current_balance / (selectedSymbol.last_price * 100 * 1.002));
                                            setBuyLot(Math.max(1, max));
                                        }} className="text-[9px] font-black text-blue-500 hover:text-blue-400 transition-all uppercase underline">Max Buy</button>
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2 text-red-500">Stop Loss</label>
                                        <input type="number" placeholder="Optional" value={buySL} onChange={(e) => setBuySL(e.target.value ? parseFloat(e.target.value) : '')} className="w-full bg-slate-950 border border-slate-800 text-white p-3 rounded-xl outline-none font-bold text-xs" />
                                    </div>
                                    <div>
                                        <label className="block text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2 text-emerald-500">Take Profit</label>
                                        <input type="number" placeholder="Optional" value={buyTP} onChange={(e) => setBuyTP(e.target.value ? parseFloat(e.target.value) : '')} className="w-full bg-slate-950 border border-slate-800 text-white p-3 rounded-xl outline-none font-bold text-xs" />
                                    </div>
                                </div>
                            </div>

                            <div className="p-6 bg-slate-950 rounded-3xl border border-slate-800 space-y-3">
                                <div className="flex justify-between items-center text-[10px] font-bold text-slate-500">
                                    <span>Estimasi Nilai:</span>
                                    <span className="text-white">Rp {(buyLot * 100 * selectedSymbol.last_price).toLocaleString()}</span>
                                </div>
                                <div className="flex justify-between items-center text-[10px] font-bold text-slate-500">
                                    <span>Estimasi Biaya (0.19%):</span>
                                    <span className="text-white">Rp {(buyLot * 100 * selectedSymbol.last_price * 0.0019).toLocaleString()}</span>
                                </div>
                                <div className="pt-3 border-t border-slate-800 flex justify-between items-center">
                                    <span className="text-xs font-black text-slate-400 uppercase tracking-tighter">Total Bayar:</span>
                                    <span className="text-lg font-black text-emerald-500 tracking-tighter">Rp {(buyLot * 100 * selectedSymbol.last_price * 1.0019).toLocaleString()}</span>
                                </div>
                            </div>

                            <button onClick={handleBuy} className="w-full py-5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-[2rem] font-black transition-all shadow-2xl shadow-emerald-900/20 uppercase tracking-widest text-sm">
                                Konfirmasi Beli
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* SELL MODAL */}
            {showSellModal && selectedSymbol && activeSession && (
                <div className="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-slate-950/90 backdrop-blur-xl animate-in fade-in duration-300">
                    <div className="max-w-md w-full bg-slate-900 border border-slate-800 rounded-[3rem] shadow-2xl overflow-hidden animate-in zoom-in-95 duration-300">
                        <div className="p-8 border-b border-slate-800 bg-red-500/5 flex items-center justify-between">
                            <div>
                                <h3 className="text-2xl font-black text-white tracking-tighter">JUAL {selectedSymbol.symbol}</h3>
                                <p className="text-[10px] text-slate-500 font-bold uppercase mt-1">Virtual Order Execution</p>
                            </div>
                            <button onClick={() => setShowSellModal(false)} className="p-3 bg-slate-800 hover:bg-slate-700 text-white rounded-full transition-all">
                                <X className="w-5 h-5" />
                            </button>
                        </div>
                        <div className="p-8 space-y-6">
                            <div className="p-6 bg-slate-950 rounded-3xl border border-slate-800 text-center">
                                <div className="text-[10px] text-slate-600 font-black uppercase mb-1">Market Price</div>
                                <div className="text-3xl font-black text-white tracking-tighter">Rp {selectedSymbol.last_price?.toLocaleString()}</div>
                            </div>

                            <div className="space-y-4">
                                <label className="block text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2">Jumlah Lot Dijual</label>
                                <div className="flex items-center gap-3">
                                    <button onClick={() => setSellLot(Math.max(1, sellLot - 1))} className="p-3 bg-slate-800 hover:bg-slate-700 text-white rounded-xl transition-all">-</button>
                                    <input
                                        type="number"
                                        value={sellLot}
                                        onChange={(e) => setSellLot(Math.max(1, parseInt(e.target.value) || 0))}
                                        className="flex-1 bg-slate-950 border border-slate-800 text-white py-3 rounded-xl outline-none focus:ring-1 focus:ring-red-500 font-black text-center text-lg"
                                    />
                                    <button onClick={() => setSellLot(sellLot + 1)} className="p-3 bg-slate-800 hover:bg-slate-700 text-white rounded-xl transition-all">+</button>
                                </div>
                            </div>

                            <button onClick={() => handleSell()} className="w-full py-5 bg-red-600 hover:bg-red-500 text-white rounded-[2rem] font-black transition-all shadow-2xl shadow-red-900/20 uppercase tracking-widest text-sm">
                                Konfirmasi Jual
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* CREATE SESSION MODAL */}
            {showCreateModal && (
                <div className="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-slate-950/90 backdrop-blur-xl animate-in fade-in duration-300">
                    <div className="max-w-sm w-full bg-slate-900 border border-slate-800 rounded-[3rem] shadow-2xl p-8 animate-in zoom-in-95 duration-300">
                        <div className="flex justify-between items-center mb-8">
                            <h3 className="text-xl font-black text-white uppercase tracking-tighter italic">New Trading Session</h3>
                            <button onClick={() => setShowCreateModal(false)} className="p-2 text-slate-500 hover:text-white"><X className="w-5 h-5" /></button>
                        </div>
                        <div className="space-y-6">
                            <div>
                                <label className="block text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2">Session Name</label>
                                <input
                                    type="text"
                                    placeholder="e.g. Bluechip Aggressive"
                                    value={newSessionName}
                                    onChange={(e) => setNewSessionName(e.target.value)}
                                    className="w-full bg-slate-950 border border-slate-800 text-white p-4 rounded-2xl outline-none focus:ring-1 focus:ring-blue-500 font-bold text-sm"
                                />
                            </div>
                            <div className="p-4 bg-blue-600/5 rounded-2xl border border-blue-600/10 flex gap-4 items-center">
                                <Info className="w-5 h-5 text-blue-400" />
                                <div className="text-[9px] text-slate-400 font-bold leading-relaxed">
                                    Setiap sesi baru akan dimulai dengan saldo virtual sebesar <span className="text-white">Rp 1 Triliun</span>.
                                </div>
                            </div>
                            <button onClick={handleCreateSession} className="w-full py-4 bg-blue-600 hover:bg-blue-500 text-white rounded-2xl font-black uppercase tracking-widest text-xs transition-all">Create Session</button>
                        </div>
                    </div>
                </div>
            )}
        </Layout>
    );
};

export default Backtest;
