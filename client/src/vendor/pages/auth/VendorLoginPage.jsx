import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { useVendorAuth } from '../../context/VendorAuthContext';
import { vendorAuthApi } from '../../api';
import logoSrc from '../../../assets/logo.png';
import '@/admin/admin.css';

export default function VendorLoginPage() {
  const { loginWithOtp } = useVendorAuth();
  const navigate = useNavigate();

  const [step, setStep] = useState('phone'); // 'phone' | 'otp'
  const [phone, setPhone] = useState('');
  const [otp, setOtp] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleRequestOtp = async (e) => {
    e.preventDefault();
    const cleaned = phone.replace(/\D/g, '');
    if (cleaned.length < 10) { setError('Enter a valid 10-digit mobile number.'); return; }
    setLoading(true);
    setError('');
    try {
      await vendorAuthApi.requestOtp(cleaned);
      toast.success('OTP sent to your number');
      setStep('otp');
    } catch (err) {
      const msg = err?.response?.data?.detail ?? err?.response?.data?.message ?? 'Failed to send OTP. Try again.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async (e) => {
    e.preventDefault();
    if (otp.length < 4) { setError('Enter the OTP you received.'); return; }
    setLoading(true);
    setError('');
    try {
      await loginWithOtp(phone.replace(/\D/g, ''), otp);
      toast.success('Welcome back!');
      navigate('/vendor', { replace: true });
    } catch (err) {
      const msg = err?.response?.data?.detail ?? err?.response?.data?.message ?? 'Invalid OTP. Please try again.';
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
          <p className="ty-login-sub">
            {step === 'phone' ? 'Enter your registered mobile number' : `Enter the OTP sent to +91 ${phone}`}
          </p>
        </div>

        <div className="ty-login-sep" />

        {step === 'phone' ? (
          <form onSubmit={handleRequestOtp} className="ty-login-form">
            {error && (
              <div className="ty-login-error">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
                </svg>
                {error}
              </div>
            )}
            <div className="ty-login-field">
              <label className="ty-login-label">Mobile Number<span className="ty-login-req">*</span></label>
              <div style={{ position: 'relative' }}>
                <span style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-tertiary)', fontSize: 13, pointerEvents: 'none' }}>+91</span>
                <input
                  type="tel"
                  className="ty-login-input"
                  placeholder="98765 43210"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  style={{ paddingLeft: 40 }}
                  maxLength={12}
                  autoFocus
                  disabled={loading}
                />
              </div>
            </div>
            <button type="submit" className="ty-login-btn" disabled={loading}>
              {loading ? <><span className="ty-login-spinner" /> Sending OTP…</> : <>Send OTP <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg></>}
            </button>
          </form>
        ) : (
          <form onSubmit={handleVerifyOtp} className="ty-login-form">
            {error && (
              <div className="ty-login-error">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
                </svg>
                {error}
              </div>
            )}
            <div className="ty-login-field">
              <label className="ty-login-label">One-Time Password<span className="ty-login-req">*</span></label>
              <input
                type="text"
                className="ty-login-input"
                placeholder="• • • • • •"
                value={otp}
                onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                autoFocus
                inputMode="numeric"
                autoComplete="one-time-code"
                style={{ letterSpacing: 8, fontSize: 20, textAlign: 'center' }}
                disabled={loading}
              />
            </div>
            <button type="submit" className="ty-login-btn" disabled={loading}>
              {loading ? <><span className="ty-login-spinner" /> Verifying…</> : <>Verify & Sign In <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg></>}
            </button>
            <button
              type="button"
              onClick={() => { setStep('phone'); setError(''); setOtp(''); }}
              style={{ background: 'none', border: 'none', color: 'var(--text-tertiary)', fontSize: 12, cursor: 'pointer', textAlign: 'center', width: '100%', marginTop: 4 }}
            >
              ← Change number
            </button>
          </form>
        )}

        <p className="ty-login-footer">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
          </svg>
          Tyohaar Vendor Portal · Secure OTP access
        </p>
      </div>
    </div>
  );
}
