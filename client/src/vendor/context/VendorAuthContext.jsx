import { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { vendorAuthApi } from '../api';

const VendorAuthContext = createContext(null);

export function VendorAuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const stored = localStorage.getItem('vendor_user');
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
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

  const loginWithOtp = useCallback(async (phone, otp) => {
    const data = await vendorAuthApi.verifyOtp(phone, otp);
    const token = data.access_token ?? data.token;
    if (token) localStorage.setItem('vendor_token', token);
    // Fetch user profile after login
    const userData = await vendorAuthApi.me();
    setUser(userData);
    localStorage.setItem('vendor_user', JSON.stringify(userData));
    return userData;
  }, []);

  const logout = useCallback(async () => {
    try { await vendorAuthApi.logout(); } catch { /* ignore */ }
    localStorage.removeItem('vendor_token');
    localStorage.removeItem('vendor_user');
    setUser(null);
  }, []);

  return (
    <VendorAuthContext.Provider value={{ user, loading, loginWithOtp, logout }}>
      {children}
    </VendorAuthContext.Provider>
  );
}

export function useVendorAuth() {
  const ctx = useContext(VendorAuthContext);
  if (!ctx) throw new Error('useVendorAuth must be used within VendorAuthProvider');
  return ctx;
}
