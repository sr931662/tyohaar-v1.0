import { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { authApi } from '../api';

const AuthContext = createContext(null);

function clearStoredSession() {
  localStorage.removeItem('admin_token');
  localStorage.removeItem('admin_refresh_token');
  localStorage.removeItem('admin_user');
  sessionStorage.removeItem('admin_token');
  sessionStorage.removeItem('admin_refresh_token');
  sessionStorage.removeItem('admin_user');
}

export function AdminAuthProvider({ children }) {
  const [admin, setAdmin] = useState(() => {
    try {
      const stored = localStorage.getItem('admin_user') || sessionStorage.getItem('admin_user');
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('admin_token') || sessionStorage.getItem('admin_token');
    if (!token) { setLoading(false); return; }

    const store = localStorage.getItem('admin_token') ? localStorage : sessionStorage;
    authApi.me()
      .then((data) => {
        setAdmin(data);
        store.setItem('admin_user', JSON.stringify(data));
      })
      .catch((err) => {
        // The apiClient interceptor already tried a token refresh before this
        // rejection reaches us, so a 401 here means the session is genuinely
        // dead — sign out. Any OTHER failure (network drop, a Cloud Run
        // cold-start timeout, a transient 502/503 while the instance spins
        // back up from zero) is NOT proof the session is invalid; wiping the
        // stored tokens on those would force a real login every time the
        // instance had scaled down. Keep the cached session and let the next
        // successful request confirm it.
        if (err?.response?.status === 401) {
          clearStoredSession();
          setAdmin(null);
        }
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email, password, remember = true) => {
    const data = await authApi.login(email, password);
    const token = data.access_token ?? data.token;
    const store = remember ? localStorage : sessionStorage;
    if (token) store.setItem('admin_token', token);
    if (data.refresh_token) store.setItem('admin_refresh_token', data.refresh_token);
    const adminData = data.admin ?? data;
    setAdmin(adminData);
    store.setItem('admin_user', JSON.stringify(adminData));
    return adminData;
  }, []);

  const logout = useCallback(async () => {
    try { await authApi.logout(); } catch { /* ignore */ }
    clearStoredSession();
    setAdmin(null);
  }, []);

  // Re-fetch the current admin (e.g. after updating the profile photo) so
  // the topbar avatar reflects the change without a full page reload.
  const refreshAdmin = useCallback(async () => {
    const data = await authApi.me();
    setAdmin(data);
    const store = localStorage.getItem('admin_token') ? localStorage : sessionStorage;
    store.setItem('admin_user', JSON.stringify(data));
    return data;
  }, []);

  const hasPermission = useCallback((permission) => {
    if (!admin) return false;
    if (admin.role === 'super_admin') return true;
    const perms = admin.permissions ?? admin.role_permissions ?? [];
    return perms.includes(permission);
  }, [admin]);

  const isSuperAdmin = admin?.role === 'super_admin';
  const isAdmin = !!admin;

  return (
    <AuthContext.Provider value={{ admin, loading, login, logout, hasPermission, isSuperAdmin, isAdmin, refreshAdmin }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAdminAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAdminAuth must be used within AdminAuthProvider');
  return ctx;
}
