import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './hooks/AuthContext';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Settings from './pages/Settings';
import Scanner from './pages/Scanner';
import Backtest from './pages/Backtest';
import Analytics from './pages/Analytics';
import StockList from './pages/StockList';

const PrivateRoute = ({ children }: { children: React.ReactNode }) => {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return <div className="h-screen w-screen bg-slate-950 flex items-center justify-center text-white">Loading...</div>;
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />;
};

const PublicRoute = ({ children }: { children: React.ReactNode }) => {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return <div className="h-screen w-screen bg-slate-950 flex items-center justify-center text-white">Loading...</div>;
  return !isAuthenticated ? <>{children}</> : <Navigate to="/" />;
};

function AppRoutes() {
  return (
    <Routes>
      <Route
        path="/login"
        element={<PublicRoute><Login /></PublicRoute>}
      />
      <Route
        path="/"
        element={<PrivateRoute><Dashboard /></PrivateRoute>}
      />
      <Route
        path="/settings"
        element={<PrivateRoute><Settings /></PrivateRoute>}
      />
      <Route
        path="/scanner"
        element={<PrivateRoute><Scanner /></PrivateRoute>}
      />
      <Route
        path="/stocks"
        element={<PrivateRoute><StockList /></PrivateRoute>}
      />
      <Route
        path="/backtest"
        element={<PrivateRoute><Backtest /></PrivateRoute>}
      />
      <Route
        path="/analytics"
        element={<PrivateRoute><Analytics /></PrivateRoute>}
      />
    </Routes>
  );
}

function App() {
  return (
    <AuthProvider>
      <Router>
        <AppRoutes />
      </Router>
    </AuthProvider>
  );
}

export default App;
