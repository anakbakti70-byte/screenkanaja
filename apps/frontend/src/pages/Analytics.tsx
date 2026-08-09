import React from 'react';
import Layout from '../components/Layout';
import { BarChart3, TrendingUp, Wallet, Target, ArrowUpRight, ArrowDownRight, Globe, Zap, Clock } from 'lucide-react';

const Analytics: React.FC = () => {
    return (
        <Layout>
            <div className="p-8 max-w-7xl mx-auto space-y-8">
                <header>
                    <h1 className="text-3xl font-bold text-white mb-2">Advanced Analytics</h1>
                    <p className="text-slate-400">Analisis mendalam performa portofolio dan statistik trading Anda.</p>
                </header>

                {/* Top Highlight Cards */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="bg-gradient-to-br from-blue-600 to-blue-800 rounded-3xl p-6 shadow-xl shadow-blue-500/20 relative overflow-hidden group">
                        <div className="relative z-10">
                            <div className="flex items-center justify-between mb-4">
                                <Wallet className="w-8 h-8 text-blue-100/50" />
                                <span className="bg-white/20 text-white text-[10px] font-bold px-2 py-1 rounded-full uppercase">Total Balance</span>
                            </div>
                            <div className="text-3xl font-bold text-white mb-1">Rp 152.400.000</div>
                            <div className="flex items-center gap-1.5 text-blue-100 text-sm font-medium">
                                <ArrowUpRight className="w-4 h-4" />
                                <span>+Rp 4.2M bulan ini</span>
                            </div>
                        </div>
                        <div className="absolute -right-4 -bottom-4 w-32 h-32 bg-white/10 rounded-full blur-3xl group-hover:scale-150 transition-transform duration-700"></div>
                    </div>

                    <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl flex flex-col justify-between">
                        <div className="flex items-center justify-between mb-2">
                            <Target className="w-6 h-6 text-emerald-500" />
                            <span className="text-xs font-bold text-slate-500 uppercase">Win Ratio</span>
                        </div>
                        <div className="flex items-end gap-3">
                            <div className="text-4xl font-bold text-white">68%</div>
                            <div className="mb-1.5 flex items-center gap-1 text-emerald-500 text-xs font-bold bg-emerald-500/10 px-2 py-1 rounded-lg">
                                <ArrowUpRight className="w-3 h-3" /> 2.1%
                            </div>
                        </div>
                        <div className="mt-4 w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                            <div className="h-full bg-emerald-500 rounded-full w-[68%] shadow-[0_0_10px_rgba(16,185,129,0.3)]"></div>
                        </div>
                    </div>

                    <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl flex flex-col justify-between">
                        <div className="flex items-center justify-between mb-2">
                            <Zap className="w-6 h-6 text-amber-500" />
                            <span className="text-xs font-bold text-slate-500 uppercase">Avg Profit/Loss</span>
                        </div>
                        <div className="flex items-end gap-3">
                            <div className="text-4xl font-bold text-white">4.2x</div>
                            <span className="text-xs text-slate-500 mb-1.5 font-medium">Risk/Reward</span>
                        </div>
                        <div className="mt-4 flex justify-between text-xs font-medium">
                            <span className="text-emerald-500">Wins: +12.4%</span>
                            <span className="text-red-500">Loss: -3.1%</span>
                        </div>
                    </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    {/* Sector Distribution */}
                    <div className="bg-slate-900 border border-slate-800 rounded-3xl p-8 shadow-xl">
                        <div className="flex items-center justify-between mb-8">
                            <h2 className="text-xl font-bold text-white flex items-center gap-3">
                                <Globe className="w-6 h-6 text-blue-500" /> Sector Allocation
                            </h2>
                            <button className="text-xs text-slate-500 font-bold hover:text-white transition-colors">View Details</button>
                        </div>

                        <div className="space-y-6">
                            {[
                                { name: 'Banking', percentage: 45, color: 'bg-blue-500' },
                                { name: 'Consumer Goods', percentage: 25, color: 'bg-emerald-500' },
                                { name: 'Infrastructure', percentage: 15, color: 'bg-amber-500' },
                                { name: 'Technology', percentage: 10, color: 'bg-purple-500' },
                                { name: 'Others', percentage: 5, color: 'bg-slate-700' },
                            ].map((sector, i) => (
                                <div key={i} className="group cursor-default">
                                    <div className="flex justify-between items-center mb-2">
                                        <span className="text-sm font-bold text-slate-300 group-hover:text-white transition-colors">{sector.name}</span>
                                        <span className="text-xs font-bold text-slate-500">{sector.percentage}%</span>
                                    </div>
                                    <div className="w-full bg-slate-950 h-3 rounded-full overflow-hidden border border-slate-800/50 p-0.5">
                                        <div
                                            className={`h-full rounded-full ${sector.color} transition-all duration-1000 ease-out`}
                                            style={{ width: `${sector.percentage}%` }}
                                        ></div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Trading Activity */}
                    <div className="bg-slate-900 border border-slate-800 rounded-3xl p-8 shadow-xl flex flex-col">
                        <div className="flex items-center justify-between mb-8">
                            <h2 className="text-xl font-bold text-white flex items-center gap-3">
                                <Clock className="w-6 h-6 text-blue-500" /> Recent Activity
                            </h2>
                        </div>

                        <div className="flex-1 space-y-4">
                            {[
                                { action: 'Buy Order', stock: 'ASII', amount: 'Rp 24.5M', time: '2 hours ago', status: 'Completed' },
                                { action: 'Sell Order', stock: 'BBCA', amount: 'Rp 50.1M', time: '5 hours ago', status: 'Completed' },
                                { action: 'Limit Order', stock: 'TLKM', amount: 'Rp 12.0M', time: '1 day ago', status: 'Pending' },
                                { action: 'Withdrawal', stock: 'CASH', amount: 'Rp 5.0M', time: '2 days ago', status: 'Completed' },
                                { action: 'Buy Order', stock: 'GOTO', amount: 'Rp 2.1M', time: '3 days ago', status: 'Failed' },
                            ].map((item, i) => (
                                <div key={i} className="flex items-center justify-between p-4 bg-slate-950/50 rounded-2xl border border-slate-800 hover:border-slate-700 transition-all">
                                    <div className="flex items-center gap-4">
                                        <div className={`p-2 rounded-xl ${item.action.includes('Buy') ? 'bg-emerald-500/10 text-emerald-500' : item.action.includes('Sell') ? 'bg-red-500/10 text-red-500' : 'bg-blue-500/10 text-blue-500'}`}>
                                            <Zap className="w-4 h-4" />
                                        </div>
                                        <div>
                                            <div className="text-sm font-bold text-white">{item.action}: {item.stock}</div>
                                            <div className="text-[10px] font-bold text-slate-500 uppercase">{item.time}</div>
                                        </div>
                                    </div>
                                    <div className="text-right">
                                        <div className="text-sm font-bold text-slate-200">{item.amount}</div>
                                        <div className={`text-[10px] font-bold uppercase ${item.status === 'Completed' ? 'text-emerald-500' : item.status === 'Pending' ? 'text-amber-500' : 'text-red-500'}`}>
                                            {item.status}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>

                        <button className="w-full mt-6 py-3 text-sm font-bold text-slate-400 hover:text-white bg-slate-800/50 rounded-xl transition-all">
                            View All Transactions
                        </button>
                    </div>
                </div>
            </div>
        </Layout>
    );
};

export default Analytics;
