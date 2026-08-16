import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { Search, Zap, TrendingUp, Calendar, Filter, X, Loader2, ArrowDownCircle, Info } from 'lucide-react';
import axios from 'axios';
import { useAuth } from '../hooks/AuthContext';
import { PatternChart } from '../components/charts/PatternChart';

const StockList: React.FC = () => {
    const { token } = useAuth();
    const [allStocks, setAllStocks] = useState<any[]>([]);
    const [recentIpos, setRecentIpos] = useState<any[]>([]);
    const [topLosers, setTopLosers] = useState<any[]>([]);
    const [topPerformers, setTopPerformers] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
    const [chartData, setChartData] = useState<any>(null);
    const [chartLoading, setChartLoading] = useState(false);

    const fetchData = async () => {
        try {
            setLoading(true);
            const stocksReq = axios.get('/api/stocks/', { headers: { Authorization: `Bearer ${token}` } }).then(res => setAllStocks(res.data));
            const ipoReq = axios.get('/api/stocks/ipo', { headers: { Authorization: `Bearer ${token}` } }).then(res => setRecentIpos(res.data));
            const losersReq = axios.get('/api/stocks/losers', { headers: { Authorization: `Bearer ${token}` } }).then(res => setTopLosers(res.data));
            const topReq = axios.get('/api/scanner/results', {
                params: { limit: 5, sort_by: 'score', latest_only: true },
                headers: { Authorization: `Bearer ${token}` }
            }).then(res => setTopPerformers(res.data));
            await Promise.allSettled([stocksReq, ipoReq, losersReq, topReq]);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (selectedSymbol) {
            const fetchChart = async () => {
                setChartLoading(true);
                try {
                    const res = await axios.get(`/api/stocks/${selectedSymbol}/candles`, {
                        params: { timeframe: '1d' },
                        headers: { Authorization: `Bearer ${token}` }
                    });
                    setChartData(res.data);
                } catch (err) { console.error(err); }
                finally { setChartLoading(false); }
            };
            fetchChart();
        }
    }, [selectedSymbol, token]);

    useEffect(() => { fetchData(); }, []);

    const filteredStocks = allStocks.filter(s =>
        s.symbol.toLowerCase().includes(search.toLowerCase()) ||
        (s.company_name && s.company_name.toLowerCase().includes(search.toLowerCase()))
    );

    return (
        <Layout>
            <div className="p-8 max-w-7xl mx-auto space-y-8 pb-20">
                <header>
                    <h1 className="text-4xl font-black text-white mb-2 tracking-tighter uppercase">Market Explorer</h1>
                    <p className="text-slate-400 text-sm font-medium uppercase tracking-[0.2em]">Monitoring Emiten & Deteksi Setup Real-time</p>
                </header>

                {selectedSymbol && (
                    <div className="animate-in fade-in slide-in-from-top-4 duration-500 space-y-4">
                        <div className="flex items-center justify-between bg-slate-900 border border-slate-800 p-5 rounded-[2rem] shadow-2xl">
                            <div className="flex items-center gap-4">
                                <div className="p-3 bg-blue-600/20 rounded-2xl text-blue-500"><TrendingUp className="w-6 h-6" /></div>
                                <div>
                                    <div className="flex items-center gap-2">
                                        <h2 className="text-2xl font-black text-white uppercase">{selectedSymbol}</h2>
                                        <div className="group relative">
                                            <Info className="w-4 h-4 text-slate-500 cursor-help" />
                                            <div className="absolute left-0 top-6 w-64 p-3 bg-slate-800 text-[10px] text-slate-200 rounded-xl hidden group-hover:block z-50 shadow-2xl border border-slate-700">
                                                Grafik interaktif yang menampilkan pergerakan harga historis, indikator AO, dan plotting otomatis Fibonacci untuk strategi CTG.
                                            </div>
                                        </div>
                                    </div>
                                    <p className="text-[10px] text-slate-500 font-bold uppercase mt-1">Analisis Teknikal & Struktur Market</p>
                                </div>
                            </div>
                            <button onClick={() => setSelectedSymbol(null)} className="p-3 bg-slate-800 hover:bg-red-600 text-white rounded-full transition-all"><X className="w-5 h-5" /></button>
                        </div>
                        <div className="h-[600px] shadow-2xl relative bg-slate-900 rounded-[2.5rem] overflow-hidden border border-slate-800">
                            {chartLoading && <div className="absolute inset-0 z-20 flex items-center justify-center bg-slate-950/60 backdrop-blur-sm"><Loader2 className="w-12 h-12 text-blue-500 animate-spin" /></div>}
                            <PatternChart data={chartData} />
                        </div>
                    </div>
                )}

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
                    <div className="lg:col-span-3 space-y-6">
                        {/* Panel: Top Setup */}
                        <div className="bg-slate-900 border border-slate-800 rounded-[2rem] p-6 shadow-xl border-t-2 border-t-amber-500/20">
                            <div className="flex items-center justify-between mb-6">
                                <div className="flex items-center gap-2 text-amber-500">
                                    <Zap className="w-5 h-5 fill-current" />
                                    <h2 className="font-black text-white uppercase tracking-widest text-[10px]">Top Setup</h2>
                                </div>
                                <div className="group relative">
                                    <Info className="w-3.5 h-3.5 text-slate-600 cursor-help" />
                                    <div className="absolute left-0 top-5 w-48 p-2 bg-slate-800 text-[9px] text-slate-300 rounded-lg hidden group-hover:block z-50 border border-slate-700">
                                        Saham dengan skor divergensi (RSI/MACD/AO) tertinggi hari ini yang siap untuk konfirmasi entri.
                                    </div>
                                </div>
                            </div>
                            <div className="space-y-3">
                                {topPerformers.length === 0 ? <p className="text-[10px] text-slate-600 py-4 text-center italic">Belum ada setup</p> :
                                    topPerformers.map((stock, i) => (
                                        <div key={i} className="flex justify-between items-center group cursor-pointer hover:bg-slate-800/80 p-3 rounded-2xl transition-all" onClick={() => setSelectedSymbol(stock.symbol)}>
                                            <div>
                                                <div className="text-sm font-black text-white group-hover:text-blue-400">{stock.symbol}</div>
                                                <div className="text-[8px] text-slate-500 font-bold uppercase">{stock.method?.split(' ')[0]}</div>
                                            </div>
                                            <div className="text-xs font-black text-emerald-500 bg-emerald-500/10 px-2.5 py-1 rounded-xl">+{stock.score?.toFixed(0)}</div>
                                        </div>
                                    ))}
                            </div>
                        </div>

                        {/* Panel: Potential Reversals */}
                        <div className="bg-slate-900 border border-slate-800 rounded-[2rem] p-6 shadow-xl border-t-2 border-t-red-500/20">
                            <div className="flex items-center justify-between mb-6">
                                <div className="flex items-center gap-2 text-red-500">
                                    <ArrowDownCircle className="w-5 h-5" />
                                    <h2 className="font-black text-white uppercase tracking-widest text-[10px]">Reversals</h2>
                                </div>
                                <div className="group relative">
                                    <Info className="w-3.5 h-3.5 text-slate-600 cursor-help" />
                                    <div className="absolute left-0 top-5 w-48 p-2 bg-slate-800 text-[9px] text-slate-300 rounded-lg hidden group-hover:block z-50 border border-slate-700">
                                        Saham Top Loser yang sedang diskon tajam, menjadi target utama untuk mencari pola Bullish Divergence manual.
                                    </div>
                                </div>
                            </div>
                            <div className="space-y-3">
                                {topLosers.length === 0 ? <p className="text-[10px] text-slate-600 py-4 text-center italic">Tidak ada kandidat</p> :
                                    topLosers.map((stock, i) => (
                                        <div key={i} className="group cursor-pointer hover:bg-slate-800/80 p-3 rounded-2xl transition-all" onClick={() => setSelectedSymbol(stock.symbol)}>
                                            <div className="flex justify-between items-center mb-0.5">
                                                <div className="text-sm font-black text-white group-hover:text-red-400">{stock.symbol}</div>
                                                <div className="text-[10px] font-black text-slate-400 tracking-tighter">Rp {stock.last_price}</div>
                                            </div>
                                            <div className="text-[8px] text-slate-600 font-bold truncate uppercase">{stock.company_name}</div>
                                        </div>
                                    ))}
                            </div>
                        </div>

                        {/* Panel: Recent IPOs */}
                        <div className="bg-slate-900 border border-slate-800 rounded-[2rem] p-6 shadow-xl border-t-2 border-t-blue-500/20">
                            <div className="flex items-center justify-between mb-6">
                                <div className="flex items-center gap-2 text-blue-500">
                                    <TrendingUp className="w-5 h-5" />
                                    <h2 className="font-black text-white uppercase tracking-widest text-[10px]">Recent IPO</h2>
                                </div>
                                <div className="group relative">
                                    <Info className="w-3.5 h-3.5 text-slate-600 cursor-help" />
                                    <div className="absolute left-0 top-5 w-48 p-2 bg-slate-800 text-[9px] text-slate-300 rounded-lg hidden group-hover:block z-50 border border-slate-700">
                                        Emiten yang baru melantai di bursa. Penting untuk dipantau karena sering memiliki volatilitas tinggi.
                                    </div>
                                </div>
                            </div>
                            <div className="space-y-3">
                                {recentIpos.map((ipo, i) => (
                                    <div key={i} className="group cursor-pointer hover:bg-slate-800/80 p-3 rounded-2xl transition-all" onClick={() => setSelectedSymbol(ipo.symbol)}>
                                        <div className="text-sm font-black text-white group-hover:text-blue-400">{ipo.symbol}</div>
                                        <div className="text-[8px] text-slate-500 font-bold truncate mb-1 uppercase">{ipo.company_name}</div>
                                        <div className="text-[8px] font-black text-emerald-500 flex items-center gap-1 uppercase tracking-tighter">
                                            <Calendar className="w-2.5 h-2.5" /> {ipo.listing_date ? new Date(ipo.listing_date).toLocaleDateString('id-ID', { day: 'numeric', month: 'short' }) : 'Baru'}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>

                    <div className="lg:col-span-9 space-y-6">
                        <div className="bg-slate-900 border border-slate-800 rounded-[2.5rem] overflow-hidden shadow-2xl">
                            <div className="p-8 border-b border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-6 bg-slate-950/20">
                                <div className="flex items-center gap-4">
                                    <div className="p-3 bg-slate-800 rounded-2xl text-blue-500"><Filter className="w-6 h-6" /></div>
                                    <div>
                                        <div className="flex items-center gap-2">
                                            <h2 className="text-xl font-black text-white uppercase tracking-tighter">Market Universe</h2>
                                            <div className="group relative">
                                                <Info className="w-4 h-4 text-slate-600 cursor-help" />
                                                <div className="absolute left-0 top-6 w-64 p-3 bg-slate-800 text-[10px] text-slate-200 rounded-xl hidden group-hover:block z-50 shadow-2xl border border-slate-700">
                                                    Daftar seluruh emiten IDX di bawah Rp 1.000 yang dipantau sistem. Harga diperbarui secara otomatis dari database.
                                                </div>
                                            </div>
                                        </div>
                                        <p className="text-[10px] text-slate-500 font-black uppercase tracking-widest mt-1">{filteredStocks.length} Saham Terdaftar</p>
                                    </div>
                                </div>
                                <div className="relative">
                                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                                    <input type="text" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Cari kode atau nama emiten..." className="bg-slate-950 border border-slate-800 text-sm text-white pl-12 pr-6 py-4 rounded-[1.5rem] outline-none focus:ring-2 focus:ring-blue-500 transition-all min-w-[350px] font-bold" />
                                </div>
                            </div>

                            <div className="overflow-x-auto">
                                <table className="w-full text-left">
                                    <thead>
                                        <tr className="text-slate-500 text-[10px] uppercase tracking-widest bg-slate-950/50 font-black">
                                            <th className="px-10 py-6">Emiten</th>
                                            <th className="px-10 py-6">Perusahaan / Sektor</th>
                                            <th className="px-10 py-6">Harga</th>
                                            <th className="px-10 py-6">Aksi</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-800">
                                        {loading ? <tr><td colSpan={4} className="px-10 py-32 text-center"><div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div><p className="text-[10px] font-black text-slate-600 uppercase">Sinkronisasi Database...</p></td></tr> :
                                            filteredStocks.map((stock, i) => (
                                                <tr key={i} className="hover:bg-blue-600/5 transition-all group cursor-pointer" onClick={() => { setSelectedSymbol(stock.symbol); window.scrollTo({ top: 100, behavior: 'smooth' }); }}>
                                                    <td className="px-10 py-8">
                                                        <div className="font-black text-white text-2xl group-hover:text-blue-400 transition-colors">{stock.symbol}</div>
                                                        <span className="text-[9px] font-black px-2 py-0.5 bg-slate-800 text-slate-500 rounded uppercase mt-2 inline-block">IDX Equity</span>
                                                    </td>
                                                    <td className="px-10 py-8">
                                                        <div className="text-xs text-slate-300 font-black uppercase truncate max-w-[250px] mb-2">{stock.company_name || stock.name}</div>
                                                        <div className="text-[9px] text-blue-400 font-black bg-blue-400/5 px-2.5 py-1 rounded-lg inline-block uppercase">{stock.sector || 'N/A'}</div>
                                                    </td>
                                                    <td className="px-10 py-8">
                                                        <div className="text-2xl font-black text-slate-100 tracking-tighter">Rp {stock.last_price?.toLocaleString() || '-'}</div>
                                                        <div className="flex items-center gap-1.5 mt-2"><div className={`w-1.5 h-1.5 rounded-full ${stock.is_active ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`}></div><span className="text-[8px] font-black text-slate-500 uppercase tracking-widest">Real-time</span></div>
                                                    </td>
                                                    <td className="px-10 py-8"><button className="px-6 py-2.5 bg-slate-800 group-hover:bg-blue-600 text-white text-[10px] font-black rounded-xl transition-all uppercase tracking-widest shadow-lg">Buka Grafik</button></td>
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

export default StockList;
