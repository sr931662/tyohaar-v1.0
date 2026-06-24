import { NavLink } from 'react-router-dom';
import { useVendorAuth } from '../../context/VendorAuthContext';
import logoSrc from '../../../assets/logo.png';

const NAV = [
  {
    label: 'Overview',
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>
      </svg>
    ),
    to: '/vendor',
    end: true,
  },
  {
    label: 'My Profile',
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
      </svg>
    ),
    to: '/vendor/profile',
  },
  {
    label: 'My Packages',
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
      </svg>
    ),
    to: '/vendor/packages',
  },
];

export default function VendorSidebar({ collapsed, onToggle }) {
  const { user, logout } = useVendorAuth();

  return (
    <aside className={`admin-sidebar${collapsed ? ' collapsed' : ''}`}>
      <div className="admin-sidebar-brand">
        {!collapsed && (
          <>
            <img src={logoSrc} alt="" style={{ width: 28, height: 28, objectFit: 'contain' }} />
            <span className="admin-sidebar-brand-name">Vendor Portal</span>
          </>
        )}
        <button className="admin-sidebar-toggle" onClick={onToggle} title="Toggle sidebar">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            {collapsed
              ? <><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></>
              : <><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></>
            }
          </svg>
        </button>
      </div>

      <nav className="admin-sidebar-nav">
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) => `admin-sidebar-link${isActive ? ' active' : ''}`}
            title={collapsed ? item.label : undefined}
          >
            <span className="admin-sidebar-icon">{item.icon}</span>
            {!collapsed && <span className="admin-sidebar-label">{item.label}</span>}
          </NavLink>
        ))}
      </nav>

      <div className="admin-sidebar-footer">
        {!collapsed && user && (
          <div className="admin-sidebar-user-name" style={{ padding: '0 12px 4px', fontSize: 12, color: 'var(--text-tertiary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {user.full_name ?? user.phone ?? 'Vendor'}
          </div>
        )}
        <button className="admin-sidebar-link" onClick={logout} style={{ width: '100%', textAlign: 'left', border: 'none', background: 'none', cursor: 'pointer', color: 'var(--text-secondary)' }} title={collapsed ? 'Logout' : undefined}>
          <span className="admin-sidebar-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>
            </svg>
          </span>
          {!collapsed && <span className="admin-sidebar-label">Logout</span>}
        </button>
      </div>
    </aside>
  );
}
