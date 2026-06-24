import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { useVendorAuth } from '../../context/VendorAuthContext';
import logoSrc from '../../../assets/logo.png';
import '@/admin/admin.css';

const EyeOpen = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
  </svg>
);
const EyeClosed = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
    <line x1="1" y1="1" x2="23" y2="23"/>
  </svg>
);

export default function VendorLoginPage() {
  const { loginWithPassword } = useVendorAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPass, setShowPass] = useState(false);
  const [loading, setLoading] = useState(false);
  const [remember, setRemember] = useState(true);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !password) { setError('Email and password are required.'); return; }
    setLoading(true);
    setError('');
    try {
      await loginWithPassword(email, password, remember);
      toast.success('Welcome back!');
      navigate('/vendor', { replace: true });
    } catch (err) {
      const msg = err?.response?.data?.detail ?? err?.response?.data?.message ?? 'Invalid email or password.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="ty-login-root">
      <div className="ty-login-card">
        <div className="ty-login-brand">
          <img src={logoSrc} alt="" className="ty-login-emblem" />
          <span className="ty-login-wordmark">Tyohaar</span>
        </div>

        <div className="ty-login-header">
          <div className="ty-login-badge">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
            </svg>
            Vendor access
          </div>
          <h1 className="ty-login-title">Vendor Portal</h1>
          <p className="ty-login-sub">Sign in to manage your profile and packages</p>
        </div>

        <div className="ty-login-sep" />

        <form onSubmit={handleSubmit} className="ty-login-form">
          {error && (
            <div className="ty-login-error">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
              </svg>
              {error}
            </div>
          )}

          <div className="ty-login-field">
            <label className="ty-login-label">Email address<span className="ty-login-req">*</span></label>
            <input
              type="email"
              className="ty-login-input"
              placeholder="vendor@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoFocus
              autoComplete="email"
              disabled={loading}
            />
          </div>

          <div className="ty-login-field">
            <label className="ty-login-label">Password<span className="ty-login-req">*</span></label>
            <div className="ty-login-pass-wrap">
              <input
                type={showPass ? 'text' : 'password'}
                className="ty-login-input"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                disabled={loading}
              />
              <button type="button" className="ty-login-eye" onClick={() => setShowPass(s => !s)} tabIndex={-1}>
                {showPass ? <EyeClosed /> : <EyeOpen />}
              </button>
            </div>
          </div>

          <label className="ty-login-remember">
            <input
              type="checkbox"
              checked={remember}
              onChange={(e) => setRemember(e.target.checked)}
              disabled={loading}
            />
            Keep me logged in
          </label>

          <button type="submit" className="ty-login-btn" disabled={loading}>
            {loading ? (
              <><span className="ty-login-spinner" /> Signing in…</>
            ) : (
              <>Sign in to Vendor Portal <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg></>
            )}
          </button>
        </form>

        <p className="ty-login-footer">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
          </svg>
          Tyohaar Vendor Portal · Secure access
        </p>
      </div>
    </div>
  );
}
