import React, { useEffect, useState } from 'react';
import { Activity, TrendingUp, AlertCircle, Loader2, ShieldAlert } from 'lucide-react';
import Layout from '../components/Layout';
import { useAuth } from '../hooks/AuthContext';
import { getScannerResults } from '../api/scanner';
import { getStocks } from '../api/stocks';
import { useNavigate } from 'react-router-dom';

const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<any[]>([]);
  const [totalStocks, setTotalStocks] = useState(0);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [results, stocks] = await Promise.all([
          getScannerResults('idx', '1d', 5),
          getStocks()
        ]);
        setData(results || []);
        setTotalStocks(stocks?.length || 0);
      } catch (error) {
        console.error("Error loading dashboard data:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const stats = [
    { label: 'Stocks Tracked', value: totalStocks.toString(), icon: Activity, color: 'text-blue-500', bg: 'bg-blue-500/10' },
    { label: 'Latest Setups', value: data.length.toString(), icon: TrendingUp, color: 'text-emerald-500', bg: 'bg-emerald-500/10' },
    { label: 'Active Signals', value: data.filter(d => d.status === 'READY').length.toString(), icon: AlertCircle, color: 'text-amber-500', bg: 'bg-amber-500/10' },
  ];

  return (
    <Layout>
      <div className="p-8 max-w-7xl mx-auto">
        <header className="mb-10">
          <h1 className="text-3xl font-bold text-white mb-2 tracking-tight">Market Overview</h1>
          <p className="text-slate-400 text-lg">
            Welcome back, <span className="text-blue-400 font-medium capitalize">{user?.username || 'User'}</span>! Here's what's happening today.
          </p>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
          {stats.map((stat, i) => (
            <div
              key={stat.label}
              className="bg-slate-900 border border-slate-800 p-6 rounded-2xl shadow-xl hover:shadow-2xl hover:border-slate-700 transition-all duration-300"
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
          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-8 min-h-[350px] flex items-center justify-center shadow-xl">
            <div className="text-center">
              <div className="inline-flex w-16 h-16 rounded-full bg-blue-600/10 items-center justify-center mb-4 border border-blue-500/20">
                <ShieldAlert className="w-8 h-8 text-blue-500" />
              </div>
              <div className="text-white font-black text-xl mb-2 uppercase tracking-tighter">CTG Compliance System</div>
              <div className="text-sm text-slate-500 font-bold px-4 leading-relaxed">
                {loading ? "Analyzing Database..." : `Sistem aktif memantau ${totalStocks} emiten IDX di bawah Rp 1.000 dengan akurasi formula Divergence Method §3-§5.`}
              </div>
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-8 min-h-[350px] shadow-xl">
            <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-blue-500" />
              Latest Potential Setups
            </h3>
            <div className="space-y-4">
              {loading ? (
                <div className="flex justify-center py-10"><Loader2 className="animate-spin text-blue-500" /></div>
              ) : data.length > 0 ? (
                data.map((item, i) => (
                  <div
                    key={i}
                    onClick={() => navigate('/scanner')}
                    className="group flex items-center gap-4 p-4 rounded-2xl bg-slate-950/50 border border-slate-800 hover:border-slate-700 transition-all cursor-pointer"
                  >
                    <div className={`w-2.5 h-2.5 rounded-full ${item.status === 'READY' ? 'bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.8)]' : 'bg-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.8)]'}`} />
                    <div className="flex-1">
                      <div className="text-sm font-bold text-slate-200 group-hover:text-blue-400 transition-colors">
                        {item.symbol} - {item.method}
                      </div>
                      <div className="text-xs text-slate-500 mt-1">
                        Score: {item.score?.toFixed(1)} • TF: {item.timeframe}
                      </div>
                    </div>
                    <div className="bg-blue-500/10 text-blue-400 px-3 py-1 rounded-full text-xs font-bold border border-blue-500/20">
                      RR {item.risk_reward?.toFixed(1)}
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center py-10 text-slate-500 text-sm">No setups found yet. Run scanner to see results.</div>
              )}
            </div>
            {data.length > 0 && (
                <button
                    onClick={() => navigate('/scanner')}
                    className="w-full mt-6 py-3 text-xs font-bold text-slate-500 hover:text-white transition-colors"
                >
                    VIEW ALL SCANNER RESULTS
                </button>
            )}
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default Dashboard;
