import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { Play, Activity, CheckCircle2, TrendingUp, BarChart, Wallet, Plus, Loader2, Search, Target, ShieldAlert, X, Zap, Info, Settings2, Briefcase, TrendingDown } from 'lucide-react';
import axios from 'axios';
import { useAuth } from '../hooks/AuthContext';
import { PatternChart } from '../components/charts/PatternChart';
import { EquityCurve } from '../components/backtest/EquityCurve';

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

    useEffect(() => {
        if (user) setBalance(user.balance);
    }, [user]);

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
                        <h1 className="text-4xl font-black text-white mb-2 tracking-tighter uppercase">Simulator Kuantitatif</h1>
                        <p className="text-slate-400 text-sm font-medium uppercase tracking-widest flex items-center gap-2">
                            Ajaib-Style Position Sizing & Real-time Data <ShieldAlert className="w-4 h-4 text-emerald-500" />
                        </p>
                    </div>

                    <div className="flex flex-wrap gap-4">
                         <div className="flex items-center gap-4 bg-slate-900 border border-slate-800 p-4 rounded-[2rem] shadow-xl">
                            <div className="p-3 bg-blue-600/20 rounded-2xl text-blue-500"><Wallet className="w-5 h-5" /></div>
                            <div>
                                <div className="text-[9px] text-slate-500 font-black uppercase tracking-tighter">Saldo Kas</div>
                                <div className="text-xl font-black text-white leading-none">Rp {(results?.cash_balance ?? balance)?.toLocaleString()}</div>
                            </div>
                        </div>
                        {results && (
                            <>
                                <div className="flex items-center gap-4 bg-slate-900 border border-slate-800 p-4 rounded-[2rem] shadow-xl">
                                    <div className="p-3 bg-amber-600/20 rounded-2xl text-amber-500"><Briefcase className="w-5 h-5" /></div>
                                    <div>
                                        <div className="text-[9px] text-slate-500 font-black uppercase tracking-tighter">Posisi Terbuka</div>
                                        <div className="text-xl font-black text-white leading-none">Rp {(results.total_equity - results.cash_balance)?.toLocaleString()}</div>
                                    </div>
                                </div>
                                <div className="flex items-center gap-4 bg-slate-900 border border-slate-800 p-4 rounded-[2rem] shadow-xl border-t-2 border-t-emerald-500/30">
                                    <div className="p-3 bg-emerald-600/20 rounded-2xl text-emerald-500"><TrendingUp className="w-5 h-5" /></div>
                                    <div>
                                        <div className="text-[9px] text-slate-500 font-black uppercase tracking-tighter">Total Ekuitas</div>
                                        <div className="text-xl font-black text-white leading-none">Rp {results.total_equity?.toLocaleString()}</div>
                                    </div>
                                </div>
                            </>
                        )}
                    </div>
                </header>

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                    <div className="lg:col-span-3 space-y-6">
                        <div className="bg-slate-900 border border-slate-800 rounded-[2.5rem] p-8 shadow-2xl space-y-8 sticky top-8">
                            <h2 className="text-lg font-black text-white flex items-center gap-2 uppercase"><Settings2 className="w-5 h-5 text-blue-500" /> Konfigurasi</h2>

                            <div className="space-y-6">
                                <div className="relative">
                                    <label className="block text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2">Emiten</label>
                                    <div className="relative">
                                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                                        <input type="text" placeholder={symbol || "Cari Kode..."} value={searchQuery} onFocus={() => setShowDropdown(true)} onChange={(e) => setSearchQuery(e.target.value)} className="w-full bg-slate-950 border border-slate-800 text-white pl-10 pr-4 py-3 rounded-xl outline-none focus:ring-2 focus:ring-blue-500 font-bold text-sm" />
                                        {showDropdown && (
                                            <div className="absolute top-full left-0 right-0 mt-2 bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden z-[100] shadow-2xl max-h-60 overflow-y-auto">
                                                {availableSymbols.map((s, idx) => (
                                                    <div key={idx} onClick={() => { setSymbol(s.symbol); setShowDropdown(false); setSearchQuery(''); }} className="p-4 hover:bg-blue-600 transition-all cursor-pointer flex justify-between border-b border-slate-800 last:border-0">
                                                        <span className="font-black text-white text-xs">{s.symbol}</span>
                                                        <span className="text-[10px] text-slate-400">Rp {s.last_price}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2">Timeframe</label>
                                        <select value={timeframe} onChange={(e) => setTimeframe(e.target.value)} className="w-full bg-slate-950 border border-slate-800 text-white p-3 rounded-xl outline-none font-bold text-xs">
                                            <option value="1d">Daily</option><option value="1h">1 Hour</option><option value="15m">15 Min</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label className="block text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2">Risiko %</label>
                                        <input type="number" value={riskPerTrade} onChange={(e) => setRiskPerTrade(Number(e.target.value))} className="w-full bg-slate-950 border border-slate-800 text-white p-3 rounded-xl font-bold text-xs" />
                                    </div>
                                </div>

                                <div className="p-4 bg-slate-950/50 border border-slate-800 rounded-2xl space-y-4">
                                    <div className="text-slate-500 font-black uppercase text-[9px] tracking-widest">Biaya & Slippage</div>
                                    <div className="grid grid-cols-3 gap-2">
                                        <div className="space-y-1">
                                            <span className="text-[8px] text-slate-600 uppercase font-bold">Buy %</span>
                                            <input type="number" value={buyFee} onChange={(e) => setBuyFee(Number(e.target.value))} className="w-full bg-slate-900 border border-slate-800 text-[10px] text-white p-2 rounded-lg font-bold" />
                                        </div>
                                        <div className="space-y-1">
                                            <span className="text-[8px] text-slate-600 uppercase font-bold">Sell %</span>
                                            <input type="number" value={sellFee} onChange={(e) => setSellFee(Number(e.target.value))} className="w-full bg-slate-900 border border-slate-800 text-[10px] text-white p-2 rounded-lg font-bold" />
                                        </div>
                                        <div className="space-y-1">
                                            <span className="text-[8px] text-slate-600 uppercase font-bold">Slip %</span>
                                            <input type="number" value={slippage} onChange={(e) => setSlippage(Number(e.target.value))} className="w-full bg-slate-900 border border-slate-800 text-[10px] text-white p-2 rounded-lg font-bold" />
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <button onClick={runSimulation} disabled={isRunning} className="w-full py-4 bg-blue-600 hover:bg-blue-700 text-white rounded-2xl font-black transition-all shadow-xl disabled:opacity-50 flex items-center justify-center gap-2 uppercase tracking-tighter text-sm">
                                {isRunning ? <Loader2 className="animate-spin w-4 h-4" /> : <Play className="w-4 h-4 fill-current" />}
                                {isRunning ? 'Simulasi...' : 'Jalankan Simulasi'}
                            </button>
                        </div>
                    </div>

                    <div className="lg:col-span-9 space-y-8">
                        {results ? (
                            <div className="animate-in fade-in slide-in-from-bottom-8 duration-700 space-y-8">
                                {/* Interactive Price Chart */}
                                <div className="bg-slate-900 border border-slate-800 rounded-[2.5rem] overflow-hidden shadow-2xl relative min-h-[500px]">
                                    <div className="absolute top-6 left-8 z-10">
                                        <h3 className="text-white font-black text-lg uppercase tracking-tighter">Price & Signals (Interactive)</h3>
                                    </div>
                                    <div className="h-full w-full">
                                        <PatternChart data={results} metadata={results} interactive={true} />
                                    </div>
                                </div>

                                {/* Metrics Summary */}
                                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                                    {[
                                        { label: 'Net Profit', value: `Rp ${results.metrics.net_profit?.toLocaleString()}`, color: results.metrics.net_profit >= 0 ? 'text-emerald-500' : 'text-red-500' },
                                        { label: 'Win Rate', value: results.metrics.win_rate, color: 'text-blue-500' },
                                        { label: 'Expectancy', value: `${results.metrics.expectancy} R`, color: results.metrics.expectancy >= 0.2 ? 'text-emerald-400' : (results.metrics.expectancy > 0 ? 'text-purple-400' : 'text-red-400') },
                                        {
                                            // FIX: profit_factor bisa berupa string "∞" (tak ada loss sama sekali).
                                            // Komparasi numerik langsung ("∞" >= 1.5) di JS selalu bernilai false
                                            // karena "∞" -> NaN, jadi warnanya salah (harusnya hijau paling kuat).
                                            label: 'Profit Factor',
                                            value: results.metrics.profit_factor,
                                            color: results.metrics.profit_factor === '∞'
                                                ? 'text-emerald-500'
                                                : (results.metrics.profit_factor >= 1.5 ? 'text-emerald-500' : (results.metrics.profit_factor >= 1 ? 'text-amber-500' : 'text-red-400'))
                                        },
                                        { label: 'Max DD', value: results.metrics.max_drawdown, color: 'text-red-400' },
                                        { label: 'Total Trades', value: results.metrics.total_trades, color: 'text-slate-400' },
                                    ].map((stat, i) => (
                                        <div key={i} className="bg-slate-900 border border-slate-800 p-5 rounded-[1.5rem] relative shadow-lg">
                                            <div className={`text-lg font-black ${stat.color} mb-1 tracking-tighter`}>{stat.value}</div>
                                            <div className="text-[8px] text-slate-500 font-black uppercase tracking-widest">{stat.label}</div>
                                        </div>
                                    ))}
                                </div>

                                {/* §8c.6/§8c.7: Peringatan signifikansi statistik -- jangan biarkan
                                    user percaya angka expectancy/win-rate kalau sample terlalu kecil */}
                                {results.metrics.sample_size_warning && (
                                    <div className="flex items-start gap-3 bg-amber-500/10 border border-amber-500/30 rounded-2xl p-5">
                                        <ShieldAlert className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
                                        <div>
                                            <div className="text-amber-400 font-black text-xs uppercase tracking-tighter mb-1">Sample Size Terlalu Kecil (&lt; 30 Trade)</div>
                                            <div className="text-amber-200/70 text-[11px] leading-relaxed">
                                                Hasil dengan {results.metrics.total_trades} trade belum signifikan secara statistik (§8c.6).
                                                Jangan dijadikan dasar keputusan modal riil -- perbanyak rentang data atau universe emiten dulu.
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {/* Breakdown metrik per strategi (§8c.6 -- wajib dipisah, jangan digabung rata) */}
                                {results.metrics_by_strategy && Object.keys(results.metrics_by_strategy).length > 0 && (
                                    <div className="bg-slate-900 border border-slate-800 rounded-[2.5rem] p-8 shadow-2xl">
                                        <h3 className="text-white font-black text-lg uppercase tracking-tighter mb-6">Breakdown Per Strategi</h3>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                            {Object.entries(results.metrics_by_strategy).map(([strategyName, m]: [string, any]) => (
                                                <div key={strategyName} className="bg-slate-950/50 border border-slate-800 rounded-2xl p-5">
                                                    <div className="flex items-center justify-between mb-3">
                                                        <span className="text-xs font-black text-blue-400 uppercase">{strategyName}</span>
                                                        {m.sample_size_warning && (
                                                            <span className="text-[8px] font-black text-amber-500 uppercase bg-amber-500/10 px-2 py-1 rounded">n={m.total_trades} kecil</span>
                                                        )}
                                                    </div>
                                                    <div className="grid grid-cols-3 gap-2 text-center">
                                                        <div>
                                                            <div className="text-sm font-black text-white">{m.win_rate}</div>
                                                            <div className="text-[8px] text-slate-500 uppercase font-bold">Win Rate</div>
                                                        </div>
                                                        <div>
                                                            <div className={`text-sm font-black ${m.expectancy >= 0.2 ? 'text-emerald-400' : (m.expectancy > 0 ? 'text-purple-400' : 'text-red-400')}`}>{m.expectancy} R</div>
                                                            <div className="text-[8px] text-slate-500 uppercase font-bold">Expectancy</div>
                                                        </div>
                                                        <div>
                                                            <div className="text-sm font-black text-slate-300">{m.total_trades}</div>
                                                            <div className="text-[8px] text-slate-500 uppercase font-bold">Trades</div>
                                                        </div>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {/* Equity Curve */}
                                <div className="bg-slate-900 border border-slate-800 rounded-[2.5rem] p-8 shadow-2xl">
                                    <h3 className="text-white font-black text-lg uppercase tracking-tighter mb-6">Equity Growth Curve</h3>
                                    <EquityCurve data={results.equity_curve} />
                                </div>

                                {/* Detailed Transaction History */}
                                <div className="bg-slate-900 border border-slate-800 rounded-[2.5rem] overflow-hidden shadow-2xl">
                                    <div className="p-8 border-b border-slate-800 bg-slate-950/20 flex justify-between items-center">
                                        <h3 className="text-white font-black text-lg uppercase tracking-tighter">Riwayat Transaksi (Broker Standard)</h3>
                                        <div className="flex flex-wrap gap-2 justify-end">
                                            <div className="px-3 py-1 bg-blue-600/10 rounded-lg border border-blue-500/20 text-[10px] text-blue-400 font-black uppercase">Modal Kurang: {results.metrics.skipped_capital}</div>
                                            <div className="px-3 py-1 bg-purple-600/10 rounded-lg border border-purple-500/20 text-[10px] text-purple-400 font-black uppercase">Risiko Terlalu Kecil: {results.metrics.skipped_risk_too_small ?? 0}</div>
                                            <div className="px-3 py-1 bg-orange-600/10 rounded-lg border border-orange-500/20 text-[10px] text-orange-400 font-black uppercase">Setup Invalid: {results.metrics.skipped_invalid_setup ?? 0}</div>
                                            <div className="px-3 py-1 bg-red-600/10 rounded-lg border border-red-500/20 text-[10px] text-red-400 font-black uppercase">Unfilled ARA: {results.metrics.unfilled_ara}</div>
                                            <div className="px-3 py-1 bg-red-600/10 rounded-lg border border-red-500/20 text-[10px] text-red-400 font-black uppercase">Blocked ARB: {results.metrics.blocked_arb_exits ?? 0}</div>
                                        </div>
                                    </div>
                                    <div className="overflow-x-auto">
                                        <table className="w-full text-left border-collapse">
                                            <thead>
                                                <tr className="text-slate-500 text-[9px] uppercase tracking-widest bg-slate-950/50 font-black">
                                                    <th className="px-6 py-4 border-b border-slate-800">Tanggal</th>
                                                    <th className="px-6 py-4 border-b border-slate-800">Strategi</th>
                                                    <th className="px-6 py-4 border-b border-slate-800 text-right">Lot</th>
                                                    <th className="px-6 py-4 border-b border-slate-800 text-right">In / Out</th>
                                                    <th className="px-6 py-4 border-b border-slate-800 text-right">Modal (Fee)</th>
                                                    <th className="px-6 py-4 border-b border-slate-800 text-right">P&L (Rp / % / R)</th>
                                                    <th className="px-6 py-4 border-b border-slate-800 text-center">Alasan / Saldo</th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-slate-800">
                                                {results.trades.map((trade: any, i: number) => (
                                                    <tr key={i} className="hover:bg-slate-800/30 transition-all">
                                                        <td className="px-6 py-4">
                                                            <div className="text-[10px] text-white font-black">{new Date(trade.entry_ts).toLocaleDateString('id-ID', {day:'2-digit', month:'short'})}</div>
                                                            <div className="text-[9px] text-slate-500 font-bold">{new Date(trade.exit_ts).toLocaleDateString('id-ID', {day:'2-digit', month:'short'})}</div>
                                                        </td>
                                                        <td className="px-6 py-4">
                                                            <div className="text-[9px] text-blue-400 font-black uppercase">{trade.strategy.split(' ')[0]}</div>
                                                        </td>
                                                        <td className="px-6 py-4 text-right">
                                                            <div className="text-[11px] text-white font-black">{trade.lots}</div>
                                                            <div className="text-[8px] text-slate-500 font-bold">{(trade.lots * 100).toLocaleString()} lbr</div>
                                                        </td>
                                                        <td className="px-6 py-4 text-right">
                                                            <div className="text-[10px] text-slate-300 font-black">{trade.entry_price.toLocaleString()}</div>
                                                            <div className="text-[10px] text-slate-400 font-black">{trade.exit_price.toLocaleString()}</div>
                                                        </td>
                                                        <td className="px-6 py-4 text-right">
                                                            <div className="text-[10px] text-slate-300 font-bold">{(trade.capital_used).toLocaleString()}</div>
                                                            <div className="text-[8px] text-slate-500">{(trade.buy_fee + trade.sell_fee).toLocaleString()} fee</div>
                                                        </td>
                                                        <td className="px-6 py-4 text-right">
                                                            <div className={`text-[11px] font-black ${trade.pnl >= 0 ? 'text-emerald-500' : 'text-red-500'}`}>
                                                                {trade.pnl >= 0 ? '+' : ''}{trade.pnl.toLocaleString()}
                                                            </div>
                                                            <div className="flex justify-end gap-2 text-[9px] font-bold">
                                                                <span className={trade.pnl >= 0 ? 'text-emerald-600' : 'text-red-600'}>{trade.pnl_pct.toFixed(2)}%</span>
                                                                <span className="text-slate-500">{trade.r_multiple.toFixed(2)} R</span>
                                                            </div>
                                                        </td>
                                                        <td className="px-6 py-4">
                                                            <div className="flex flex-col items-center gap-1">
                                                                <div className={`text-[8px] font-black px-1.5 py-0.5 rounded uppercase ${trade.reason === 'TAKE PROFIT' ? 'bg-emerald-500/10 text-emerald-500' : 'bg-red-500/10 text-red-500'}`}>
                                                                    {trade.reason}
                                                                </div>
                                                                <div className="text-[9px] text-slate-400 font-bold">Rp {trade.balance_after.toLocaleString()}</div>
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