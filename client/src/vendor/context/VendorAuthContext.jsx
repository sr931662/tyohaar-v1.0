import { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { vendorAuthApi } from '../api';

const VendorAuthContext = createContext(null);

// Placeholder used when real auth is bypassed in dev mode
const DEV_USER = {
  id: 'dev-vendor-user',
  full_name: 'Dev Vendor',
  phone: '+910000000000',
  role: 'vendor',
  __dev: true,
};

export function VendorAuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('vendor_user') ?? 'null');
    } catch {
      return null;
    }
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem('vendor_user');
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        // Dev user — skip token verification
        if (parsed?.__dev) { setUser(parsed); setLoading(false); return; }
      } catch { /* fall through */ }
    }

    const token = localStorage.getItem('vendor_token');
    if (!token) { setLoading(false); return; }

    vendorAuthApi.me()
      .then((data) => {
        setUser(data);
        localStorage.setItem('vendor_user', JSON.stringify(data));
      })
      .catch(() => {
        localStorage.removeItem('vendor_token');
        localStorage.removeItem('vendor_user');
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  // Real OTP login — wire up when auth method is finalised
  const loginWithOtp = useCallback(async (phone, otp) => {
    const data = await vendorAuthApi.verifyOtp(phone, otp);
    const token = data.access_token ?? data.token;
    if (token) localStorage.setItem('vendor_token', token);
    const userData = await vendorAuthApi.me();
    setUser(userData);
    localStorage.setItem('vendor_user', JSON.stringify(userData));
    return userData;
  }, []);

  // Dev bypass — no API call, sets a placeholder user
  const devLogin = useCallback(() => {
    setUser(DEV_USER);
    localStorage.setItem('vendor_user', JSON.stringify(DEV_USER));
  }, []);

  const logout = useCallback(async () => {
    if (!user?.__dev) {
      try { await vendorAuthApi.logout(); } catch { /* ignore */ }
    }
    localStorage.removeItem('vendor_token');
    localStorage.removeItem('vendor_user');
    setUser(null);
  }, [user]);

  return (
    <VendorAuthContext.Provider value={{ user, loading, loginWithOtp, devLogin, logout }}>
      {children}
    </VendorAuthContext.Provider>
  );
}

export function useVendorAuth() {
  const ctx = useContext(VendorAuthContext);
  if (!ctx) throw new Error('useVendorAuth must be used within VendorAuthProvider');
  return ctx;
}
