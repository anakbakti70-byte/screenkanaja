import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { Play, Activity, CheckCircle2, TrendingUp, BarChart, Wallet, Plus, Loader2, Search, Target, ShieldAlert, X, Zap, Info, Settings2 } from 'lucide-react';
import axios from 'axios';
import { useAuth } from '../hooks/AuthContext';
import { PatternChart } from '../components/charts/PatternChart';

const Backtest: React.FC = () => {
    const { token, user, updateUser } = useAuth();
    const [isRunning, setIsRunning] = useState(false);
    const [symbol, setSymbol] = useState('GOTO');
    const [availableSymbols, setAvailableSymbols] = useState<any[]>([]);
    const [timeframe, setTimeframe] = useState('1d');
    const [riskPerTrade, setRiskPerTrade] = useState(1);
    const [buyFee, setBuyFee] = useState(0.19);
    const [sellFee, setSellFee] = useState(0.29);
    const [slippage, setSlippage] = useState(0.1);
    const [results, setResults] = useState<any>(null);
    const [balance, setBalance] = useState(0);
    const [searchQuery, setSearchQuery] = useState('');
    const [showDropdown, setShowDropdown] = useState(false);
    const [suggestedStocks, setSuggestedStocks] = useState<any[]>([]);

    useEffect(() => {
        if (user) setBalance(user.balance);
        fetchSuggestions();
    }, [user]);

    const fetchSuggestions = async () => {
        try {
            const res = await axios.get('/api/scanner/results', {
                params: { limit: 12, latest_only: true },
                headers: { Authorization: `Bearer ${token}` }
            });
            setSuggestedStocks(res.data);
        } catch (err) { console.error(err); }
    };

    useEffect(() => {
        const delayDebounceFn = setTimeout(() => {
            if (searchQuery || showDropdown) fetchSymbols(searchQuery);
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
        } catch (err) { console.error(err); }
    };

    const runSimulation = async () => {
        setIsRunning(true);
        setResults(null);
        try {
            const res = await axios.post('/api/backtest/run', {
                symbol, timeframe, initial_capital: balance, risk_per_trade: riskPerTrade,
                buy_fee: buyFee / 100, sell_fee: sellFee / 100, slippage_pct: slippage / 100
            }, { headers: { Authorization: `Bearer ${token}` } });
            setResults(res.data);
        } catch (err) { alert("Simulasi gagal."); }
        finally { setIsRunning(false); }
    };

    return (
        <Layout>
            <div className="p-8 max-w-7xl mx-auto space-y-8 pb-20">
                <header className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                    <div>
                        <h1 className="text-4xl font-black text-white mb-2 tracking-tighter">Simulator Kuantitatif</h1>
                        <p className="text-slate-400 text-sm font-medium uppercase tracking-widest flex items-center gap-2">
                            Standard Backtest Saham Indonesia <ShieldAlert className="w-4 h-4 text-emerald-500" />
                        </p>
                    </div>

                    <div className="flex items-center gap-4 bg-slate-900 border border-slate-800 p-5 rounded-[2.5rem] shadow-2xl">
                        <div className="p-3 bg-blue-600/20 rounded-2xl text-blue-500"><Wallet className="w-6 h-6" /></div>
                        <div>
                            <div className="flex items-center gap-1.5">
                                <div className="text-[10px] text-slate-500 font-black uppercase tracking-tighter">Modal Trading</div>
                                <div className="group relative">
                                    <Info className="w-3 h-3 text-slate-600 cursor-help" />
                                    <div className="absolute left-0 top-4 w-48 p-2 bg-slate-800 text-[9px] text-slate-300 rounded-lg hidden group-hover:block z-50 border border-slate-700">
                                        Kapital yang digunakan untuk menghitung ukuran lot dan risiko per transaksi.
                                    </div>
                                </div>
                            </div>
                            <div className="text-2xl font-black text-white leading-none">Rp {balance?.toLocaleString()}</div>
                        </div>
                    </div>
                </header>

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                    <div className="lg:col-span-4 space-y-6">
                        <div className="bg-slate-900 border border-slate-800 rounded-[2.5rem] p-8 shadow-2xl space-y-8 sticky top-8">
                            <h2 className="text-xl font-black text-white mb-6 flex items-center gap-2"><Settings2 className="w-6 h-6 text-blue-500" /> Konfigurasi</h2>

                            <div className="space-y-6">
                                <div className="relative">
                                    <label className="block text-xs font-black text-slate-500 uppercase tracking-widest mb-3 flex items-center gap-1">
                                        Pilih Emiten <Info className="w-3 h-3 cursor-help text-slate-600" title="Pilih kode saham untuk diuji kinerjanya secara historis" />
                                    </label>
                                    <div className="relative group">
                                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                                        <input type="text" placeholder={symbol ? `Terpilih: ${symbol}` : "Cari Kode..."} value={searchQuery} onFocus={() => setShowDropdown(true)} onChange={(e) => setSearchQuery(e.target.value)} className="w-full bg-slate-950 border border-slate-800 text-white pl-12 pr-4 py-4 rounded-2xl outline-none focus:ring-2 focus:ring-blue-500 font-bold" />
                                        {showDropdown && (
                                            <div className="absolute top-full left-0 right-0 mt-2 bg-slate-900 border border-slate-800 rounded-3xl overflow-hidden z-50 shadow-2xl max-h-80 overflow-y-auto backdrop-blur-xl">
                                                {availableSymbols.map((s, idx) => (
                                                    <div key={idx} onClick={() => { setSymbol(s.symbol); setShowDropdown(false); setSearchQuery(''); }} className="p-5 hover:bg-blue-600 transition-all cursor-pointer flex justify-between border-b border-slate-800 last:border-0">
                                                        <span className="font-black text-white">{s.symbol}</span>
                                                        <span className="text-xs text-slate-400">Rp {s.last_price}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-xs font-black text-slate-500 uppercase tracking-widest mb-3 flex items-center gap-1">
                                            Timeframe <Info className="w-3 h-3 cursor-help text-slate-600" title="Daily untuk investasi, 1 Jam untuk swing, 15 Menit untuk intraday" />
                                        </label>
                                        <select value={timeframe} onChange={(e) => setTimeframe(e.target.value)} className="w-full bg-slate-950 border border-slate-800 text-white p-4 rounded-2xl outline-none font-bold">
                                            <option value="1d">Daily</option><option value="1h">1 Hour</option><option value="15m">15 Min</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label className="block text-xs font-black text-slate-500 uppercase tracking-widest mb-3 flex items-center gap-1">
                                            Risiko % <Info className="w-3 h-3 cursor-help text-slate-600" title="Batas modal yang siap hilang per transaksi (Stop Loss)" />
                                        </label>
                                        <input type="number" value={riskPerTrade} onChange={(e) => setRiskPerTrade(Number(e.target.value))} className="w-full bg-slate-950 border border-slate-800 text-white p-4 rounded-2xl font-bold" />
                                    </div>
                                </div>

                                <div className="p-6 bg-slate-950/50 border border-slate-800 rounded-3xl space-y-4">
                                    <div className="flex items-center gap-2 text-slate-500 font-black uppercase text-[10px]">
                                        Biaya & Slippage <Info className="w-3 h-3 cursor-help" title="Input biaya bursa asli agar hasil profit lebih realistis" />
                                    </div>
                                    <div className="grid grid-cols-3 gap-2">
                                        <input type="number" value={buyFee} onChange={(e) => setBuyFee(Number(e.target.value))} className="bg-slate-900 border border-slate-800 text-[10px] text-white p-2 rounded-lg" />
                                        <input type="number" value={sellFee} onChange={(e) => setSellFee(Number(e.target.value))} className="bg-slate-900 border border-slate-800 text-[10px] text-white p-2 rounded-lg" />
                                        <input type="number" value={slippage} onChange={(e) => setSlippage(Number(e.target.value))} className="bg-slate-900 border border-slate-800 text-[10px] text-white p-2 rounded-lg" />
                                    </div>
                                </div>
                            </div>

                            <button onClick={runSimulation} disabled={isRunning} className="w-full py-5 bg-blue-600 hover:bg-blue-700 text-white rounded-3xl font-black transition-all shadow-xl disabled:opacity-50 flex items-center justify-center gap-2">
                                {isRunning ? <Loader2 className="animate-spin w-5 h-5" /> : <Play className="w-5 h-5 fill-current" />}
                                {isRunning ? 'SIMULASI BERJALAN...' : 'JALANKAN SIMULASI'}
                            </button>
                        </div>
                    </div>

                    <div className="lg:col-span-8 space-y-8">
                        {results ? (
                            <div className="animate-in fade-in slide-in-from-bottom-8 duration-700 space-y-8">
                                <div className="bg-slate-900 border border-slate-800 rounded-[3rem] overflow-hidden shadow-2xl relative min-h-[500px]">
                                    <div className="h-full w-full"><PatternChart data={results.candles} trades={results.trades} /></div>
                                </div>

                                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                                    {[
                                        { label: 'Net Profit', value: `Rp ${results.metrics.net_profit?.toLocaleString()}`, color: 'text-emerald-500', info: 'Keuntungan bersih setelah dikurangi semua biaya.' },
                                        { label: 'Win Rate', value: results.metrics.win_rate, color: 'text-blue-500', info: 'Persentase transaksi yang berakhir menguntungkan.' },
                                        { label: 'Expectancy', value: results.metrics.expectancy, color: 'text-purple-400', info: 'Rata-rata hasil (R) per transaksi. Angka positif berarti sistem profit.' },
                                        { label: 'Profit Factor', value: results.metrics.profit_factor, color: 'text-amber-500', info: 'Rasio antara total keuntungan dibanding total kerugian.' },
                                        { label: 'Max DD', value: results.metrics.max_drawdown, color: 'text-red-400', info: 'Penurunan modal terbesar dari titik puncak ke lembah.' },
                                        { label: 'Trades', value: results.metrics.total_trades, color: 'text-slate-400', info: 'Total jumlah transaksi yang terjadi selama periode uji.' },
                                    ].map((stat, i) => (
                                        <div key={i} className="bg-slate-900 border border-slate-800 p-5 rounded-[2rem] relative group">
                                            <div className="absolute top-4 right-4"><Info className="w-3 h-3 text-slate-700 cursor-help" title={stat.info} /></div>
                                            <div className={`text-xl font-black ${stat.color} mb-1`}>{stat.value}</div>
                                            <div className="text-[8px] text-slate-500 font-black uppercase tracking-widest">{stat.label}</div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ) : (
                            <div className="flex flex-col items-center justify-center h-full min-h-[600px] bg-slate-900/50 border border-dashed border-slate-800 rounded-[4rem] opacity-40">
                                <Activity className="w-16 h-16 text-slate-600 mb-4" />
                                <h3 className="text-2xl font-black text-white uppercase tracking-tighter">Hasil Simulasi Muncul Di Sini</h3>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </Layout>
    );
};

export default Backtest;
