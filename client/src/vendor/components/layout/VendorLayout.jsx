import { useState, Suspense } from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { useVendorAuth } from '../../context/VendorAuthContext';
import { useAdminTheme } from '../../../admin/hooks/useTheme';
import VendorSidebar from './VendorSidebar';
import '@/admin/admin.css';

const PAGE_VARIANTS = {
  initial: { opacity: 0, y: 10 },
  enter:   { opacity: 1, y: 0  },
  exit:    { opacity: 0, y: -6 },
};
const PAGE_TRANSITION = { duration: 0.18, ease: [0.4, 0, 0.2, 1] };

function PageLoader() {
  return (
    <div style={{ padding: 32 }}>
      <div style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="skeleton skeleton-card" style={{ height: 92, flex: 1 }} />
        ))}
      </div>
      <div className="skeleton skeleton-card" style={{ height: 240, marginBottom: 16 }} />
    </div>
  );
}

function VendorTopbar({ onToggleSidebar }) {
  const { user } = useVendorAuth();
  const { theme, toggle } = useAdminTheme();

  const initials = user?.full_name
    ? user.full_name.split(' ').map((w) => w[0]).join('').slice(0, 2).toUpperCase()
    : 'V';

  return (
    <header className="admin-topbar">
      <div className="admin-topbar-left">
        <button className="btn btn-ghost btn-icon" onClick={onToggleSidebar} title="Toggle sidebar" style={{ display: 'none' }}>
          ☰
        </button>
      </div>
      <div className="admin-topbar-right">
        <button className="btn btn-ghost btn-icon" onClick={toggle} title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}>
          {theme === 'light' ? '🌙' : '☀️'}
        </button>
        {user && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: 4 }}>
            <div className="admin-avatar" style={{ background: 'var(--brand-600)', color: 'white', fontSize: 12 }}>
              {initials}
            </div>
            <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', maxWidth: 140, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {user.full_name ?? user.email ?? 'Vendor'}
            </div>
          </div>
        )}
      </div>
    </header>
  );
}

export default function VendorLayout() {
  const { user, loading } = useVendorAuth();
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();

  if (loading) {
    return (
      <div className="admin-root" style={{ alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}>
        <div className="spinner" style={{ width: 32, height: 32, borderWidth: 3 }} />
      </div>
    );
  }

  if (!user) return <Navigate to="/vendor/login" replace />;

  return (
    <div className="admin-root">
      <VendorSidebar collapsed={collapsed} onToggle={() => setCollapsed((c) => !c)} />
      <main className={`admin-main${collapsed ? ' sidebar-collapsed' : ''}`}>
        <VendorTopbar onToggleSidebar={() => setCollapsed((c) => !c)} />
        <div className="admin-content">
          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={location.pathname}
              variants={PAGE_VARIANTS}
              initial="initial"
              animate="enter"
              exit="exit"
              transition={PAGE_TRANSITION}
            >
              <Suspense fallback={<PageLoader />}>
                <Outlet />
              </Suspense>
            </motion.div>
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}
