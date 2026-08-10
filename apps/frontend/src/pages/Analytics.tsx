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

                <div className="flex items-center justify-center h-64 bg-slate-900/50 border border-dashed border-slate-800 rounded-3xl">
                    <div className="text-center">
                        <BarChart3 className="w-12 h-12 text-slate-700 mx-auto mb-4" />
                        <h2 className="text-lg font-bold text-slate-500">No Analytics Data Available</h2>
                        <p className="text-sm text-slate-600">Start trading or scanning to generate analytics.</p>
                    </div>
                </div>
            </div>
        </Layout>
    );
};

export default Analytics;
