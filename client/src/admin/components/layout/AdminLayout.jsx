import { useState, useEffect, Suspense } from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { useAdminAuth } from '../../context/AuthContext';
import Sidebar from './Sidebar';
import Topbar from './Topbar';
import '../../admin.css';

const PAGE_VARIANTS = {
  initial: { opacity: 0, y: 10 },
  enter:   { opacity: 1, y: 0  },
  exit:    { opacity: 0, y: -6 },
};

const PAGE_TRANSITION = { duration: 0.18, ease: [0.4, 0, 0.2, 1] };

function PageLoader() {
  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="skeleton skeleton-card" style={{ height: 92, flex: 1 }} />
        ))}
      </div>
      <div className="skeleton skeleton-card" style={{ height: 240, marginBottom: 16 }} />
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <div className="skeleton skeleton-card" style={{ height: 160 }} />
        <div className="skeleton skeleton-card" style={{ height: 160 }} />
      </div>
    </div>
  );
}

export default function AdminLayout() {
  const { admin, loading } = useAdminAuth();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const location = useLocation();

  // Close the mobile drawer automatically on navigation.
  useEffect(() => { setMobileNavOpen(false); }, [location.pathname]);

  if (loading) {
    return (
      <div className="admin-root" style={{ alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}>
        <div className="spinner" style={{ width: 32, height: 32, borderWidth: 3 }} />
      </div>
    );
  }

  if (!admin) {
    return <Navigate to="/workspace/login" replace />;
  }

  return (
    <div className="admin-root">
      <Sidebar
        collapsed={collapsed}
        onToggle={() => setCollapsed((c) => !c)}
        mobileOpen={mobileNavOpen}
        onCloseMobile={() => setMobileNavOpen(false)}
      />
      <div
        className={`admin-sidebar-scrim${mobileNavOpen ? ' mobile-open' : ''}`}
        onClick={() => setMobileNavOpen(false)}
      />
      <main className={`admin-main${collapsed ? ' sidebar-collapsed' : ''}`}>
        <Topbar
          sidebarCollapsed={collapsed}
          onToggleSidebar={() => setCollapsed((c) => !c)}
          onOpenMobileNav={() => setMobileNavOpen(true)}
        />
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
