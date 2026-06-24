import { NavLink } from 'react-router-dom';
import { useVendorAuth } from '../../context/VendorAuthContext';
import logoSrc from '../../../assets/logo.png';

const NAV = [
  {
    section: 'Main',
    items: [
      {
        to: '/vendor',
        end: true,
        label: 'Overview',
        icon: (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>
          </svg>
        ),
      },
      {
        to: '/vendor/profile',
        label: 'My Profile',
        icon: (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
          </svg>
        ),
      },
      {
        to: '/vendor/packages',
        label: 'My Packages',
        icon: (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
          </svg>
        ),
      },
      {
        to: '/vendor/bank',
        label: 'Bank Accounts',
        icon: (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/>
          </svg>
        ),
      },
    ],
  },
];

export default function VendorSidebar({ collapsed, onToggle }) {
  const { user, logout } = useVendorAuth();

  const initials = user?.full_name
    ? user.full_name.split(' ').map((w) => w[0]).join('').slice(0, 2).toUpperCase()
    : 'V';

  return (
    <aside className={`admin-sidebar${collapsed ? ' collapsed' : ''}`}>
      {/* Brand */}
      <div className="admin-sidebar-logo">
        <img src={logoSrc} alt="Tyohaar" style={{ height: 28, width: 'auto', flexShrink: 0 }} />
        {!collapsed && <span className="logo-text">Vendor</span>}
        <button
          className="sidebar-toggle"
          onClick={onToggle}
          title={collapsed ? 'Expand' : 'Collapse'}
        >
          {collapsed ? '›' : '‹'}
        </button>
      </div>

      {/* Nav */}
      <nav className="admin-sidebar-nav">
        {NAV.map((group) => (
          <div className="admin-nav-section" key={group.section}>
            <div className="admin-nav-section-label">{group.section}</div>
            {group.items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) => `admin-nav-item${isActive ? ' active' : ''}`}
                title={collapsed ? item.label : undefined}
              >
                <span className="nav-icon">{item.icon}</span>
                {!collapsed && <span className="nav-label">{item.label}</span>}
              </NavLink>
            ))}
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="admin-sidebar-footer">
        {!collapsed && user && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 8px', marginBottom: 4 }}>
            <div className="admin-avatar" style={{ background: 'var(--brand-700)', color: 'white', fontSize: 11, flexShrink: 0 }}>
              {initials}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 12.5, fontWeight: 600, color: 'white', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {user.full_name ?? user.email ?? 'Vendor'}
              </div>
              <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>Vendor</div>
            </div>
          </div>
        )}
        <button
          className="admin-nav-item"
          onClick={logout}
          style={{ width: '100%', color: 'rgba(255,100,100,0.8)' }}
          title={collapsed ? 'Logout' : undefined}
        >
          <span className="nav-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>
            </svg>
          </span>
          {!collapsed && <span className="nav-label">Logout</span>}
        </button>
      </div>
    </aside>
  );
}
