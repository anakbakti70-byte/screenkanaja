import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { Radar, Target, Filter, Info, ChevronRight, Activity, TrendingUp, ShieldCheck, X, BarChart3, Loader2, BookOpen, Calculator, Zap, Clock, AlertCircle, ShoppingCart, Plus, Check } from 'lucide-react';
import axios from 'axios';
import { useAuth } from '../hooks/AuthContext';
import { PatternChart } from '../components/charts/PatternChart';

const MethodologyModal: React.FC<{ isOpen: boolean; onClose: () => void }> = ({ isOpen, onClose }) => {
    if (!isOpen) return null;

    const sections = [
        {
            title: "🧠 Inti Otak (Next Candle Direction)",
            icon: <Zap className="w-5 h-5 text-amber-400" />,
            content: [
                { label: "Prediksi Realtime", desc: "Mendeteksi bibit pergerakan pada bar TERBARU. Sinyal hanya valid jika candle konfirmasi muncul hari ini." },
                { label: "Konfirmasi Arah", desc: "Entry dilakukan SETELAH arah terkonfirmasi oleh 'cendol' (bullish solid). Fokus pada arah bar berikutnya." },
                { label: "Anti-Stale System", desc: "Sistem secara otomatis mengabaikan pola lama. Setiap scan menggunakan data market detik ini." }
            ]
        },
        {
            title: "📊 Metode & Target Fibonacci",
            icon: <Calculator className="w-5 h-5 text-blue-400" />,
            content: [
                { label: "Bullish Divergence", desc: "W5 < W3 VS Indikator Higher Low. TP: Fibo 0.6 dari W5 ke W4." },
                { label: "Double Bullish", desc: "Divergence kedua muncul karena yang pertama GAGAL capai TP 0.5. TP: Level 0.5 pertama." },
                { label: "Correction (ABC)", desc: "Buy di Zona Retracement 0.6 - 0.7. TP: Fibo Extension 1.618 dari struktur A-B-C." },
                { label: "Hidden Bullish", desc: "Higher Low C > A VS Indikator Lower Low. TP: Fibo 1.0 (100%) dari E ke D." }
            ]
        },
        {
            title: "⏱️ Life-Cycle Signal",
            icon: <Activity className="w-5 h-5 text-emerald-400" />,
            content: [
                { label: "VALID", desc: "Sinyal baru, konfirmasi lengkap, harga masih di area entry." },
                { label: "STALE", desc: "Pola benar tapi waktu entry sudah lewat atau harga sudah lari." },
                { label: "INVALID", desc: "Struktur rusak atau harga sudah menembus Stop Loss." },
                { label: "Freshness", desc: "Sinyal hanya dianggap VALID maksimal 3 candle sejak deteksi." }
            ]
        }
    ];

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-950/90 backdrop-blur-xl animate-in fade-in duration-300">
            <div className="max-w-4xl w-full bg-slate-900 border border-slate-800 rounded-[3rem] shadow-[0_0_50px_rgba(0,0,0,0.5)] overflow-hidden max-h-[90vh] flex flex-col">
                <div className="p-8 border-b border-slate-800 bg-slate-950/50 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-blue-500/20 rounded-2xl text-blue-400">
                            <BookOpen className="w-6 h-6" />
                        </div>
                        <div>
                            <h2 className="text-2xl font-black text-white uppercase tracking-tighter">CTG Methodology</h2>
                            <p className="text-[10px] text-slate-500 font-black uppercase tracking-widest mt-1 text-blue-400">Anti-Stale & Real-time Entry Engine</p>
                        </div>
                    </div>
                    <button onClick={onClose} className="p-3 bg-slate-800 hover:bg-red-600 text-white rounded-full transition-all group">
                        <X className="w-5 h-5 group-hover:scale-110" />
                    </button>
                </div>

                <div className="p-8 overflow-y-auto space-y-8 custom-scrollbar">
                    {sections.map((section, idx) => (
                        <div key={idx} className="space-y-4">
                            <div className="flex items-center gap-3">
                                {section.icon}
                                <h3 className="font-black text-white uppercase text-sm tracking-widest">{section.title}</h3>
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {section.content.map((item, i) => (
                                    <div key={i} className="bg-slate-800/30 border border-slate-800/50 p-4 rounded-2xl group hover:border-blue-500/30 transition-all">
                                        <div className="text-[10px] font-black text-blue-400 uppercase mb-1">{item.label}</div>
                                        <div className="text-[11px] text-slate-300 leading-relaxed font-medium">{item.desc}</div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

const Scanner: React.FC = () => {
    const { token } = useAuth();
    const [signals, setSignals] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedSignal, setSelectedSignal] = useState<any | null>(null);
    const [chartData, setChartData] = useState<any>(null);
    const [chartLoading, setChartLoading] = useState(false);
    const [isRulesModalOpen, setIsRulesModalOpen] = useState(false);
    const [lastSyncTime, setLastSyncTime] = useState<string>(new Date().toLocaleTimeString());

    // Auto Buy States
    const [showTradeModal, setShowTradeModal] = useState(false);
    const [selectedTradeSignal, setSelectedTradeSignal] = useState<any | null>(null);
    const [tradeLot, setTradeLot] = useState(1);
    const [sessions, setSessions] = useState<any[]>([]);
    const [activeSessionId, setActiveSessionId] = useState<number | null>(null);
    const [tradeLoading, setTradeLoading] = useState(false);

    const fetchSessions = async () => {
        try {
            const res = await axios.get('/api/backtest/sessions', {
                headers: { Authorization: `Bearer ${token}` }
            });
            setSessions(res.data || []);
            if (res.data && res.data.length > 0) {
                setActiveSessionId(res.data[0].id);
            }
        } catch (err) {
            console.error("Failed to fetch sessions:", err);
        }
    };

    const handleAutoBuy = async () => {
        if (!selectedTradeSignal || !activeSessionId) {
            alert("Silakan pilih sesi backtest terlebih dahulu.");
            return;
        }

        setTradeLoading(true);
        try {
            await axios.post('/api/backtest/order', {
                session_id: activeSessionId,
                symbol: selectedTradeSignal.symbol,
                side: 'BUY',
                quantity: tradeLot * 100,
                price: selectedTradeSignal.entry_price,
                stop_loss: selectedTradeSignal.stop_loss,
                take_profit: selectedTradeSignal.take_profit || selectedTradeSignal.tp_short
            }, {
                headers: { Authorization: `Bearer ${token}` }
            });

            alert(`Berhasil membeli ${selectedTradeSignal.symbol} ${tradeLot} lot!`);
            setShowTradeModal(false);
        } catch (err: any) {
            console.error("Trade Error:", err);
            alert(err.response?.data?.detail || "Gagal melakukan Auto Buy.");
        } finally {
            setTradeLoading(false);
        }
    };

    const fetchSignals = async (showLoading = true) => {
        try {
            if (showLoading) setLoading(true);
            const res = await axios.get('/api/scanner/results', {
                params: { limit: 50, latest_only: true },
                headers: { Authorization: `Bearer ${token}` },
                timeout: 5000
            });
            setSignals(res.data || []);
            setLastSyncTime(new Date().toLocaleTimeString());
        } catch (err) {
            console.error("Scanner Fetch Error:", err);
        } finally {
            if (showLoading) setLoading(false);
        }
    };

    useEffect(() => {
        if (!token) return;
        fetchSignals(true);
        fetchSessions();
        // Cek data terbaru setiap 1 detik
        const interval = setInterval(() => fetchSignals(false), 1000);
        return () => clearInterval(interval);
    }, [token]);

    const openChart = async (sig: any) => {
        setSelectedSignal(sig);
        setChartLoading(true);
        try {
            const res = await axios.get(`/api/stocks/${sig.symbol}/candles`, {
                params: { timeframe: sig.timeframe },
                headers: { Authorization: `Bearer ${token}` }
            });
            setChartData(res.data);
        } catch (err) {
            console.error("Failed to load chart:", err);
        } finally {
            setChartLoading(false);
        }
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'READY':
            case 'VALID': return 'bg-emerald-500/20 text-emerald-500 border-emerald-500/30';
            case 'STALE': return 'bg-amber-500/20 text-amber-500 border-amber-500/30';
            case 'INVALID': return 'bg-red-500/20 text-red-500 border-red-500/30';
            default: return 'bg-slate-500/20 text-slate-500 border-slate-500/30';
        }
    };

    return (
        <Layout>
            <MethodologyModal isOpen={isRulesModalOpen} onClose={() => setIsRulesModalOpen(false)} />

            {/* AUTO BUY MODAL */}
            {showTradeModal && selectedTradeSignal && (
                <div className="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-slate-950/90 backdrop-blur-xl animate-in fade-in duration-300">
                    <div className="max-w-md w-full bg-slate-900 border border-slate-800 rounded-[3rem] shadow-2xl overflow-hidden animate-in zoom-in-95 duration-300">
                        <div className="p-8 border-b border-slate-800 bg-emerald-500/5 flex items-center justify-between">
                            <div>
                                <h3 className="text-2xl font-black text-white tracking-tighter italic">AUTO BUY {selectedTradeSignal.symbol}</h3>
                                <p className="text-[10px] text-slate-500 font-bold uppercase mt-1 tracking-widest flex items-center gap-2">
                                    Strategy-Based Execution <Check className="w-3 h-3 text-emerald-500" />
                                </p>
                            </div>
                            <button onClick={() => setShowTradeModal(false)} className="p-3 bg-slate-800 hover:bg-slate-700 text-white rounded-full transition-all">
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        <div className="p-8 space-y-6">
                            {/* Strategy Data (Read Only) */}
                            <div className="grid grid-cols-3 gap-3">
                                <div className="p-3 bg-slate-950 border border-slate-800 rounded-2xl">
                                    <div className="text-[8px] text-slate-600 font-black uppercase mb-1">Entry</div>
                                    <div className="text-xs font-black text-white">Rp {selectedTradeSignal.entry_price?.toLocaleString()}</div>
                                </div>
                                <div className="p-3 bg-slate-950 border border-slate-800 rounded-2xl">
                                    <div className="text-[8px] text-red-500/50 font-black uppercase mb-1">Stop Loss</div>
                                    <div className="text-xs font-black text-red-400">Rp {selectedTradeSignal.stop_loss?.toLocaleString()}</div>
                                </div>
                                <div className="p-3 bg-slate-950 border border-slate-800 rounded-2xl">
                                    <div className="text-[8px] text-emerald-500/50 font-black uppercase mb-1">Target</div>
                                    <div className="text-xs font-black text-emerald-400">Rp {(selectedTradeSignal.take_profit || selectedTradeSignal.tp_short)?.toLocaleString()}</div>
                                </div>
                            </div>

                            {/* Session Selection */}
                            <div>
                                <label className="block text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2">Select Backtest Session</label>
                                <select
                                    value={activeSessionId || ''}
                                    onChange={(e) => setActiveSessionId(Number(e.target.value))}
                                    className="w-full bg-slate-950 border border-slate-800 text-white p-4 rounded-2xl outline-none focus:ring-1 focus:ring-emerald-500 font-bold text-xs appearance-none"
                                >
                                    {sessions.length === 0 ? (
                                        <option value="">No Active Sessions</option>
                                    ) : (
                                        sessions.map(s => (
                                            <option key={s.id} value={s.id}>{s.name.toUpperCase()} (Rp {(s.current_balance/1000000).toFixed(0)}M)</option>
                                        ))
                                    )}
                                </select>
                            </div>

                            {/* Lot Input */}
                            <div>
                                <label className="block text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2 text-center">Jumlah Lot</label>
                                <div className="flex items-center gap-4">
                                    <button onClick={() => setTradeLot(Math.max(1, tradeLot - 1))} className="p-4 bg-slate-800 hover:bg-slate-700 text-white rounded-2xl transition-all font-black">-</button>
                                    <input
                                        type="number"
                                        value={tradeLot}
                                        onChange={(e) => setTradeLot(Math.max(1, parseInt(e.target.value) || 0))}
                                        className="flex-1 bg-slate-950 border border-slate-800 text-white py-4 rounded-2xl outline-none focus:ring-1 focus:ring-emerald-500 font-black text-center text-xl"
                                    />
                                    <button onClick={() => setTradeLot(tradeLot + 1)} className="p-4 bg-slate-800 hover:bg-slate-700 text-white rounded-2xl transition-all font-black">+</button>
                                </div>
                            </div>

                            {/* Value Display */}
                            <div className="p-6 bg-slate-950 rounded-3xl border border-slate-800 space-y-3">
                                <div className="flex justify-between items-center text-[10px] font-bold text-slate-500">
                                    <span>Estimasi Nilai:</span>
                                    <span className="text-white">Rp {(tradeLot * 100 * selectedTradeSignal.entry_price).toLocaleString()}</span>
                                </div>
                                <div className="pt-3 border-t border-slate-800 flex justify-between items-center">
                                    <span className="text-xs font-black text-slate-400 uppercase tracking-tighter">Total Net:</span>
                                    <span className="text-lg font-black text-emerald-500 tracking-tighter">Rp {(tradeLot * 100 * selectedTradeSignal.entry_price * 1.0019).toLocaleString()}</span>
                                </div>
                            </div>

                            <button
                                onClick={handleAutoBuy}
                                disabled={tradeLoading || !activeSessionId}
                                className="w-full py-5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-[2rem] font-black transition-all shadow-2xl shadow-emerald-900/20 uppercase tracking-widest text-sm flex items-center justify-center gap-3"
                            >
                                {tradeLoading ? (
                                    <>
                                        <Loader2 className="w-5 h-5 animate-spin" />
                                        <span>Executing Order...</span>
                                    </>
                                ) : (
                                    <>
                                        <ShoppingCart className="w-5 h-5" />
                                        <span>Confirm Auto Buy</span>
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            <div className="p-8 max-w-7xl mx-auto space-y-8 pb-20">
                <header className="flex items-end justify-between">
                    <div>
                        <h1 className="text-4xl font-black text-white mb-2 tracking-tighter uppercase italic">CTG LIVE ENGINE</h1>
                        <div className="flex items-center gap-3">
                            <p className="text-slate-400 text-xs font-bold uppercase tracking-[0.3em] flex items-center gap-2">
                                Real-time Orchestrator <Zap className="w-4 h-4 text-amber-400 fill-amber-400" />
                            </p>
                            <div className="h-4 w-px bg-slate-800" />
                            <div className="flex items-center gap-2 bg-emerald-500/10 px-2 py-1 rounded-md border border-emerald-500/20">
                                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                                <span className="text-[9px] font-black text-emerald-500 uppercase tracking-widest">Synced: {lastSyncTime}</span>
                            </div>
                        </div>
                    </div>
                    <div className="flex gap-4">
                        <button onClick={fetchSignals} className="p-3 bg-slate-800 hover:bg-slate-700 text-white rounded-xl transition-all">
                            <Radar className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
                        </button>
                        <button onClick={() => setIsRulesModalOpen(true)} className="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white font-black text-[10px] uppercase tracking-widest rounded-2xl shadow-lg shadow-blue-900/20 transition-all">
                            Methodology
                        </button>
                    </div>
                </header>

                {selectedSignal && (
                    <div className="animate-in fade-in zoom-in-95 duration-300 space-y-4">
                        <div className="flex items-center justify-between bg-slate-900 border border-slate-800 p-6 rounded-[2.5rem] shadow-2xl">
                            <div className="flex items-center gap-6">
                                <div className="p-4 bg-emerald-500/10 rounded-3xl text-emerald-500 border border-emerald-500/20">
                                    <BarChart3 className="w-8 h-8" />
                                </div>
                                <div>
                                    <div className="flex items-center gap-3">
                                        <h2 className="text-4xl font-black text-white tracking-tighter">{selectedSignal.symbol}</h2>
                                        <span className={`px-4 py-1.5 rounded-xl text-[10px] font-black border ${getStatusColor(selectedSignal.status)}`}>
                                            {selectedSignal.status}
                                        </span>
                                    </div>
                                    <p className="text-[10px] text-slate-500 font-bold uppercase mt-1 tracking-widest flex items-center gap-2">
                                        <Clock className="w-3 h-3" /> Signal Age: {selectedSignal.signal_age} Candles | TF: {selectedSignal.timeframe}
                                    </p>
                                </div>
                            </div>
                            {selectedSignal.reason && (
                                <div className="hidden lg:flex items-center gap-3 px-6 py-3 bg-slate-800/50 rounded-2xl border border-slate-700 max-w-md">
                                    <AlertCircle className="w-5 h-5 text-amber-500 shrink-0" />
                                    <p className="text-[11px] text-slate-300 font-medium leading-relaxed">{selectedSignal.reason}</p>
                                </div>
                            )}
                            <button onClick={() => { setSelectedSignal(null); setChartData(null); }} className="p-4 bg-slate-800 hover:bg-red-600 text-white rounded-full transition-all">
                                <X className="w-6 h-6" />
                            </button>
                        </div>

                        <div className="h-[600px] shadow-2xl relative bg-slate-950 rounded-[3rem] overflow-hidden border border-slate-800">
                            {chartLoading && (
                                <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-slate-950/80 backdrop-blur-md">
                                    <Loader2 className="w-12 h-12 text-blue-500 animate-spin mb-4" />
                                    <span className="text-[10px] font-black text-blue-500 uppercase tracking-[0.3em]">Processing Visual Proof...</span>
                                </div>
                            )}
                            <PatternChart data={chartData} metadata={selectedSignal} interactive={true} />
                        </div>
                    </div>
                )}

                <div className="bg-slate-900 border border-slate-800 rounded-[2.5rem] overflow-hidden shadow-2xl">
                    <div className="overflow-x-auto">
                        <table className="w-full text-left">
                            <thead className="bg-slate-950/50 text-[10px] font-black uppercase text-slate-500 tracking-widest">
                                <tr>
                                    <th className="px-8 py-6">Asset</th>
                                    <th className="px-8 py-6">Method / Indicator</th>
                                    <th className="px-8 py-6">Life-Cycle Status</th>
                                    <th className="px-8 py-6">Levels (IDR)</th>
                                    <th className="px-8 py-6 text-right">RR Score</th>
                                    <th className="px-8 py-6 text-center">Verification</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-800">
                                {loading ? (
                                    <tr><td colSpan={6} className="px-8 py-32 text-center text-slate-600 font-black uppercase italic animate-pulse">Scanning Global Market...</td></tr>
                                ) : signals.length === 0 ? (
                                    <tr><td colSpan={6} className="px-8 py-32 text-center">
                                        <div className="flex flex-col items-center gap-4">
                                            <div className="p-6 bg-slate-800/50 rounded-full text-slate-600">
                                                <Radar className="w-12 h-12" />
                                            </div>
                                            <div>
                                                <h3 className="text-xl font-black text-slate-400 uppercase tracking-tighter">Tidak Ada Setup Aktif</h3>
                                                <p className="text-[10px] text-slate-500 font-bold uppercase mt-1">Sistem hanya menampilkan sinyal berstatus READY & VALID.</p>
                                            </div>
                                        </div>
                                    </td></tr>
                                ) : (
                                    signals.map((sig, i) => (
                                        <tr key={i} className={`hover:bg-blue-600/5 transition-all group cursor-pointer ${sig.status === 'VALID' ? 'bg-emerald-500/5' : ''}`} onClick={() => openChart(sig)}>
                                            <td className="px-8 py-6">
                                                <div className="font-black text-white text-2xl tracking-tighter group-hover:text-blue-400 transition-colors">{sig.symbol}</div>
                                                <div className="text-[10px] text-slate-500 font-bold uppercase mt-1">{sig.timeframe}</div>
                                            </td>
                                            <td className="px-8 py-6">
                                                <div className="text-xs text-slate-200 font-black uppercase mb-1">{sig.method}</div>
                                                <div className="text-[9px] text-cyan-400 font-bold bg-cyan-400/5 px-2 py-0.5 rounded inline-block">Ref: {sig.indicator_used}</div>
                                            </td>
                                            <td className="px-8 py-6">
                                                <div className="space-y-2">
                                                    <span className={`px-3 py-1 rounded-lg text-[9px] font-black border ${getStatusColor(sig.status)}`}>
                                                        {sig.status}
                                                    </span>
                                                    <div className="flex items-center gap-1.5 text-[9px] text-slate-500 font-bold uppercase">
                                                        <Clock className="w-3 h-3" /> {sig.signal_age} Bars Old
                                                    </div>
                                                </div>
                                            </td>
                                            <td className="px-8 py-6">
                                                <div className="text-[10px] space-y-1.5 font-bold">
                                                    <div className="flex items-center gap-2"><span className="text-slate-500 w-14 uppercase">Entry</span><span className="text-white">Rp {sig.entry_price?.toLocaleString()}</span></div>
                                                    <div className="flex items-center gap-2"><span className="text-slate-500 w-14 uppercase">Stop</span><span className="text-red-400">Rp {sig.stop_loss?.toLocaleString()}</span></div>
                                                    <div className="flex items-center gap-2"><span className="text-slate-500 w-14 uppercase">Target</span><span className="text-emerald-400">Rp {(sig.take_profit || sig.tp_short)?.toLocaleString()}</span></div>
                                                </div>
                                            </td>
                                            <td className="px-8 py-6 text-right">
                                                <div className="flex flex-col items-end">
                                                    <div className="text-2xl font-black text-white">x{sig.risk_reward?.toFixed(1)}</div>
                                                    <div className="text-[8px] text-slate-500 font-black uppercase mt-1">Risk/Reward</div>
                                                </div>
                                            </td>
                                            <td className="px-8 py-6 text-center">
                                                <div className="flex gap-2 justify-center">
                                                    <button
                                                        onClick={(e) => { e.stopPropagation(); window.location.href = `/backtest?symbol=${sig.symbol}`; }}
                                                        className="px-4 py-2.5 bg-blue-600/10 text-blue-400 text-[9px] font-black rounded-xl transition-all uppercase tracking-widest border border-blue-600/20 hover:bg-blue-600 hover:text-white"
                                                    >
                                                        Trade
                                                    </button>
                                                    <button
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            setSelectedTradeSignal(sig);
                                                            setTradeLot(1);
                                                            setShowTradeModal(true);
                                                        }}
                                                        className="px-4 py-2.5 bg-emerald-600/10 text-emerald-500 text-[9px] font-black rounded-xl transition-all uppercase tracking-widest border border-emerald-600/20 hover:bg-emerald-600 hover:text-white flex items-center gap-1.5"
                                                    >
                                                        <ShoppingCart className="w-3 h-3" /> Auto Buy
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </Layout>
    );
};

export default Scanner;
