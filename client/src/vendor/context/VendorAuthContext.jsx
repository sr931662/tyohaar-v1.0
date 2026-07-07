import { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { vendorAuthApi } from '../api';

const VendorAuthContext = createContext(null);

function clearStoredSession() {
  localStorage.removeItem('vendor_token');
  localStorage.removeItem('vendor_refresh_token');
  localStorage.removeItem('vendor_user');
  sessionStorage.removeItem('vendor_token');
  sessionStorage.removeItem('vendor_refresh_token');
  sessionStorage.removeItem('vendor_user');
}

function storeTokens(store, data) {
  if (data.access_token) store.setItem('vendor_token', data.access_token);
  if (data.refresh_token) store.setItem('vendor_refresh_token', data.refresh_token);
}

// Merge the personal-profile photo (stored on UserProfile, not User) onto the
// user object so sidebars/avatars can read `user.profile_photo_url` directly.
async function fetchFullUser() {
  const userData = await vendorAuthApi.me();
  try {
    const profile = await vendorAuthApi.getUserProfile(userData.id);
    return { ...userData, profile_photo_url: profile?.profile_photo_url ?? null };
  } catch {
    return userData;
  }
}

export function VendorAuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const stored = localStorage.getItem('vendor_user') || sessionStorage.getItem('vendor_user');
      return JSON.parse(stored ?? 'null');
    } catch {
      return null;
    }
  });
  const [loading, setLoading] = useState(true);

  const getStore = () => (localStorage.getItem('vendor_token') ? localStorage : sessionStorage);

  useEffect(() => {
    const token = localStorage.getItem('vendor_token') || sessionStorage.getItem('vendor_token');
    if (!token) { setLoading(false); return; }

    fetchFullUser()
      .then((data) => {
        setUser(data);
        getStore().setItem('vendor_user', JSON.stringify(data));
      })
      .catch((err) => {
        // The vendorClient interceptor already tried a token refresh before
        // this rejection reaches us, so a 401 here means the session is
        // genuinely dead — sign out. Any OTHER failure (network drop, a
        // Cloud Run cold-start timeout, a transient 502/503 while the
        // instance spins back up from zero) is NOT proof the session is
        // invalid; wiping the stored tokens on those would force a real
        // login every time the instance had scaled down. Keep the cached
        // session and let the next successful request confirm it.
        if (err?.response?.status === 401) {
          clearStoredSession();
          setUser(null);
        }
      })
      .finally(() => setLoading(false));
  }, []);

  const loginWithPassword = useCallback(async (email, password, remember = true) => {
    const data = await vendorAuthApi.loginWithPassword(email, password);
    const store = remember ? localStorage : sessionStorage;
    storeTokens(store, data);
    const userData = await fetchFullUser();
    setUser(userData);
    store.setItem('vendor_user', JSON.stringify(userData));
    return userData;
  }, []);

  const loginWithGoogle = useCallback(async (idToken, remember = true) => {
    const data = await vendorAuthApi.loginWithGoogle(idToken);
    if (!data.access_token) {
      // New or not-yet-approved account — nothing to log in to yet.
      return { pending: true };
    }
    const store = remember ? localStorage : sessionStorage;
    storeTokens(store, data);
    const userData = await fetchFullUser();
    setUser(userData);
    store.setItem('vendor_user', JSON.stringify(userData));
    return { pending: false, user: userData };
  }, []);

  const logout = useCallback(async () => {
    try { await vendorAuthApi.logout(); } catch { /* ignore */ }
    clearStoredSession();
    setUser(null);
  }, []);

  // Re-fetch the current user (e.g. after updating the profile photo) so
  // sidebars/avatars reflect the change without a full page reload.
  const refreshUser = useCallback(async () => {
    const userData = await fetchFullUser();
    setUser(userData);
    getStore().setItem('vendor_user', JSON.stringify(userData));
    return userData;
  }, []);

  return (
    <VendorAuthContext.Provider value={{ user, loading, loginWithPassword, loginWithGoogle, logout, refreshUser }}>
      {children}
    </VendorAuthContext.Provider>
  );
}

export function useVendorAuth() {
  const ctx = useContext(VendorAuthContext);
  if (!ctx) throw new Error('useVendorAuth must be used within VendorAuthProvider');
  return ctx;
}
