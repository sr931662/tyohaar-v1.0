import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { useAdminAuth } from '../../context/AuthContext';
import '../../admin.css';

export default function LoginPage() {
  const { login } = useAdminAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPass, setShowPass] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !password) {
      setError('Email and password are required.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      await login(email, password);
      toast.success('Welcome back!');
      navigate('/admin', { replace: true });
    } catch (err) {
      const msg = err?.response?.data?.detail
        ?? err?.response?.data?.message
        ?? 'Invalid credentials. Please try again.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="admin-root" style={{ minHeight: '100vh', background: 'var(--bg-base)' }}>
      <div className="admin-login-page" style={{ flex: 1 }}>
        <div className="admin-login-card">
          <div className="admin-login-logo">
            <div className="logo-icon">T</div>
            <span className="logo-text">Tyohaar</span>
          </div>

          <h1 className="admin-login-title">Admin Workspace</h1>
          <p className="admin-login-sub">Sign in to access the admin dashboard</p>

          <form onSubmit={handleSubmit}>
            {error && (
              <div className="admin-alert admin-alert-error" style={{ marginBottom: 16 }}>
                <span>⚠</span>
                <span>{error}</span>
              </div>
            )}

            <div className="form-group">
              <label className="form-label required">Email address</label>
              <input
                type="email"
                className="form-control"
                placeholder="admin@tyohaar.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoFocus
                autoComplete="email"
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label className="form-label required">Password</label>
              <div style={{ position: 'relative' }}>
                <input
                  type={showPass ? 'text' : 'password'}
                  className="form-control"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  disabled={loading}
                  style={{ paddingRight: 40 }}
                />
                <button
                  type="button"
                  onClick={() => setShowPass((s) => !s)}
                  style={{
                    position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)',
                    background: 'none', border: 'none', cursor: 'pointer', fontSize: 14,
                    color: 'var(--text-tertiary)',
                  }}
                >
                  {showPass ? '🙈' : '👁'}
                </button>
              </div>
            </div>

            <button
              type="submit"
              className="btn btn-primary w-full"
              disabled={loading}
              style={{ marginTop: 8, padding: '10px', fontSize: 14 }}
            >
              {loading ? (
                <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span className="spinner" style={{ width: 16, height: 16 }} />
                  Signing in…
                </span>
              ) : (
                'Sign in to Admin'
              )}
            </button>
          </form>

          <p style={{ textAlign: 'center', fontSize: 12, color: 'var(--text-tertiary)', marginTop: 20 }}>
            Tyohaar Admin Portal · Secure access only
          </p>
        </div>
      </div>
    </div>
  );
}
