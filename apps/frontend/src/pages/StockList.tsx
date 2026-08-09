import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { Search, Zap, TrendingUp, Calendar, Filter, ChevronRight, Info } from 'lucide-react';
import axios from 'axios';
import { useAuth } from '../hooks/AuthContext';

const StockList: React.FC = () => {
    const { token } = useAuth();
    const [allStocks, setAllStocks] = useState<any[]>([]);
    const [recentIpos, setRecentIpos] = useState<any[]>([]);
    const [topPerformers, setTopPerformers] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');

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
        s.company_name.toLowerCase().includes(search.toLowerCase())
    );

    return (
        <Layout>
            <div className="p-8 max-w-7xl mx-auto space-y-8">
                <header>
                    <h1 className="text-3xl font-bold text-white mb-2">Daftar Saham IDX</h1>
                    <p className="text-slate-400">Database saham real-time yang tersinkronisasi langsung dengan bursa.</p>
                </header>

                <div className="grid grid-cols-1 lg:grid-cols-4 gap-8 items-start">
                    {/* Left Stats Section */}
                    <div className="lg:col-span-1 space-y-6">
                        {/* Top Performer Card */}
                        <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl">
                            <div className="flex items-center gap-2 mb-6">
                                <Zap className="w-5 h-5 text-amber-500" />
                                <h2 className="font-bold text-white uppercase tracking-wider text-xs">Top Setup Today</h2>
                            </div>
                            <div className="space-y-4">
                                {topPerformers.length === 0 ? (
                                    <p className="text-xs text-slate-500 italic">No setups found.</p>
                                ) : (
                                    topPerformers.map((stock, i) => (
                                        <div key={i} className="flex justify-between items-center">
                                            <div>
                                                <div className="text-sm font-bold text-white">{stock.symbol}</div>
                                                <div className="text-[10px] text-slate-500 uppercase">{stock.strategy_name.split(' ')[0]}</div>
                                            </div>
                                            <div className="text-xs font-bold text-emerald-500">{stock.score.toFixed(0)}%</div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>

                        {/* IPO Card */}
                        <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl">
                            <div className="flex items-center gap-2 mb-6">
                                <TrendingUp className="w-5 h-5 text-emerald-500" />
                                <h2 className="font-bold text-white uppercase tracking-wider text-xs">Recent IPOs</h2>
                            </div>
                            <div className="space-y-4">
                                {recentIpos.length === 0 ? (
                                    <p className="text-xs text-slate-500 italic">Run sync_universe to see IPOs.</p>
                                ) : (
                                    recentIpos.map((ipo, i) => (
                                        <div key={i} className="group">
                                            <div className="text-xs font-bold text-white group-hover:text-emerald-400 transition-colors">{ipo.symbol}</div>
                                            <div className="text-[10px] text-slate-500 mb-1">{ipo.company_name}</div>
                                            <div className="text-[9px] font-bold text-emerald-500 flex items-center gap-1 uppercase">
                                                <Calendar className="w-3 h-3" />
                                                {new Date(ipo.listing_date).toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' })}
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Main Stock Table */}
                    <div className="lg:col-span-3 space-y-6">
                        <div className="bg-slate-900 border border-slate-800 rounded-3xl overflow-hidden shadow-xl">
                            <div className="p-6 border-b border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
                                <div className="flex items-center gap-3">
                                    <Filter className="w-5 h-5 text-blue-500" />
                                    <h2 className="text-lg font-bold text-white">Market Universe</h2>
                                    <span className="bg-blue-600/20 text-blue-500 text-xs font-bold px-2.5 py-1 rounded-lg">
                                        {filteredStocks.length} Saham Terdaftar
                                    </span>
                                </div>
                                <div className="relative">
                                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                                    <input
                                        type="text"
                                        value={search}
                                        onChange={(e) => setSearch(e.target.value)}
                                        placeholder="Cari kode atau nama perusahaan..."
                                        className="bg-slate-950 border border-slate-800 text-sm text-slate-300 pl-10 pr-4 py-2 rounded-xl outline-none focus:ring-2 focus:ring-blue-500 min-w-[280px]"
                                    />
                                </div>
                            </div>

                            <div className="overflow-x-auto">
                                <table className="w-full text-left">
                                    <thead>
                                        <tr className="text-slate-500 text-xs uppercase tracking-wider bg-slate-950/50">
                                            <th className="px-6 py-4 font-bold">Kode</th>
                                            <th className="px-6 py-4 font-bold">Nama Perusahaan</th>
                                            <th className="px-6 py-4 font-bold">Sektor / Industri</th>
                                            <th className="px-6 py-4 font-bold">Market Cap</th>
                                            <th className="px-6 py-4 font-bold">Status</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-800">
                                        {loading ? (
                                            <tr>
                                                <td colSpan={5} className="px-6 py-12 text-center">
                                                    <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                                                    <span className="text-slate-500">Loading database...</span>
                                                </td>
                                            </tr>
                                        ) : filteredStocks.length === 0 ? (
                                            <tr>
                                                <td colSpan={5} className="px-6 py-12 text-center text-slate-500 italic">Data tidak ditemukan.</td>
                                            </tr>
                                        ) : (
                                            filteredStocks.map((stock, i) => (
                                                <tr key={i} className="hover:bg-slate-800/30 transition-colors group">
                                                    <td className="px-6 py-4 font-bold text-white group-hover:text-blue-400">
                                                        {stock.symbol}
                                                    </td>
                                                    <td className="px-6 py-4">
                                                        <div className="text-xs text-slate-300 font-medium truncate max-w-[200px]">{stock.company_name}</div>
                                                    </td>
                                                    <td className="px-6 py-4">
                                                        <div className="text-[10px] text-blue-400 font-bold">{stock.sector || '-'}</div>
                                                        <div className="text-[9px] text-slate-500 truncate max-w-[150px]">{stock.industry || '-'}</div>
                                                    </td>
                                                    <td className="px-6 py-4 text-xs text-slate-400">
                                                        {stock.market_cap ? `Rp ${(stock.market_cap / 1e12).toFixed(1)}T` : '-'}
                                                    </td>
                                                    <td className="px-6 py-4">
                                                        <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold ${stock.is_active ? 'bg-emerald-500/10 text-emerald-500' : 'bg-red-500/10 text-red-500'}`}>
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

                        <div className="bg-blue-600/10 border border-blue-500/30 p-4 rounded-2xl flex gap-3 items-start">
                            <Info className="w-5 h-5 text-blue-500 mt-0.5" />
                            <p className="text-sm text-blue-300 leading-relaxed">
                                Daftar ini disinkronkan otomatis dengan API Bursa Efek Indonesia (IDX). Saham baru akan otomatis muncul di sini setelah listing resmi.
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </Layout>
    );
};

export default StockList;
