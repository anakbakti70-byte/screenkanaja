import React from 'react';
import { Activity, TrendingUp, AlertCircle } from 'lucide-react';
import Layout from '../components/Layout';
import { useAuth } from '../hooks/AuthContext';

const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const stats = [
    { label: 'Active Scans', value: '12', icon: Activity, color: 'text-blue-500', bg: 'bg-blue-500/10' },
    { label: 'Bullish Setups', value: '5', icon: TrendingUp, color: 'text-emerald-500', bg: 'bg-emerald-500/10' },
    { label: 'Alerts Today', value: '3', icon: AlertCircle, color: 'text-amber-500', bg: 'bg-amber-500/10' },
  ];

  return (
    <Layout>
      <div className="p-8 max-w-7xl mx-auto">
        <header className="mb-10 animate-[fadeIn_0.5s_ease-out_forwards]">
          <h1 className="text-3xl font-bold text-white mb-2 tracking-tight">Market Overview</h1>
          <p className="text-slate-400 text-lg">
            Welcome back, <span className="text-blue-400 font-medium capitalize">{user?.username || 'User'}</span>! Here's what's happening today.
          </p>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
          {stats.map((stat, i) => (
            <div
              key={stat.label}
              className="bg-slate-900 border border-slate-800 p-6 rounded-2xl shadow-xl hover:shadow-2xl hover:border-slate-700 transition-all duration-300 animate-[slideUp_0.5s_ease-out_forwards]"
              style={{ animationDelay: `${i * 100}ms` }}
            >
              <div className="flex items-center justify-between mb-4">
                <div className={`p-3 rounded-xl ${stat.bg}`}>
                  <stat.icon className={`w-6 h-6 ${stat.color}`} />
                </div>
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-widest bg-slate-950 px-3 py-1 rounded-full border border-slate-800">Live</span>
              </div>
              <div className="text-4xl font-bold text-white mb-2 tracking-tight">{stat.value}</div>
              <div className="text-sm text-slate-400 font-medium">{stat.label}</div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-8 min-h-[350px] flex items-center justify-center shadow-xl animate-[slideUp_0.5s_ease-out_forwards]" style={{ animationDelay: '300ms' }}>
            <div className="text-center">
              <div className="inline-flex w-16 h-16 rounded-full bg-slate-800/50 items-center justify-center mb-4 border border-slate-700/50">
                <TrendingUp className="w-8 h-8 text-slate-500" />
              </div>
              <div className="text-slate-300 font-medium mb-2">Recent Setups Chart</div>
              <div className="text-sm text-slate-500 italic px-4">(Integrasi Chart TradingView/Lightweight akan muncul di sini)</div>
            </div>
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-8 min-h-[350px] shadow-xl animate-[slideUp_0.5s_ease-out_forwards]" style={{ animationDelay: '400ms' }}>
            <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-blue-500" />
              Recent Alerts
            </h3>
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="group flex items-center gap-4 p-4 rounded-2xl bg-slate-950/50 border border-slate-800 hover:border-slate-700 transition-all cursor-pointer">
                  <div className="w-2.5 h-2.5 rounded-full bg-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.8)]" />
                  <div className="flex-1">
                    <div className="text-sm font-bold text-slate-200 group-hover:text-blue-400 transition-colors">BBCA.JK - Bullish Divergence</div>
                    <div className="text-xs text-slate-500 mt-1">{i * 2} minutes ago • Timeframe: 1H</div>
                  </div>
                  <div className="bg-blue-500/10 text-blue-400 px-3 py-1 rounded-full text-xs font-bold border border-blue-500/20">
                    Match 85%
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default Dashboard;
