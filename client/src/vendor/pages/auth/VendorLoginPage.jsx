import { useNavigate } from 'react-router-dom';
import { useVendorAuth } from '../../context/VendorAuthContext';
import logoSrc from '../../../assets/logo.png';
import '@/admin/admin.css';

export default function VendorLoginPage() {
  const { devLogin } = useVendorAuth();
  const navigate = useNavigate();

  const handleDevLogin = () => {
    devLogin();
    navigate('/vendor', { replace: true });
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
          <p className="ty-login-sub">Login system is being configured</p>
        </div>

        <div className="ty-login-sep" />

        {/* Coming soon notice */}
        <div style={{
          background: 'rgba(245, 158, 11, 0.1)',
          border: '1px solid rgba(245, 158, 11, 0.25)',
          borderRadius: 10,
          padding: '14px 16px',
          display: 'flex',
          gap: 10,
          alignItems: 'flex-start',
          marginBottom: 20,
        }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0, marginTop: 1 }}>
            <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          <span style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
            Vendor login (OTP / email) is under setup.<br />
            Use the dev bypass below to access the portal.
          </span>
        </div>

        <button className="ty-login-btn" onClick={handleDevLogin}>
          Continue as Vendor (Dev)
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M5 12h14M12 5l7 7-7 7"/>
          </svg>
        </button>

        <p className="ty-login-footer" style={{ marginTop: 20 }}>
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
          Real auth will be wired once login method is finalised
        </p>
      </div>
    </div>
  );
}
