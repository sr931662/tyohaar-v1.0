import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { vendorAuthApi } from '../../api';
import { useVendorAuth } from '../../context/VendorAuthContext';
import GoogleSignInButton from '../../components/GoogleSignInButton';
import logoSrc from '../../../assets/logo.png';
import '@/admin/admin.css';

const VENDOR_TYPES = [
  { value: 'decorator', label: 'Decorator' },
  { value: 'caterer', label: 'Caterer' },
  { value: 'photographer', label: 'Photographer' },
  { value: 'videographer', label: 'Videographer' },
  { value: 'baker', label: 'Baker' },
  { value: 'florist', label: 'Florist' },
  { value: 'entertainer', label: 'Entertainer' },
  { value: 'venue', label: 'Venue' },
  { value: 'planner', label: 'Event Planner' },
  { value: 'makeup_artist', label: 'Makeup Artist' },
  { value: 'mehndi_artist', label: 'Mehndi Artist' },
  { value: 'music', label: 'Music' },
  { value: 'multi_service', label: 'Multi-Service' },
  { value: 'other', label: 'Other' },
];

export default function VendorRegisterPage() {
  const { loginWithGoogle } = useVendorAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({
    fullName: '',
    email: '',
    phone: '',
    businessName: '',
    vendorType: '',
    password: '',
    confirmPassword: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const update = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }));

  const validate = () => {
    if (!form.fullName || !form.email || !form.phone || !form.businessName || !form.vendorType || !form.password) {
      return 'All fields are required.';
    }
    if (form.password.length < 8) return 'Password must be at least 8 characters.';
    if (form.password !== form.confirmPassword) return 'Passwords do not match.';
    if (!/^\+?[0-9]{10,15}$/.test(form.phone.trim())) return 'Enter a valid phone number (e.g. +919876543210).';
    return '';
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const validationError = validate();
    if (validationError) { setError(validationError); return; }

    setLoading(true);
    setError('');
    try {
      const phone = form.phone.trim().startsWith('+') ? form.phone.trim() : `+91${form.phone.trim()}`;
      await vendorAuthApi.register({
        email: form.email.trim().toLowerCase(),
        password: form.password,
        full_name: form.fullName.trim(),
        phone,
        business_name: form.businessName.trim(),
        vendor_type: form.vendorType,
      });
      setSubmitted(true);
    } catch (err) {
      const msg = err?.response?.data?.detail ?? err?.response?.data?.message ?? 'Registration failed. Please try again.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleCredential = async (idToken) => {
    setError('');
    setLoading(true);
    try {
      const result = await loginWithGoogle(idToken, true);
      if (result.pending) {
        setSubmitted(true);
      } else {
        toast.success('Welcome back!');
        navigate('/vendor', { replace: true });
      }
    } catch (err) {
      const msg = err?.response?.data?.detail ?? err?.response?.data?.message ?? 'Google sign-up failed.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return (
      <div className="ty-login-root">
        <div className="ty-login-card">
          <div className="ty-login-brand">
            <img src={logoSrc} alt="" className="ty-login-emblem" />
            <span className="ty-login-wordmark">Tyohaar</span>
          </div>
          <div className="ty-login-header">
            <h1 className="ty-login-title">Registration submitted</h1>
            <p className="ty-login-sub">
              Thanks for registering! Our team will review your business details and activate
              your account shortly. You'll be able to sign in once it's approved.
            </p>
          </div>
          <div className="ty-login-sep" />
          <Link to="/vendor/login" className="ty-login-btn" style={{ textDecoration: 'none' }}>
            Back to sign in
          </Link>
        </div>
      </div>
    );
  }

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
            Vendor registration
          </div>
          <h1 className="ty-login-title">Become a Tyohaar Vendor</h1>
          <p className="ty-login-sub">Create your business account to start listing packages</p>
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
            <label className="ty-login-label">Full name<span className="ty-login-req">*</span></label>
            <input className="ty-login-input" value={form.fullName} onChange={update('fullName')} placeholder="Your name" disabled={loading} autoComplete="name" />
          </div>

          <div className="ty-login-field">
            <label className="ty-login-label">Email address<span className="ty-login-req">*</span></label>
            <input type="email" className="ty-login-input" value={form.email} onChange={update('email')} placeholder="vendor@example.com" disabled={loading} autoComplete="email" />
          </div>

          <div className="ty-login-field">
            <label className="ty-login-label">Phone number<span className="ty-login-req">*</span></label>
            <input className="ty-login-input" value={form.phone} onChange={update('phone')} placeholder="+919876543210" disabled={loading} autoComplete="tel" />
          </div>

          <div className="ty-login-field">
            <label className="ty-login-label">Business name<span className="ty-login-req">*</span></label>
            <input className="ty-login-input" value={form.businessName} onChange={update('businessName')} placeholder="Your business/brand name" disabled={loading} />
          </div>

          <div className="ty-login-field">
            <label className="ty-login-label">Service category<span className="ty-login-req">*</span></label>
            <select className="ty-login-input" value={form.vendorType} onChange={update('vendorType')} disabled={loading}>
              <option value="" disabled>Select a category</option>
              {VENDOR_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>

          <div className="ty-login-field">
            <label className="ty-login-label">Password<span className="ty-login-req">*</span></label>
            <input type="password" className="ty-login-input" value={form.password} onChange={update('password')} placeholder="At least 8 characters" disabled={loading} autoComplete="new-password" />
          </div>

          <div className="ty-login-field">
            <label className="ty-login-label">Confirm password<span className="ty-login-req">*</span></label>
            <input type="password" className="ty-login-input" value={form.confirmPassword} onChange={update('confirmPassword')} placeholder="Re-enter password" disabled={loading} autoComplete="new-password" />
          </div>

          <button type="submit" className="ty-login-btn" disabled={loading}>
            {loading ? (
              <><span className="ty-login-spinner" /> Submitting…</>
            ) : (
              <>Create Vendor Account <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg></>
            )}
          </button>
        </form>

        <div className="ty-login-divider">or</div>
        <GoogleSignInButton onCredential={handleGoogleCredential} label="Sign up with Google" disabled={loading} />

        <div className="ty-login-links ty-login-links--center" style={{ marginTop: 20 }}>
          <span className="ty-login-muted">Already registered?</span>
          <Link to="/vendor/login" className="ty-login-link">Sign in</Link>
        </div>
      </div>
    </div>
  );
}
