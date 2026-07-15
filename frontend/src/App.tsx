import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { authApi } from './services/api';
import type { User } from './types';
import { SidebarProvider } from './contexts/SidebarContext';

import LoginPage from './pages/LoginPage';
import UserDashboard from './pages/UserDashboard';
import AdminDashboard from './pages/AdminDashboard';
import JobMonitoringPage from './pages/JobMonitoringPage';
import UserManagement from './pages/UserManagement';
import SettingsPage from './pages/SettingsPage';
import InstagramAccountsPage from './pages/InstagramAccountsPage';
import ExportPage from './pages/ExportPage';
import StagingDataPage from './pages/StagingDataPage';

import './styles/layout.css';

interface AuthProviderProps {
  children: React.ReactNode;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = React.createContext<AuthContextType | null>(null);

function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      authApi.getMe()
        .then(userData => {
          setUser(userData as User);
        })
        .catch(() => {
          localStorage.removeItem('token');
        })
        .finally(() => {
          setLoading(false);
        });
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (username: string, password: string) => {
    const response = await authApi.login(username, password);
    localStorage.setItem('token', response.access_token);
    const userData = await authApi.getMe();
    setUser(userData as User);
  };

  const logout = () => {
    localStorage.removeItem('token');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

function useAuth() {
  const context = React.useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}

function ProtectedRoute({ children, requireAdmin = false }: { children: React.ReactNode; requireAdmin?: boolean }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner" />
        <p>Memuat...</p>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (requireAdmin && user.role !== 'admin') {
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
}

function AppContent() {
  const { user } = useAuth();

  return (
    <SidebarProvider>
      <Routes>
        <Route path="/login" element={
          user ? <Navigate to={user.role === 'admin' ? '/admin' : '/dashboard'} replace /> : <LoginPage />
        } />
        <Route path="/dashboard" element={
          <ProtectedRoute>
            <UserDashboard />
          </ProtectedRoute>
        } />
        <Route path="/export" element={
          <ProtectedRoute>
            <ExportPage />
          </ProtectedRoute>
        } />
        <Route path="/accounts" element={
          <ProtectedRoute>
            <InstagramAccountsPage />
          </ProtectedRoute>
        } />
        <Route path="/admin" element={
          <ProtectedRoute requireAdmin>
            <AdminDashboard />
          </ProtectedRoute>
        } />
        <Route path="/jobs" element={
          <ProtectedRoute requireAdmin>
            <JobMonitoringPage />
          </ProtectedRoute>
        } />
        <Route path="/users" element={
          <ProtectedRoute requireAdmin>
            <UserManagement />
          </ProtectedRoute>
        } />
        <Route path="/settings" element={
          <ProtectedRoute requireAdmin>
            <SettingsPage />
          </ProtectedRoute>
        } />
        <Route path="/staging" element={
          <ProtectedRoute requireAdmin>
            <StagingDataPage />
          </ProtectedRoute>
        } />
        <Route path="/" element={
          user ? <Navigate to={user.role === 'admin' ? '/admin' : '/dashboard'} replace /> : <Navigate to="/login" replace />
        } />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </SidebarProvider>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </BrowserRouter>
  );
}

export { useAuth };
