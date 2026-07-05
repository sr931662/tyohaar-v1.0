import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { useAdminAuth } from '../../context/AuthContext';
import { useAdminTheme } from '../../hooks/useTheme';
import { authApi } from '../../api';
import Modal from '../ui/Modal';
import ImageUploadField from '../ui/ImageUploadField';

export default function Topbar({ sidebarCollapsed, onToggleSidebar, onOpenMobileNav }) {
  const { admin, refreshAdmin } = useAdminAuth();
  const { theme, toggle } = useAdminTheme();
  const [search, setSearch] = useState('');
  const [photoModalOpen, setPhotoModalOpen] = useState(false);
  const [photoUrl, setPhotoUrl] = useState('');
  const [saving, setSaving] = useState(false);
  const navigate = useNavigate();

  const handleSearch = (e) => {
    if (e.key === 'Enter' && search.trim()) {
      navigate(`/admin/search?q=${encodeURIComponent(search.trim())}`);
      setSearch('');
    }
  };

  const openPhotoModal = () => {
    setPhotoUrl(admin?.profile_photo_url ?? '');
    setPhotoModalOpen(true);
  };

  const handleSavePhoto = async () => {
    setSaving(true);
    try {
      await authApi.updateUserProfile(admin.user_id, { profile_photo_url: photoUrl || undefined });
      await refreshAdmin();
      toast.success('Profile photo updated.');
      setPhotoModalOpen(false);
    } catch (err) {
      toast.error(err?.response?.data?.detail ?? 'Failed to update profile photo.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <header className="admin-topbar">
      <div className="admin-topbar-left">
        {/* Mobile menu — opens the sidebar as a full drawer; hidden on desktop */}
        <button className="btn btn-ghost btn-icon mobile-nav-toggle" onClick={onOpenMobileNav} aria-label="Open menu" title="Open menu">
          ☰
        </button>

        {/* Global search */}
        <div className="admin-search-bar admin-search-bar-desktop" style={{ maxWidth: 340 }}>
          <span style={{ color: 'var(--text-tertiary)', fontSize: 14 }}>⌕</span>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={handleSearch}
            placeholder="Search users, vendors, bookings… (↵)"
          />
          <span style={{ color: 'var(--text-tertiary)', fontSize: 11, background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', borderRadius: 4, padding: '1px 5px' }}>⌘K</span>
        </div>

        {/* Compact search entry point for narrow screens — the full bar above is hidden there */}
        <button
          className="btn btn-ghost btn-icon admin-search-btn-mobile"
          onClick={() => navigate('/admin/search')}
          aria-label="Search"
          title="Search"
        >
          ⌕
        </button>
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
          <div
            style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: 4, cursor: 'pointer' }}
            onClick={openPhotoModal}
            title="Change profile photo"
          >
            <div className="admin-avatar" style={{ background: 'var(--brand-600)', color: 'white', fontSize: 12, overflow: 'hidden' }}>
              {admin.profile_photo_url ? (
                <img src={admin.profile_photo_url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
              ) : (
                admin.full_name?.[0] ?? admin.email?.[0]?.toUpperCase() ?? 'A'
              )}
            </div>
            <div style={{ display: 'none' }} className="topbar-user-name">
              <span style={{ fontSize: 13, fontWeight: 600 }}>{admin.full_name ?? 'Admin'}</span>
            </div>
          </div>
        )}
      </div>

      <Modal
        open={photoModalOpen}
        onClose={() => setPhotoModalOpen(false)}
        title="Profile Photo"
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setPhotoModalOpen(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={handleSavePhoto} disabled={saving}>
              {saving ? 'Saving…' : 'Save'}
            </button>
          </>
        }
      >
        <ImageUploadField value={photoUrl} onChange={setPhotoUrl} usage="profile_photo" />
      </Modal>
    </header>
  );
}
