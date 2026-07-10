import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { occasionsApi } from '../../api';
import { formatDate } from '../../utils/format';
import StatusBadge from '../../components/ui/StatusBadge';
import Pagination from '../../components/ui/Pagination';
import { SkeletonTable } from '../../components/ui/Skeleton';
import Modal, { ConfirmDialog } from '../../components/ui/Modal';
import ImageUploadField from '../../components/ui/ImageUploadField';
import { usePagination } from '../../hooks/usePagination';

function UnderDevelopment({ label }) {
  return (
    <div className="admin-card" style={{ textAlign: 'center', padding: '48px 24px' }}>
      <div style={{ fontSize: 32, marginBottom: 12 }}>🚧</div>
      <h3 style={{ margin: '0 0 8px' }}>{label} — Under development</h3>
      <p style={{ color: 'var(--text-secondary, #6b7280)', margin: 0 }}>
        This section isn't wired up for real management yet. Check back soon.
      </p>
    </div>
  );
}

const EMPTY_THEME_FORM = {
  name: '', description: '', cover_image_url: '', thumbnail_url: '',
  primary_color: '#C8A96E', secondary_color: '', accent_color: '', background_color: '',
  is_active: true, is_featured: false,
};

function ThemesTab() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [deleteId, setDeleteId] = useState(null);
  const [form, setForm] = useState(EMPTY_THEME_FORM);

  const { data: themes = [] } = useQuery({
    queryKey: ['occasions', 'themes'],
    queryFn: () => occasionsApi.listThemes(),
  });

  const saveMutation = useMutation({
    mutationFn: (body) => editItem ? occasionsApi.updateTheme(editItem.id, body) : occasionsApi.createTheme(body),
    onSuccess: () => {
      toast.success(editItem ? 'Theme updated' : 'Theme created');
      qc.invalidateQueries(['occasions', 'themes']);
      setOpen(false); setEditItem(null); setForm(EMPTY_THEME_FORM);
    },
    onError: () => toast.error('Save failed'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id) => occasionsApi.deleteTheme(id),
    onSuccess: () => { toast.success('Theme deleted'); qc.invalidateQueries(['occasions', 'themes']); setDeleteId(null); },
    onError: () => toast.error('Delete failed'),
  });

  const openCreate = () => { setEditItem(null); setForm(EMPTY_THEME_FORM); setOpen(true); };
  const openEdit = (theme) => {
    setEditItem(theme);
    setForm({
      name: theme.name,
      description: theme.description ?? '',
      cover_image_url: theme.cover_image_url ?? '',
      thumbnail_url: theme.thumbnail_url ?? '',
      primary_color: theme.colors?.primary ?? '#C8A96E',
      secondary_color: theme.colors?.secondary ?? '',
      accent_color: theme.colors?.accent ?? '',
      background_color: theme.colors?.background ?? '',
      is_active: theme.is_active ?? true,
      is_featured: theme.is_featured ?? false,
    });
    setOpen(true);
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
        <button className="btn btn-primary btn-sm" onClick={openCreate}>+ New Theme</button>
      </div>
      <div className="admin-table-wrapper">
        <table className="admin-table">
          <thead>
            <tr><th>Name</th><th>Colors</th><th>Status</th><th>Actions</th></tr>
          </thead>
          <tbody>
            {themes.map((theme) => (
              <tr key={theme.id}>
                <td><div className="admin-user-name">{theme.name}</div></td>
                <td>
                  <div style={{ display: 'flex', gap: 4 }}>
                    {['primary', 'secondary', 'accent', 'background'].map((k) => (
                      theme.colors?.[k] ? (
                        <span key={k} title={`${k}: ${theme.colors[k]}`}
                          style={{
                            width: 20, height: 20, borderRadius: '50%',
                            background: theme.colors[k],
                            border: '1px solid rgba(0,0,0,0.15)',
                            display: 'inline-block',
                          }} />
                      ) : null
                    ))}
                    {!theme.colors && <span>—</span>}
                  </div>
                </td>
                <td><StatusBadge status={theme.is_active ? 'active' : 'inactive'} /></td>
                <td>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <button className="btn btn-secondary btn-sm" onClick={() => openEdit(theme)}>Edit</button>
                    <button className="btn btn-danger btn-sm" onClick={() => setDeleteId(theme.id)}>Delete</button>
                  </div>
                </td>
              </tr>
            ))}
            {!themes.length && <tr><td colSpan={4} className="admin-table-empty">No themes yet</td></tr>}
          </tbody>
        </table>
      </div>

      <Modal open={open} onClose={() => setOpen(false)} title={editItem ? 'Edit Theme' : 'New Theme'}
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setOpen(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={() => saveMutation.mutate(form)} disabled={!form.name || saveMutation.isPending}>
              {saveMutation.isPending ? 'Saving…' : 'Save'}
            </button>
          </>
        }
      >
        <div className="form-group">
          <label className="form-label required">Name</label>
          <input className="form-control" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder="Royal Gold" />
        </div>
        <div className="form-group">
          <label className="form-label">Description</label>
          <textarea className="form-control" rows={2} value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
        </div>
        <div className="form-group">
          <label className="form-label">Cover Image</label>
          <ImageUploadField value={form.cover_image_url} onChange={(url) => setForm(f => ({ ...f, cover_image_url: url }))} usage="occasion_cover" label="Upload" />
        </div>
        <div className="form-group">
          <label className="form-label">Thumbnail</label>
          <ImageUploadField value={form.thumbnail_url} onChange={(url) => setForm(f => ({ ...f, thumbnail_url: url }))} usage="occasion_cover" label="Upload" />
        </div>
        <div className="form-group">
          <label className="form-label required">Primary Color</label>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <input type="color" value={form.primary_color || '#C8A96E'} onChange={e => setForm(f => ({ ...f, primary_color: e.target.value }))} style={{ width: 44, height: 36, padding: 2 }} />
            <input className="form-control" value={form.primary_color} onChange={e => setForm(f => ({ ...f, primary_color: e.target.value }))} placeholder="#C8A96E" />
          </div>
        </div>
        <div className="form-group">
          <label className="form-label">Secondary Color</label>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <input type="color" value={form.secondary_color || '#F5F0E8'} onChange={e => setForm(f => ({ ...f, secondary_color: e.target.value }))} style={{ width: 44, height: 36, padding: 2 }} />
            <input className="form-control" value={form.secondary_color} onChange={e => setForm(f => ({ ...f, secondary_color: e.target.value }))} placeholder="Optional" />
          </div>
        </div>
        <div className="form-group">
          <label className="form-label">Accent Color</label>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <input type="color" value={form.accent_color || '#8B1A1A'} onChange={e => setForm(f => ({ ...f, accent_color: e.target.value }))} style={{ width: 44, height: 36, padding: 2 }} />
            <input className="form-control" value={form.accent_color} onChange={e => setForm(f => ({ ...f, accent_color: e.target.value }))} placeholder="Optional" />
          </div>
        </div>
        <div className="form-group">
          <label className="form-label">Background Color</label>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <input type="color" value={form.background_color || '#FFF8F0'} onChange={e => setForm(f => ({ ...f, background_color: e.target.value }))} style={{ width: 44, height: 36, padding: 2 }} />
            <input className="form-control" value={form.background_color} onChange={e => setForm(f => ({ ...f, background_color: e.target.value }))} placeholder="Optional" />
          </div>
        </div>
        <div className="form-check">
          <input type="checkbox" id="theme_featured" checked={form.is_featured} onChange={e => setForm(f => ({ ...f, is_featured: e.target.checked }))} />
          <label htmlFor="theme_featured">Featured (promoted in the theme picker)</label>
        </div>
        {editItem && (
          <div className="form-check">
            <input type="checkbox" id="theme_active" checked={form.is_active} onChange={e => setForm(f => ({ ...f, is_active: e.target.checked }))} />
            <label htmlFor="theme_active">Active</label>
          </div>
        )}
      </Modal>

      <ConfirmDialog open={!!deleteId} onClose={() => setDeleteId(null)} onConfirm={() => deleteMutation.mutate(deleteId)}
        title="Delete Theme" message="This theme will be permanently deleted." danger loading={deleteMutation.isPending} />
    </div>
  );
}

