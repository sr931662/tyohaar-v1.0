import { useState } from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAdminAuth } from '../../context/AuthContext';
import Sidebar from './Sidebar';
import Topbar from './Topbar';
import '../../admin.css';

export default function AdminLayout() {
  const { admin, loading } = useAdminAuth();
  const [collapsed, setCollapsed] = useState(false);

  if (loading) {
    return (
      <div className="admin-root" style={{ alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}>
        <div className="spinner" style={{ width: 32, height: 32, borderWidth: 3 }} />
      </div>
    );
  }

  if (!admin) {
    return <Navigate to="/admin/login" replace />;
  }

  return (
    <div className="admin-root">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((c) => !c)} />
      <main className={`admin-main${collapsed ? ' sidebar-collapsed' : ''}`}>
        <Topbar sidebarCollapsed={collapsed} onToggleSidebar={() => setCollapsed((c) => !c)} />
        <div className="admin-content">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
