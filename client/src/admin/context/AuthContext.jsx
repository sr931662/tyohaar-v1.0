import { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { authApi } from '../api';

const AuthContext = createContext(null);

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
      .catch(() => {
        localStorage.removeItem('admin_token');
        localStorage.removeItem('admin_user');
        sessionStorage.removeItem('admin_token');
        sessionStorage.removeItem('admin_user');
        setAdmin(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email, password, remember = true) => {
    const data = await authApi.login(email, password);
    const token = data.access_token ?? data.token;
    const store = remember ? localStorage : sessionStorage;
    if (token) store.setItem('admin_token', token);
    const adminData = data.admin ?? data;
    setAdmin(adminData);
    store.setItem('admin_user', JSON.stringify(adminData));
    return adminData;
  }, []);

  const logout = useCallback(async () => {
    try { await authApi.logout(); } catch { /* ignore */ }
    localStorage.removeItem('admin_token');
    localStorage.removeItem('admin_user');
    sessionStorage.removeItem('admin_token');
    sessionStorage.removeItem('admin_user');
    setAdmin(null);
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
    <AuthContext.Provider value={{ admin, loading, login, logout, hasPermission, isSuperAdmin, isAdmin }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAdminAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAdminAuth must be used within AdminAuthProvider');
  return ctx;
}
