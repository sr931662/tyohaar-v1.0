import { useState, Suspense } from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { useVendorAuth } from '../../context/VendorAuthContext';
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
        {[0, 1, 2].map((i) => (
          <div key={i} className="skeleton skeleton-card" style={{ height: 90, flex: 1 }} />
        ))}
      </div>
      <div className="skeleton skeleton-card" style={{ height: 220 }} />
    </div>
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
        <div className="admin-topbar" style={{ borderBottom: '1px solid var(--border-subtle)', padding: '0 24px', height: 52, display: 'flex', alignItems: 'center', gap: 12 }}>
          <button
            className="admin-topbar-btn"
            onClick={() => setCollapsed((c) => !c)}
            style={{ display: 'none' }}
          />
          <span style={{ fontSize: 13, color: 'var(--text-tertiary)' }}>
            Vendor Portal
          </span>
        </div>
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
