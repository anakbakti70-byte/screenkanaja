import React, { useState, useRef, useEffect } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
    LayoutDashboard,
    Search,
    BarChart3,
    History,
    Settings as SettingsIcon,
    LogOut,
    TrendingUp,
    ChevronUp,
    List as ListIcon
} from 'lucide-react';
import { useAuth } from '../hooks/AuthContext';

const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const { logout, user } = useAuth();
    const navigate = useNavigate();
    const [showUserMenu, setShowUserMenu] = useState(false);
    const menuRef = useRef<HTMLDivElement>(null);

    const navigation = [
        { name: 'Dashboard', icon: LayoutDashboard, path: '/' },
        { name: 'Scanner', icon: Search, path: '/scanner' },
        { name: 'Daftar Saham', icon: ListIcon, path: '/stocks' },
        { name: 'Backtest', icon: History, path: '/backtest' },
        { name: 'Analytics', icon: BarChart3, path: '/analytics' },
    ];

    // Close menu when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
                setShowUserMenu(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    return (
        <div className="flex h-screen bg-slate-950 font-sans text-slate-200">
            <aside className="w-64 border-r border-slate-800 bg-slate-900 flex flex-col justify-between transition-all">
                <div>
                    <div className="p-6 flex items-center gap-3">
                        <div className="bg-blue-600/20 p-2 rounded-lg">
                            <TrendingUp className="w-7 h-7 text-blue-500" />
                        </div>
                        <span className="text-xl font-bold tracking-tight text-white">StockScanner</span>
                    </div>

                    <nav className="flex-1 px-4 mt-6 space-y-2">
                        {navigation.map((item) => (
                            <NavLink
                                key={item.name}
                                to={item.path}
                                className={({ isActive }) =>
                                    `flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group ${isActive
                                        ? 'bg-blue-600/10 text-blue-500 font-semibold'
                                        : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                                    }`
                                }
                            >
                                <item.icon className="w-5 h-5 transition-transform group-hover:scale-110" />
                                <span>{item.name}</span>
                            </NavLink>
                        ))}
                    </nav>
                </div>

                <div className="p-4 relative" ref={menuRef}>
                    {/* Popup Menu */}
                    {showUserMenu && (
                        <div className="absolute bottom-full mb-2 left-4 right-4 bg-slate-800 border border-slate-700 rounded-xl shadow-2xl overflow-hidden animate-fade-in z-50">
                            <button
                                onClick={() => { setShowUserMenu(false); navigate('/settings'); }}
                                className="w-full flex items-center gap-3 px-4 py-3 text-sm text-slate-300 hover:bg-slate-700/50 hover:text-white transition-colors"
                            >
                                <SettingsIcon className="w-4 h-4" />
                                Account Settings
                            </button>
                            <div className="h-px w-full bg-slate-700"></div>
                            <button
                                onClick={() => { setShowUserMenu(false); logout(); }}
                                className="w-full flex items-center gap-3 px-4 py-3 text-sm text-red-400 hover:bg-red-500/10 hover:text-red-300 transition-colors"
                            >
                                <LogOut className="w-4 h-4" />
                                Logout
                            </button>
                        </div>
                    )}

                    {/* User Profile Button */}
                    <button
                        onClick={() => setShowUserMenu(!showUserMenu)}
                        className={`w-full flex items-center justify-between px-4 py-3 rounded-xl border transition-all ${showUserMenu
                                ? 'bg-slate-800 border-slate-600 shadow-lg'
                                : 'bg-slate-800/40 border-slate-700/50 hover:bg-slate-800 hover:border-slate-600'
                            }`}
                    >
                        <div className="flex items-center gap-3 overflow-hidden">
                            <div className="overflow-hidden text-left">
                                <div className="text-sm font-semibold text-white truncate">{user?.username || 'Loading...'}</div>
                                <div className="text-xs text-slate-500 capitalize">{user?.role || 'Guest'}</div>
                            </div>
                        </div>
                        <ChevronUp className={`w-5 h-5 text-slate-500 transition-transform ${showUserMenu ? 'rotate-180' : ''}`} />
                    </button>
                </div>
            </aside>

            <main className="flex-1 overflow-x-hidden overflow-y-auto bg-slate-950 relative z-0">
                {children}
            </main>
        </div>
    );
};

export default Layout;
