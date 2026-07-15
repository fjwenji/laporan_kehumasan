import React, { useState } from 'react';
import { Eye, EyeOff, AlertCircle, X, Key } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import { authApi } from '../services/api';
import './LoginPage.css';

export default function LoginPage() {
  const navigate = useNavigate();
  const { user, login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [showForgotModal, setShowForgotModal] = useState(false);
  const [forgotUsername, setForgotUsername] = useState('');
  const [forgotSuccess, setForgotSuccess] = useState('');
  const [forgotLoading, setForgotLoading] = useState(false);

  React.useEffect(() => {
    if (user) {
      navigate(user.role === 'admin' ? '/admin' : '/dashboard', { replace: true });
    }
  }, [user, navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await login(username, password);
    } catch (err) {
      setError('Username atau password salah');
    } finally {
      setIsLoading(false);
    }
  };

  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setForgotSuccess('');
    setForgotLoading(true);

    try {
      await authApi.forgotPassword(forgotUsername);
      setForgotSuccess('Instruksi reset password telah dikirim. Hubungi admin jika tidak menerima.');
      setForgotUsername('');
    } catch (err: any) {
      setError(err.message || 'Gagal request reset password');
    } finally {
      setForgotLoading(false);
    }
  };

  return (
    <div className="login-page">
      <section className="login-form-side">
        <div className="login-form-container">
          <div className="login-brand">
            <span className="brand-name">DJPb Mayz Monitoring System</span>
          </div>

          <div className="login-welcome">
            <h1 className="login-title">Selamat Datang Kembali</h1>
            <p className="login-subtitle">
              Masuk untuk mengakses dashboard monitoring publikasi Instagram DJPb
            </p>
          </div>
          <form onSubmit={handleSubmit} className="login-form">
            {error && (
              <div className="error-message">
                <AlertCircle size={16} />
                <span>{error}</span>
              </div>
            )}

            <div className="form-group">
              <label htmlFor="username">Username</label>
              <input
                type="text"
                id="username"
                className="form-input"
                placeholder="Masukkan username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                disabled={isLoading}
                autoComplete="username"
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="password">Password</label>
              <div className="password-wrapper">
                <input
                  type={showPassword ? 'text' : 'password'}
                  id="password"
                  className="form-input"
                  placeholder="Masukkan password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isLoading}
                  autoComplete="current-password"
                  required
                />
                <button
                  type="button"
                  className="toggle-password"
                  onClick={() => setShowPassword(!showPassword)}
                  tabIndex={-1}
                  aria-label={showPassword ? 'Sembunyikan password' : 'Tampilkan password'}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              className="login-button"
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <span className="spinner" />
                  <span>Memuat...</span>
                </>
              ) : (
                <span>Masuk</span>
              )}
            </button>

            <button
              type="button"
              className="forgot-password-link"
              onClick={() => setShowForgotModal(true)}
            >
              <Key size={14} />
              <span>Lupa password?</span>
            </button>
          </form>

          <div className="login-footer">
            <p className="login-footer-text">
              © {new Date().getFullYear()} DJPb Mayz Monitoring System. Hak cipta dilindungi.
            </p>
          </div>
        </div>
      </section>

      <section className="login-illustration-side">
        <div className="login-illustration">
          <img
            src="/assets/images/login/login_illustration.png"
            alt="Mayz Monitoring Illustration"
            className="illustration-image"
          />
        </div>
      </section>

      {showForgotModal && (
        <div className="modal-overlay" onClick={() => setShowForgotModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Lupa Password</h3>
              <button className="close-btn" onClick={() => setShowForgotModal(false)}>
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleForgotPassword}>
              <div className="forgot-info">
                <p>Masukkan username Anda. Admin akan mereset password Anda.</p>
              </div>

              {error && (
                <div className="error-message">
                  <AlertCircle size={16} />
                  <span>{error}</span>
                </div>
              )}

              {forgotSuccess && (
                <div className="success-message">
                  <span>{forgotSuccess}</span>
                </div>
              )}

              <div className="form-group">
                <label>Username</label>
                <input
                  type="text"
                  className="form-input"
                  value={forgotUsername}
                  onChange={(e) => setForgotUsername(e.target.value)}
                  placeholder="Masukkan username"
                  required
                />
              </div>

              <div className="modal-actions">
                <button type="button" className="btn btn-ghost" onClick={() => setShowForgotModal(false)}>
                  Batal
                </button>
                <button type="submit" className="btn btn-primary" disabled={forgotLoading}>
                  {forgotLoading ? 'Memuat...' : 'Request Reset'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
