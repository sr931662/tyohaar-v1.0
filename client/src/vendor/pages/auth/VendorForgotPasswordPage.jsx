import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { vendorAuthApi } from '../../api';
import logoSrc from '../../../assets/logo.png';
import '@/admin/admin.css';

export default function VendorForgotPasswordPage() {
  const navigate = useNavigate();

  const [step, setStep] = useState('request'); // 'request' | 'confirm'
  const [email, setEmail] = useState('');
  const [otpCode, setOtpCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleRequestOtp = async (e) => {
    e.preventDefault();
    if (!email) { setError('Email is required.'); return; }
    setLoading(true);
    setError('');
    try {
      await vendorAuthApi.requestPasswordResetOtp(email.trim().toLowerCase());
      toast.success('OTP sent to your email address.');
      setStep('confirm');
    } catch (err) {
      const msg = err?.response?.data?.detail ?? err?.response?.data?.message ?? 'Could not send OTP. Please try again.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmReset = async (e) => {
    e.preventDefault();
    if (!otpCode || !newPassword) { setError('OTP and new password are required.'); return; }
    if (newPassword.length < 8) { setError('Password must be at least 8 characters.'); return; }
    if (newPassword !== confirmPassword) { setError('Passwords do not match.'); return; }
    setLoading(true);
    setError('');
    try {
      await vendorAuthApi.resetPassword(email.trim().toLowerCase(), otpCode.trim(), newPassword);
      toast.success('Password reset successfully. Please sign in.');
      navigate('/vendor/login', { replace: true });
    } catch (err) {
      const msg = err?.response?.data?.detail ?? err?.response?.data?.message ?? 'Invalid or expired OTP.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    setLoading(true);
    setError('');
    try {
      await vendorAuthApi.requestPasswordResetOtp(email.trim().toLowerCase());
      toast.success('A new OTP has been sent.');
    } catch (err) {
      const msg = err?.response?.data?.detail ?? err?.response?.data?.message ?? 'Could not resend OTP.';
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
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
            </svg>
            Password recovery
          </div>
          <h1 className="ty-login-title">Forgot password?</h1>
          <p className="ty-login-sub">
            {step === 'request'
              ? "Enter your vendor account's email and we'll send a one-time code to verify it's you."
              : `Enter the OTP sent to ${email} and choose a new password.`}
          </p>
        </div>

        <div className="ty-login-sep" />

        {step === 'request' ? (
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
            <button type="submit" className="ty-login-btn" disabled={loading}>
              {loading ? (<><span className="ty-login-spinner" /> Sending…</>) : 'Send OTP'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleConfirmReset} className="ty-login-form">
            {error && (
              <div className="ty-login-error">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
                </svg>
                {error}
              </div>
            )}
            <div className="ty-login-field">
              <label className="ty-login-label">OTP code<span className="ty-login-req">*</span></label>
              <input
                className="ty-login-input"
                placeholder="6-digit code"
                inputMode="numeric"
                value={otpCode}
                onChange={(e) => setOtpCode(e.target.value)}
                autoFocus
                disabled={loading}
              />
            </div>
            <div className="ty-login-field">
              <label className="ty-login-label">New password<span className="ty-login-req">*</span></label>
              <input
                type="password"
                className="ty-login-input"
                placeholder="At least 8 characters"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                autoComplete="new-password"
                disabled={loading}
              />
            </div>
            <div className="ty-login-field">
              <label className="ty-login-label">Confirm new password<span className="ty-login-req">*</span></label>
              <input
                type="password"
                className="ty-login-input"
                placeholder="Re-enter password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                autoComplete="new-password"
                disabled={loading}
              />
            </div>
            <button type="submit" className="ty-login-btn" disabled={loading}>
              {loading ? (<><span className="ty-login-spinner" /> Resetting…</>) : 'Reset password'}
            </button>
            <div className="ty-login-links ty-login-links--center" style={{ marginTop: 14 }}>
              <button type="button" className="ty-login-link" onClick={handleResend} disabled={loading}>
                Resend OTP
              </button>
              <span className="ty-login-muted">·</span>
              <button type="button" className="ty-login-link" onClick={() => setStep('request')} disabled={loading}>
                Change email
              </button>
            </div>
          </form>
        )}

        <div className="ty-login-links ty-login-links--center" style={{ marginTop: 20 }}>
          <Link to="/vendor/login" className="ty-login-link">Back to sign in</Link>
        </div>
      </div>
    </div>
  );
}
