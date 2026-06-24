import { NavLink, useLocation } from 'react-router-dom';
import logoSrc from '../../../assets/logo.png';
import { useAdminAuth } from '../../context/AuthContext';

const NAV = [
  {
    section: 'Overview',
    items: [
      { to: '/admin', label: 'Dashboard', icon: '⬡', exact: true },
      { to: '/admin/search', label: 'Global Search', icon: '⌕' },
    ],
  },
  {
    section: 'CRM',
    items: [
      { to: '/admin/vendors', label: 'Vendor CRM', icon: '🏪' },
      { to: '/admin/customers', label: 'Customer CRM', icon: '👥' },
    ],
  },
  {
    section: 'Operations',
    items: [
      { to: '/admin/bookings', label: 'Bookings', icon: '📅' },
      { to: '/admin/packages', label: 'Packages', icon: '📦' },
      { to: '/admin/occasions', label: 'Occasions', icon: '🎉' },
    ],
  },
  {
    section: 'Finance',
    items: [
      { to: '/admin/payments', label: 'Payments', icon: '💳' },
      { to: '/admin/wallets', label: 'Wallets', icon: '👛' },
      { to: '/admin/memberships', label: 'Memberships', icon: '⭐' },
    ],
  },
  {
    section: 'Engagement',
    items: [
      { to: '/admin/notifications', label: 'Notifications', icon: '🔔' },
      { to: '/admin/support', label: 'Support', icon: '🎧' },
      { to: '/admin/media', label: 'Media', icon: '🖼️' },
    ],
  },
  {
    section: 'Platform',
    items: [
      { to: '/admin/io', label: 'Import / Export', icon: '⇅' },
      { to: '/admin/automation', label: 'Automation', icon: '⚡' },
      { to: '/admin/settings', label: 'Settings', icon: '⚙' },
    ],
  },
  {
    section: 'Admin',
    superAdmin: true,
    items: [
      { to: '/admin/admin-management', label: 'Team & Roles', icon: '🛡' },
    ],
  },
];

export default function Sidebar({ collapsed, onToggle }) {
  const { admin, isSuperAdmin, logout } = useAdminAuth();
  const location = useLocation();

  return (
    <aside className={`admin-sidebar${collapsed ? ' collapsed' : ''}`}>
      <div className="admin-sidebar-logo">
        <img src={logoSrc} alt="Tyohaar" style={{ height: 28, width: 'auto', flexShrink: 0 }} />
        {!collapsed && <span className="logo-text">Tyohaar</span>}
        <button className="sidebar-toggle" onClick={onToggle} title={collapsed ? 'Expand' : 'Collapse'}>
          {collapsed ? '›' : '‹'}
        </button>
      </div>

      <nav className="admin-sidebar-nav">
        {NAV.map((group) => {
          if (group.superAdmin && !isSuperAdmin) return null;
          return (
            <div className="admin-nav-section" key={group.section}>
              <div className="admin-nav-section-label">{group.section}</div>
              {group.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.exact}
                  className={({ isActive }) =>
                    `admin-nav-item${isActive ? ' active' : ''}`
                  }
                  title={collapsed ? item.label : undefined}
                >
                  <span className="nav-icon" style={{ fontSize: 16 }}>{item.icon}</span>
                  {!collapsed && <span className="nav-label">{item.label}</span>}
                </NavLink>
              ))}
            </div>
          );
        })}
      </nav>

      <div className="admin-sidebar-footer">
        {!collapsed && admin && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 8px', marginBottom: 4 }}>
            <div className="admin-avatar" style={{ background: 'var(--brand-700)', color: 'white', fontSize: 11 }}>
              {admin.full_name?.[0] ?? admin.email?.[0]?.toUpperCase() ?? 'A'}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 12.5, fontWeight: 600, color: 'white', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {admin.full_name ?? 'Admin'}
              </div>
              <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {admin.role ?? ''}
              </div>
            </div>
          </div>
        )}
        <button
          className="admin-nav-item"
          onClick={logout}
          style={{ width: '100%', color: 'rgba(255,100,100,0.8)' }}
          title="Logout"
        >
          <span className="nav-icon" style={{ fontSize: 16 }}>⎋</span>
          {!collapsed && <span className="nav-label">Logout</span>}
        </button>
      </div>
    </aside>
  );
}
