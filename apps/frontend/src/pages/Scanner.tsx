import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { Radar, Target, Filter, Info, ChevronRight, Activity, TrendingUp, ShieldCheck, X, BarChart3, Loader2 } from 'lucide-react';
import axios from 'axios';
import { useAuth } from '../hooks/AuthContext';
import { PatternChart } from '../components/charts/PatternChart';

const Scanner: React.FC = () => {
    const { token } = useAuth();
    const [signals, setSignals] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedSignal, setSelectedSignal] = useState<any | null>(null);
    const [chartData, setChartData] = useState<any>(null);
    const [chartLoading, setChartLoading] = useState(false);

    useEffect(() => {
        const fetchSignals = async () => {
            try {
                setLoading(true);
                const res = await axios.get('/api/scanner/results', {
                    params: { limit: 20, latest_only: true },
                    headers: { Authorization: `Bearer ${token}` }
                });
                setSignals(res.data);
            } catch (err) { console.error(err); }
            finally { setLoading(false); }
        };
        fetchSignals();
    }, [token]);

    const openChart = async (sig: any) => {
        setSelectedSignal(sig);
        setChartLoading(true);
        try {
            // Fetch candles for the specific symbol found in scanner
            const res = await axios.get(`/api/stocks/${sig.symbol}/candles`, {
                params: { timeframe: sig.timeframe },
                headers: { Authorization: `Bearer ${token}` }
            });
            setChartData(res.data);
        } catch (err) {
            console.error("Failed to load scanner chart:", err);
        } finally {
            setChartLoading(false);
        }
    };

    return (
        <Layout>
            <div className="p-8 max-w-7xl mx-auto space-y-8 pb-20">
                <header>
                    <h1 className="text-4xl font-black text-white mb-2 tracking-tighter uppercase">CTG Scanner</h1>
                    <p className="text-slate-400 text-sm font-medium uppercase tracking-[0.2em] flex items-center gap-2">
                        Pencarian Setup Bullish & Hidden Divergence Otomatis <ShieldCheck className="w-4 h-4 text-emerald-500" />
                    </p>
                </header>

                {/* Proof Graph Section (Full Width) */}
                {selectedSignal && (
                    <div className="animate-in fade-in slide-in-from-top-4 duration-500 space-y-4">
                        <div className="flex items-center justify-between bg-slate-900 border border-slate-800 p-6 rounded-[2.5rem] shadow-2xl">
                            <div className="flex items-center gap-5">
                                <div className="p-4 bg-emerald-500/20 rounded-2xl text-emerald-500 border border-emerald-500/20 shadow-inner">
                                    <BarChart3 className="w-7 h-7" />
                                </div>
                                <div>
                                    <div className="flex items-center gap-3">
                                        <h2 className="text-3xl font-black text-white uppercase tracking-tight">{selectedSignal.symbol}</h2>
                                        <span className="px-3 py-1 bg-blue-600/20 text-blue-400 text-[10px] font-black rounded-lg border border-blue-600/20 uppercase">{selectedSignal.method}</span>
                                    </div>
                                    <p className="text-[10px] text-slate-500 font-bold uppercase mt-1 tracking-widest">Verifikasi Sinyal & Konfirmasi Struktur Market</p>
                                </div>
                            </div>
                            <button
                                onClick={() => { setSelectedSignal(null); setChartData(null); }}
                                className="p-4 bg-slate-800/50 hover:bg-red-600 text-white rounded-full transition-all border border-slate-700 hover:border-red-500 group"
                            >
                                <X className="w-6 h-6 group-hover:scale-110 transition-transform" />
                            </button>
                        </div>

                        <div className="h-[650px] shadow-2xl relative bg-slate-950 rounded-[3rem] overflow-hidden border border-slate-800 ring-1 ring-white/5">
                            {chartLoading && (
                                <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-slate-950/80 backdrop-blur-md">
                                    <Loader2 className="w-12 h-12 text-emerald-500 animate-spin mb-4" />
                                    <span className="text-[10px] font-black text-emerald-500 uppercase tracking-[0.3em]">Memuat Analisis...</span>
                                </div>
                            )}
                            <PatternChart
                                data={chartData}
                                metadata={selectedSignal}
                                interactive={true}
                            />
                        </div>
                    </div>
                )}

                <div className="bg-slate-900 border border-slate-800 rounded-[2.5rem] overflow-hidden shadow-2xl">
                    <div className="p-8 border-b border-slate-800 bg-slate-950/20 flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <div className="p-3 bg-blue-600/20 rounded-2xl text-blue-500"><Radar className="w-6 h-6 animate-pulse" /></div>
                            <div>
                                <h2 className="text-xl font-black text-white uppercase tracking-tighter">Sinyal Terdeteksi</h2>
                                <p className="text-[10px] text-slate-500 font-black uppercase mt-1">Berdasarkan data harga real-time & struktur wave</p>
                            </div>
                        </div>
                        <div className="group relative">
                            <Info className="w-5 h-5 text-slate-600 cursor-help" />
                            <div className="absolute right-0 top-8 w-64 p-3 bg-slate-800 text-[10px] text-slate-200 rounded-xl hidden group-hover:block z-50 shadow-2xl border border-slate-700">
                                Sinyal yang tampil di sini telah melewati verifikasi struktur wave 1-2-3-4-5 atau A-B-C dan konfirmasi indikator momentum.
                            </div>
                        </div>
                    </div>

                    <div className="overflow-x-auto">
                        <table className="w-full text-left">
                            <thead className="bg-slate-950/50 text-[10px] font-black uppercase text-slate-500 tracking-widest">
                                <tr>
                                    <th className="px-8 py-6">Emiten / TF</th>
                                    <th className="px-8 py-6">Strategi / Indikator</th>
                                    <th className="px-8 py-6">Status</th>
                                    <th className="px-8 py-6">Entry / SL / TP</th>
                                    <th className="px-8 py-6 text-right">Skor</th>
                                    <th className="px-8 py-6 text-center">Aksi</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-800">
                                {loading ? (
                                    <tr><td colSpan={6} className="px-8 py-32 text-center text-slate-600 font-black uppercase italic">Memindai Market...</td></tr>
                                ) : signals.length === 0 ? (
                                    <tr><td colSpan={6} className="px-8 py-32 text-center text-slate-600 font-black uppercase italic">Belum ada setup valid terdeteksi</td></tr>
                                ) : (
                                    signals.map((sig, i) => (
                                        <tr key={i} className="hover:bg-blue-600/5 transition-all group cursor-pointer" onClick={() => openChart(sig)}>
                                            <td className="px-8 py-6">
                                                <div className="font-black text-white text-xl group-hover:text-blue-400 transition-colors">{sig.symbol}</div>
                                                <div className="text-[10px] text-slate-500 font-bold uppercase mt-1">{sig.timeframe}</div>
                                            </td>
                                            <td className="px-8 py-6">
                                                <div className="text-xs text-slate-200 font-black uppercase mb-1">{sig.method}</div>
                                                <div className="text-[9px] text-blue-400 font-bold bg-blue-400/5 px-2 py-0.5 rounded inline-block">Ref: {sig.indicator_used}</div>
                                            </td>
                                            <td className="px-8 py-6">
                                                <div className="flex items-center gap-2">
                                                    <span className={`px-3 py-1 rounded-full text-[9px] font-black tracking-widest ${sig.status === 'READY' ? 'bg-emerald-500/20 text-emerald-500' : 'bg-amber-500/20 text-amber-500'}`}>
                                                        {sig.status}
                                                    </span>
                                                </div>
                                            </td>
                                            <td className="px-8 py-6">
                                                <div className="text-[10px] space-y-1">
                                                    <div className="flex gap-2"><span className="text-slate-500 w-12 font-black">ENTRY:</span><span className="text-white font-black">Rp {sig.entry_price}</span></div>
                                                    <div className="flex gap-2"><span className="text-slate-500 w-12 font-black">SL:</span><span className="text-red-400 font-black">Rp {sig.stop_loss}</span></div>
                                                    <div className="flex gap-2"><span className="text-slate-500 w-12 font-black">TP:</span><span className="text-emerald-400 font-black">Rp {sig.take_profit || sig.tp_short}</span></div>
                                                </div>
                                                {sig.metadata?.expected_entry_day && (
                                                    <div className="mt-3 pt-3 border-t border-slate-800/50">
                                                        <div className="flex items-center gap-1.5 text-[8px] font-black text-blue-500 uppercase tracking-tighter">
                                                            <Target className="w-3 h-3" />
                                                            Prediksi Entri: {new Date(sig.metadata.expected_entry_day).toLocaleDateString('id-ID', { weekday: 'long', day: 'numeric', month: 'short' })}
                                                        </div>
                                                        <div className="text-[7px] text-slate-600 font-bold uppercase mt-0.5 ml-4.5">Minggu ke-{sig.metadata.calendar_info?.week_number || '-'}</div>
                                                    </div>
                                                )}
                                            </td>
                                            <td className="px-8 py-6 text-right">
                                                <div className="text-2xl font-black text-white leading-none">+{sig.score?.toFixed(0)}</div>
                                                <div className="text-[8px] text-slate-500 font-black uppercase mt-2">Quality Score</div>
                                            </td>
                                            <td className="px-8 py-6 text-center">
                                                <button
                                                    className="px-6 py-2.5 bg-slate-800 group-hover:bg-blue-600 text-white text-[9px] font-black rounded-xl transition-all uppercase tracking-widest shadow-lg border border-slate-700 group-hover:border-blue-500"
                                                >
                                                    Cek Metode
                                                </button>
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
