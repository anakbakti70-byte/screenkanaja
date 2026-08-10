import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { Search, Zap, TrendingUp, Calendar, Filter, Info, X } from 'lucide-react';
import axios from 'axios';
import { useAuth } from '../hooks/AuthContext';
import { StockChart } from '../components/charts/StockChart';

const StockList: React.FC = () => {
    const { token } = useAuth();
    const [allStocks, setAllStocks] = useState<any[]>([]);
    const [recentIpos, setRecentIpos] = useState<any[]>([]);
    const [topPerformers, setTopPerformers] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);

    const fetchData = async () => {
        try {
            setLoading(true);
            const [stocksRes, ipoRes, topRes] = await Promise.all([
                axios.get('/api/stocks/', { headers: { Authorization: `Bearer ${token}` } }),
                axios.get('/api/stocks/ipo', { headers: { Authorization: `Bearer ${token}` } }),
                axios.get('/api/scanner/results', {
                    params: { limit: 5, sort_by: 'score', latest_only: true },
                    headers: { Authorization: `Bearer ${token}` }
                })
            ]);
            setAllStocks(stocksRes.data);
            setRecentIpos(ipoRes.data);
            setTopPerformers(topRes.data);
        } catch (err) {
            console.error("Failed to fetch stock list data", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const filteredStocks = allStocks.filter(s =>
        s.symbol.toLowerCase().includes(search.toLowerCase()) ||
        (s.company_name && s.company_name.toLowerCase().includes(search.toLowerCase()))
    );

    return (
        <Layout>
            <div className="p-8 max-w-7xl mx-auto space-y-8">
                <header>
                    <h1 className="text-3xl font-bold text-white mb-2 tracking-tight">Daftar Saham IDX</h1>
                    <p className="text-slate-400">Database saham real-time di bawah Rp 1.000.</p>
                </header>

                {/* Analysis Area for Selected Stock */}
                {selectedSymbol && (
                    <div className="animate-in fade-in slide-in-from-top-4 duration-500 space-y-4">
                        <div className="flex items-center justify-between bg-slate-900 border border-slate-800 p-4 rounded-3xl">
                            <div className="flex items-center gap-4">
                                <div className="p-3 bg-blue-500/10 rounded-2xl">
                                    <TrendingUp className="w-6 h-6 text-blue-500" />
                                </div>
                                <div>
                                    <h2 className="text-xl font-black text-white">{selectedSymbol}</h2>
                                    <p className="text-[10px] text-slate-500 uppercase tracking-widest">Real-time IDX Interactive Chart</p>
                                </div>
                            </div>
                            <button
                                onClick={() => setSelectedSymbol(null)}
                                className="p-2 bg-slate-800 hover:bg-red-600 text-white rounded-full transition-all"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>
                        <div className="h-[600px] shadow-2xl">
                            <StockChart symbol={selectedSymbol} market="idx" />
                        </div>
                    </div>
                )}

                <div className="grid grid-cols-1 lg:grid-cols-4 gap-8 items-start">
                    {/* Left Sidebar */}
                    <div className="lg:col-span-1 space-y-6">
                        <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl">
                            <div className="flex items-center gap-2 mb-6 text-amber-500">
                                <Zap className="w-5 h-5 fill-current" />
                                <h2 className="font-bold text-white uppercase tracking-wider text-xs">Top Setup Today</h2>
                            </div>
                            <div className="space-y-4">
                                {topPerformers.length === 0 ? (
                                    <p className="text-xs text-slate-500 italic">No setups found.</p>
                                ) : (
                                    topPerformers.map((stock, i) => (
                                        <div key={i} className="flex justify-between items-center group cursor-pointer hover:bg-slate-800/50 p-2 rounded-xl transition-all" onClick={() => setSelectedSymbol(stock.symbol)}>
                                            <div>
                                                <div className="text-sm font-bold text-white group-hover:text-blue-400">{stock.symbol}</div>
                                                <div className="text-[9px] text-slate-500 uppercase">{stock.method?.split(' ')[0]}</div>
                                            </div>
                                            <div className="text-xs font-bold text-emerald-500 bg-emerald-500/10 px-2 py-1 rounded-lg">{stock.score?.toFixed(0)}</div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>

                        <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl">
                            <div className="flex items-center gap-2 mb-6 text-emerald-500">
                                <TrendingUp className="w-5 h-5" />
                                <h2 className="font-bold text-white uppercase tracking-wider text-xs">Recent IPOs</h2>
                            </div>
                            <div className="space-y-4">
                                {recentIpos.length === 0 ? (
                                    <p className="text-xs text-slate-500 italic">No IPOs found.</p>
                                ) : (
                                    recentIpos.map((ipo, i) => (
                                        <div key={i} className="group cursor-pointer hover:bg-slate-800/50 p-2 rounded-xl transition-all" onClick={() => setSelectedSymbol(ipo.symbol)}>
                                            <div className="text-xs font-bold text-white group-hover:text-blue-400">{ipo.symbol}</div>
                                            <div className="text-[9px] text-slate-500 truncate mb-1">{ipo.company_name}</div>
                                            <div className="text-[9px] font-bold text-emerald-500 flex items-center gap-1 uppercase">
                                                <Calendar className="w-3 h-3" />
                                                {ipo.listing_date ? new Date(ipo.listing_date).toLocaleDateString('id-ID', { day: 'numeric', month: 'short' }) : '-'}
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Main List */}
                    <div className="lg:col-span-3 space-y-6">
                        <div className="bg-slate-900 border border-slate-800 rounded-3xl overflow-hidden shadow-xl">
                            <div className="p-6 border-b border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
                                <div className="flex items-center gap-3">
                                    <Filter className="w-5 h-5 text-blue-500" />
                                    <h2 className="text-lg font-bold text-white">Market Universe</h2>
                                    <span className="bg-blue-600/20 text-blue-500 text-[10px] font-black px-3 py-1 rounded-full uppercase tracking-tighter">
                                        {filteredStocks.length} Saham Terdaftar
                                    </span>
                                </div>
                                <div className="relative">
                                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                                    <input
                                        type="text"
                                        value={search}
                                        onChange={(e) => setSearch(e.target.value)}
                                        placeholder="Cari kode atau nama..."
                                        className="bg-slate-950 border border-slate-800 text-sm text-slate-300 pl-10 pr-4 py-2.5 rounded-xl outline-none focus:ring-2 focus:ring-blue-500 transition-all min-w-[280px]"
                                    />
                                </div>
                            </div>

                            <div className="overflow-x-auto">
                                <table className="w-full text-left">
                                    <thead>
                                        <tr className="text-slate-500 text-[10px] uppercase tracking-widest bg-slate-950/50 font-black">
                                            <th className="px-6 py-5">Emiten</th>
                                            <th className="px-6 py-5">Nama Perusahaan</th>
                                            <th className="px-6 py-5">Sektor</th>
                                            <th className="px-6 py-5">Harga</th>
                                            <th className="px-6 py-5">Status</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-800">
                                        {loading ? (
                                            <tr>
                                                <td colSpan={5} className="px-6 py-20 text-center">
                                                    <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
                                                </td>
                                            </tr>
                                        ) : filteredStocks.length === 0 ? (
                                            <tr>
                                                <td colSpan={5} className="px-6 py-20 text-center text-slate-500 italic">Emiten tidak ditemukan.</td>
                                            </tr>
                                        ) : (
                                            filteredStocks.map((stock, i) => (
                                                <tr
                                                    key={i}
                                                    className={`hover:bg-slate-800/40 transition-all group cursor-pointer ${selectedSymbol === stock.symbol ? 'bg-blue-600/10 border-l-4 border-l-blue-500' : ''}`}
                                                    onClick={() => {
                                                        setSelectedSymbol(stock.symbol);
                                                        window.scrollTo({ top: 100, behavior: 'smooth' });
                                                    }}
                                                >
                                                    <td className="px-6 py-5 font-black text-white text-lg">
                                                        {stock.symbol}
                                                    </td>
                                                    <td className="px-6 py-5">
                                                        <div className="text-xs text-slate-300 font-medium truncate max-w-[200px]">{stock.company_name || stock.name}</div>
                                                    </td>
                                                    <td className="px-6 py-5">
                                                        <div className="text-[10px] text-blue-400 font-bold bg-blue-400/5 px-2 py-0.5 rounded inline-block">{stock.sector || 'N/A'}</div>
                                                    </td>
                                                    <td className="px-6 py-5 text-sm font-bold text-slate-200">
                                                        Rp {stock.last_price?.toLocaleString() || '-'}
                                                    </td>
                                                    <td className="px-6 py-5">
                                                        <span className={`px-2 py-1 rounded-full text-[9px] font-black tracking-widest uppercase ${stock.is_active ? 'bg-emerald-500/10 text-emerald-500' : 'bg-red-500/10 text-red-500'}`}>
                                                            {stock.is_active ? 'ACTIVE' : 'INACTIVE'}
                                                        </span>
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

export default StockList;