export default function OccasionsPage() {
  const qc = useQueryClient();
  const { page, perPage, setPage } = usePagination();
  const [activeTab, setActiveTab] = useState('occasions');
  const [newOpen, setNewOpen] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [deleteId, setDeleteId] = useState(null);
  const [form, setForm] = useState({ name: '', description: '', is_active: true, thumbnail_url: '' });

  const { data, isLoading } = useQuery({
    queryKey: ['occasions', { page, perPage }],
    queryFn: () => occasionsApi.list({ page, per_page: perPage }),
    enabled: activeTab === 'occasions',
  });

  const saveMutation = useMutation({
    mutationFn: (body) => editItem ? occasionsApi.update(editItem.id, body) : occasionsApi.create(body),
    onSuccess: () => {
      toast.success(editItem ? 'Updated' : 'Created');
      qc.invalidateQueries(['occasions']);
      setNewOpen(false); setEditItem(null);
    },
    onError: () => toast.error('Save failed'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id) => occasionsApi.delete(id),
    onSuccess: () => { toast.success('Deleted'); qc.invalidateQueries(['occasions']); setDeleteId(null); },
    onError: () => toast.error('Delete failed'),
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const pages = data?.pages ?? 1;

  const openEdit = (item) => {
    setEditItem(item);
    setForm({
      name: item.name,
      description: item.description ?? '',
      is_active: item.is_active ?? true,
      thumbnail_url: item.thumbnail_url ?? '',
    });
    setNewOpen(true);
  };

  const TABS = [
    { key: 'occasions', label: 'Occasions' },
    { key: 'categories', label: 'Categories' },
    { key: 'moods', label: 'Moods' },
    { key: 'tags', label: 'Tags' },
    { key: 'themes', label: 'Themes' },
  ];

  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <h1>Occasions & Categories</h1>
          <p>Manage occasion types, categories, moods, tags, and themes</p>
        </div>
        {activeTab === 'occasions' && (
          <button className="btn btn-primary" onClick={() => { setEditItem(null); setForm({ name: '', description: '', is_active: true, thumbnail_url: '' }); setNewOpen(true); }}>
            + New Occasion
          </button>
        )}
      </div>

      <div className="admin-tabs">
        {TABS.map(t => (
          <button key={t.key} className={`admin-tab${activeTab === t.key ? ' active' : ''}`} onClick={() => setActiveTab(t.key)}>
            {t.label}
          </button>
        ))}
      </div>

      {activeTab === 'occasions' && (
        isLoading ? <SkeletonTable rows={8} cols={5} /> : (
          <div className="admin-table-wrapper">
            <table className="admin-table">
              <thead>
                <tr><th>Image</th><th>Name</th><th>Description</th><th>Status</th><th>Created</th><th>Actions</th></tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id}>
                    <td>
                      {item.thumbnail_url ? (
                        <img src={item.thumbnail_url} alt="" style={{ width: 40, height: 40, borderRadius: 8, objectFit: 'cover' }} />
                      ) : (
                        <div style={{ width: 40, height: 40, borderRadius: 8, background: 'var(--border-color, #e5e7eb)' }} />
                      )}
                    </td>
                    <td><div className="admin-user-name">{item.name}</div></td>
                    <td>{item.description ?? '—'}</td>
                    <td><StatusBadge status={item.is_active ? 'active' : 'inactive'} /></td>
                    <td>{formatDate(item.created_at)}</td>
                    <td>
                      <div style={{ display: 'flex', gap: 6 }}>
                        <button className="btn btn-secondary btn-sm" onClick={() => openEdit(item)}>Edit</button>
                        <button className="btn btn-danger btn-sm" onClick={() => setDeleteId(item.id)}>Delete</button>
                      </div>
                    </td>
                  </tr>
                ))}
                {!items.length && <tr><td colSpan={6} className="admin-table-empty">No occasions</td></tr>}
              </tbody>
            </table>
            <Pagination page={page} pages={pages} total={total} perPage={perPage} onChange={setPage} />
          </div>
        )
      )}

      {activeTab === 'categories' && <UnderDevelopment label="Categories" />}
      {activeTab === 'moods' && <UnderDevelopment label="Moods" />}
      {activeTab === 'tags' && <UnderDevelopment label="Tags" />}
      {activeTab === 'themes' && <ThemesTab />}

      <Modal open={newOpen} onClose={() => setNewOpen(false)} title={editItem ? 'Edit Occasion' : 'New Occasion'}
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setNewOpen(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={() => saveMutation.mutate(form)} disabled={!form.name || saveMutation.isPending}>
              {saveMutation.isPending ? 'Saving…' : 'Save'}
            </button>
          </>
        }
      >
        <div className="form-group">
          <label className="form-label required">Name</label>
          <input className="form-control" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder="Birthday" />
        </div>
        <div className="form-group">
          <label className="form-label">Description</label>
          <textarea className="form-control" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} rows={3} />
        </div>
        <div className="form-group">
          <label className="form-label">Card Image</label>
          <ImageUploadField
            value={form.thumbnail_url}
            onChange={(url) => setForm(f => ({ ...f, thumbnail_url: url }))}
            usage="occasion_cover"
            label="Upload"
          />
          <div className="form-hint">Shown on occasion cards in the customer app (e.g. "Other Moments").</div>
        </div>
        <div className="form-check">
          <input type="checkbox" id="is_active" checked={form.is_active} onChange={e => setForm(f => ({ ...f, is_active: e.target.checked }))} />
          <label htmlFor="is_active">Active</label>
        </div>
      </Modal>

      <ConfirmDialog open={!!deleteId} onClose={() => setDeleteId(null)} onConfirm={() => deleteMutation.mutate(deleteId)}
        title="Delete Occasion" message="This will soft-delete the occasion." danger loading={deleteMutation.isPending} />
    </div>
  );
}
