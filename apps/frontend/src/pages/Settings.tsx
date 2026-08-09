import React, { useState } from 'react';
import Layout from '../components/Layout';
import { useAuth } from '../hooks/AuthContext';
import { Save, User, CheckCircle2, Key, Eye, EyeOff } from 'lucide-react';
import axios from 'axios';

const Settings: React.FC = () => {
    const { user, updateUser, token } = useAuth();
    const [activeTab, setActiveTab] = useState<'profile' | 'password'>('profile');

    const [username, setUsername] = useState(user?.username || '');
    const [newPassword, setNewPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);

    const [loading, setLoading] = useState(false);
    const [successMsg, setSuccessMsg] = useState('');
    const [errorMsg, setErrorMsg] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setErrorMsg('');
        setSuccessMsg('');

        try {
            // Handle standard JSON payload for username & password
            const payload: any = {};
            if (activeTab === 'profile') {
                if (username !== user?.username) payload.username = username;
            } else if (activeTab === 'password') {
                if (!newPassword) {
                    setErrorMsg("Kolom password baru wajib diisi.");
                    setLoading(false);
                    return;
                }
                payload.password = newPassword;
            }

            if (Object.keys(payload).length > 0) {
                await axios.put('/api/users/settings', payload, {
                    headers: { Authorization: `Bearer ${token}` }
                });

                if (activeTab === 'profile' && user && payload.username) {
                    updateUser({ ...user, username: payload.username });
                }

                setSuccessMsg('Pembaruan berhasil disimpan!');

                if (activeTab === 'password') {
                    setNewPassword('');
                }
            } else {
                setSuccessMsg("Tidak ada perubahan yang dilakukan.");
            }
        } catch (err: any) {
            setErrorMsg(err.response?.data?.detail || "Gagal menyimpan perubahan.");
        } finally {
            setLoading(false);
            setTimeout(() => setSuccessMsg(''), 5000);
        }
    };

    return (
        <Layout>
            <div className="p-8 max-w-5xl mx-auto h-full flex flex-col">
                <header className="mb-8 animate-fade-in">
                    <h1 className="text-3xl font-bold text-white mb-2 tracking-tight">Account Settings</h1>
                    <p className="text-slate-400">Sesuaikan profil dan amankan akun Anda di sini.</p>
                </header>

                <div className="flex-1 flex flex-col md:flex-row gap-8 animate-slide-up" style={{ animationDelay: '100ms' }}>
                    {/* Settings Menu Sidebar */}
                    <div className="w-full md:w-64 space-y-2">
                        <button
                            type="button"
                            onClick={() => { setActiveTab('profile'); setErrorMsg(''); setSuccessMsg(''); }}
                            className={`w-full flex items-center gap-3 px-5 py-4 rounded-2xl transition-all font-medium ${activeTab === 'profile'
                                    ? 'bg-blue-600/10 text-blue-500 ring-1 ring-blue-500/50 shadow-[0_0_15px_rgba(59,130,246,0.1)]'
                                    : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'
                                }`}
                        >
                            <User className="w-5 h-5" />
                            Profil
                        </button>
                        <button
                            type="button"
                            onClick={() => { setActiveTab('password'); setErrorMsg(''); setSuccessMsg(''); }}
                            className={`w-full flex items-center gap-3 px-5 py-4 rounded-2xl transition-all font-medium ${activeTab === 'password'
                                    ? 'bg-blue-600/10 text-blue-500 ring-1 ring-blue-500/50 shadow-[0_0_15px_rgba(59,130,246,0.1)]'
                                    : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'
                                }`}
                        >
                            <Key className="w-5 h-5" />
                            Keamanan
                        </button>
                    </div>

                    {/* Settings Content area */}
                    <form onSubmit={handleSubmit} className="flex-1 bg-slate-900 border border-slate-800 rounded-3xl p-8 shadow-xl min-h-[400px]">
                        {successMsg && (
                            <div className="mb-6 bg-emerald-500/10 border border-emerald-500/50 text-emerald-500 p-4 rounded-xl flex items-center gap-3 animate-fade-in">
                                <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
                                <p className="text-sm font-medium">{successMsg}</p>
                            </div>
                        )}

                        {errorMsg && (
                            <div className="mb-6 bg-red-500/10 border border-red-500/50 text-red-500 p-4 rounded-xl text-sm font-medium animate-fade-in">
                                {errorMsg}
                            </div>
                        )}

                        <div className="animate-fade-in" key={activeTab}>
                            {activeTab === 'profile' && (
                                <div className="space-y-8">
                                    <h3 className="text-xl font-bold text-white mb-6 border-b border-slate-800 pb-4">Profil Publik</h3>
                                    <div className="max-w-md space-y-6">
                                        <div>
                                            <label className="block text-sm font-medium text-slate-400 mb-2">Username Display</label>
                                            <div className="relative">
                                                <User className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                                                <input
                                                    type="text"
                                                    required
                                                    value={username}
                                                    onChange={(e) => setUsername(e.target.value)}
                                                    className="w-full bg-slate-950 border border-slate-700 text-white pl-12 pr-4 py-3 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition-all focus:bg-slate-900"
                                                />
                                            </div>
                                            <p className="text-xs text-slate-500 mt-2">Nama ini akan ditampilkan pada sistem Anda.</p>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {activeTab === 'password' && (
                                <div className="space-y-8">
                                    <h3 className="text-xl font-bold text-white mb-6 border-b border-slate-800 pb-4">Keamanan Kata Sandi</h3>
                                    <div className="max-w-md space-y-6">
                                        <div>
                                            <label className="block text-sm font-medium text-slate-400 mb-2">Password Baru</label>
                                            <div className="relative">
                                                <Key className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                                                <input
                                                    type={showPassword ? "text" : "password"}
                                                    value={newPassword}
                                                    onChange={(e) => setNewPassword(e.target.value)}
                                                    className="w-full bg-slate-950 border border-slate-700 text-white pl-12 pr-12 py-3 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition-all focus:bg-slate-900"
                                                    placeholder="Tentukan sandi baru"
                                                />
                                                <button
                                                    type="button"
                                                    onClick={() => setShowPassword(!showPassword)}
                                                    className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
                                                >
                                                    {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}

                            <div className="pt-10 flex border-t border-slate-800 mt-8">
                                <button
                                    type="submit"
                                    disabled={loading}
                                    className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-xl font-bold flex items-center gap-2 transition-all shadow-lg shadow-blue-500/20 disabled:opacity-50"
                                >
                                    <Save className="w-5 h-5" />
                                    {loading ? 'Menyimpan...' : 'Simpan Perubahan'}
                                </button>
                            </div>
                        </div>
                    </form>
                </div>
            </div>
        </Layout>
    );
};

export default Settings;