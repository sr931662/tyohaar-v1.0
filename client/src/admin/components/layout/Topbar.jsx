import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAdminAuth } from '../../context/AuthContext';
import { useAdminTheme } from '../../hooks/useTheme';

export default function Topbar({ sidebarCollapsed, onToggleSidebar }) {
  const { admin } = useAdminAuth();
  const { theme, toggle } = useAdminTheme();
  const [search, setSearch] = useState('');
  const navigate = useNavigate();

  const handleSearch = (e) => {
    if (e.key === 'Enter' && search.trim()) {
      navigate(`/admin/search?q=${encodeURIComponent(search.trim())}`);
      setSearch('');
    }
  };

  return (
    <header className="admin-topbar">
      <div className="admin-topbar-left">
        {/* Mobile / extra toggle */}
        <button className="btn btn-ghost btn-icon" onClick={onToggleSidebar} style={{ display: 'none' }}>
          ☰
        </button>

        {/* Global search */}
        <div className="admin-search-bar" style={{ maxWidth: 340 }}>
          <span style={{ color: 'var(--text-tertiary)', fontSize: 14 }}>⌕</span>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={handleSearch}
            placeholder="Search users, vendors, bookings… (↵)"
          />
          <span style={{ color: 'var(--text-tertiary)', fontSize: 11, background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', borderRadius: 4, padding: '1px 5px' }}>⌘K</span>
        </div>
      </div>

      <div className="admin-topbar-right">
        {/* Theme toggle */}
        <button className="btn btn-ghost btn-icon" onClick={toggle} title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}>
          {theme === 'light' ? '🌙' : '☀️'}
        </button>

        {/* Notifications shortcut */}
        <button className="btn btn-ghost btn-icon" onClick={() => navigate('/admin/notifications')} title="Notifications">
          🔔
        </button>

        {/* User avatar */}
        {admin && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: 4, cursor: 'pointer' }}>
            <div className="admin-avatar" style={{ background: 'var(--brand-600)', color: 'white', fontSize: 12 }}>
              {admin.full_name?.[0] ?? admin.email?.[0]?.toUpperCase() ?? 'A'}
            </div>
            <div style={{ display: 'none' }} className="topbar-user-name">
              <span style={{ fontSize: 13, fontWeight: 600 }}>{admin.full_name ?? 'Admin'}</span>
            </div>
          </div>
        )}
      </div>
    </header>
  );
}
