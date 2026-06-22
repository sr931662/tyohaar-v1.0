import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { settingsApi } from '../../api';
import { formatDate } from '../../utils/format';
import Modal, { ConfirmDialog } from '../../components/ui/Modal';
import { SkeletonTable } from '../../components/ui/Skeleton';

function AppSettingsTab() {
  const qc = useQueryClient();
  const [saving, setSaving] = useState(false);

  const { data: settings, isLoading } = useQuery({
    queryKey: ['settings', 'app'],
    queryFn: () => settingsApi.getAppSettings(),
  });

  const [form, setForm] = useState({});
  const hasForm = Object.keys(form).length > 0;
  const merged = { ...(settings ?? {}), ...form };

  const saveMutation = useMutation({
    mutationFn: () => settingsApi.updateAppSettings(form),
    onSuccess: () => { toast.success('Settings saved'); qc.invalidateQueries(['settings', 'app']); setForm({}); },
    onError: () => toast.error('Save failed'),
  });

  if (isLoading) return <div style={{ padding: 24, color: 'var(--text-tertiary)' }}>Loading…</div>;

  const S = settings ?? {};

  return (
    <div style={{ maxWidth: 600 }}>
      <div className="admin-card">
        <div className="admin-card-header"><div className="admin-card-title">Platform Settings</div></div>
        <div className="admin-card-body">
          {[
            { key: 'platform_name', label: 'Platform Name', type: 'text' },
            { key: 'support_email', label: 'Support Email', type: 'email' },
            { key: 'support_phone', label: 'Support Phone', type: 'text' },
            { key: 'currency', label: 'Currency', type: 'text' },
            { key: 'commission_rate', label: 'Commission Rate (%)', type: 'number' },
          ].map(({ key, label, type }) => (
            <div className="form-group" key={key}>
              <label className="form-label">{label}</label>
              <input className="form-control" type={type} value={form[key] ?? S[key] ?? ''} onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))} />
            </div>
          ))}
          <div className="form-check">
            <input type="checkbox" id="maintenance_mode" checked={form.maintenance_mode ?? S.maintenance_mode ?? false}
              onChange={e => setForm(f => ({ ...f, maintenance_mode: e.target.checked }))} />
            <label htmlFor="maintenance_mode">Maintenance Mode</label>
          </div>
          <div style={{ marginTop: 16, display: 'flex', justifyContent: 'flex-end' }}>
            <button className="btn btn-primary" onClick={() => saveMutation.mutate()} disabled={!hasForm || saveMutation.isPending}>
              {saveMutation.isPending ? 'Saving…' : 'Save Changes'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function BannersTab() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [deleteId, setDeleteId] = useState(null);
  const [form, setForm] = useState({ title: '', image_url: '', link_url: '', is_active: true, position: 0 });

  const { data: banners = [], isLoading } = useQuery({
    queryKey: ['settings', 'banners'],
    queryFn: () => settingsApi.listBanners(),
  });

  const saveMutation = useMutation({
    mutationFn: (body) => editItem ? settingsApi.updateBanner(editItem.id, body) : settingsApi.createBanner(body),
    onSuccess: () => { toast.success(editItem ? 'Banner updated' : 'Banner created'); qc.invalidateQueries(['settings', 'banners']); setOpen(false); setEditItem(null); },
    onError: () => toast.error('Failed'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id) => settingsApi.deleteBanner(id),
    onSuccess: () => { toast.success('Deleted'); qc.invalidateQueries(['settings', 'banners']); setDeleteId(null); },
    onError: () => toast.error('Failed'),
  });

  const openEdit = (b) => {
    setEditItem(b);
    setForm({ title: b.title, image_url: b.image_url ?? '', link_url: b.link_url ?? '', is_active: b.is_active ?? true, position: b.position ?? 0 });
    setOpen(true);
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
        <button className="btn btn-primary" onClick={() => { setEditItem(null); setForm({ title:'', image_url:'', link_url:'', is_active:true, position:0 }); setOpen(true); }}>+ New Banner</button>
      </div>
      {isLoading ? <SkeletonTable rows={4} cols={4} /> : (
        <div className="admin-table-wrapper">
          <table className="admin-table">
            <thead><tr><th>Title</th><th>Position</th><th>Status</th><th>Actions</th></tr></thead>
            <tbody>
              {banners.map((b) => (
                <tr key={b.id}>
                  <td>{b.title}</td>
                  <td>{b.position}</td>
                  <td><span className={`badge ${b.is_active ? 'badge-green' : 'badge-gray'}`}>{b.is_active ? 'Active' : 'Inactive'}</span></td>
                  <td>
                    <div style={{ display: 'flex', gap: 6 }}>
                      <button className="btn btn-secondary btn-sm" onClick={() => openEdit(b)}>Edit</button>
                      <button className="btn btn-danger btn-sm" onClick={() => setDeleteId(b.id)}>Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
              {!banners.length && <tr><td colSpan={4} className="admin-table-empty">No banners</td></tr>}
            </tbody>
          </table>
        </div>
      )}
      <Modal open={open} onClose={() => setOpen(false)} title={editItem ? 'Edit Banner' : 'New Banner'}
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setOpen(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={() => saveMutation.mutate(form)} disabled={!form.title || saveMutation.isPending}>
              {saveMutation.isPending ? 'Saving…' : 'Save'}
            </button>
          </>
        }
      >
        <div className="form-group"><label className="form-label required">Title</label><input className="form-control" value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} /></div>
        <div className="form-group"><label className="form-label">Image URL</label><input className="form-control" value={form.image_url} onChange={e => setForm(f => ({ ...f, image_url: e.target.value }))} /></div>
        <div className="form-group"><label className="form-label">Link URL</label><input className="form-control" value={form.link_url} onChange={e => setForm(f => ({ ...f, link_url: e.target.value }))} /></div>
        <div className="form-group"><label className="form-label">Position</label><input className="form-control" type="number" value={form.position} onChange={e => setForm(f => ({ ...f, position: parseInt(e.target.value) || 0 }))} /></div>
        <div className="form-check">
          <input type="checkbox" id="banner_active" checked={form.is_active} onChange={e => setForm(f => ({ ...f, is_active: e.target.checked }))} />
          <label htmlFor="banner_active">Active</label>
        </div>
      </Modal>
      <ConfirmDialog open={!!deleteId} onClose={() => setDeleteId(null)} onConfirm={() => deleteMutation.mutate(deleteId)}
        title="Delete Banner" message="This banner will be permanently deleted." danger loading={deleteMutation.isPending} />
    </div>
  );
}

function FAQsTab() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [deleteId, setDeleteId] = useState(null);
  const [form, setForm] = useState({ question: '', answer: '', category: '', position: 0 });

  const { data: faqs = [], isLoading } = useQuery({
    queryKey: ['settings', 'faqs'],
    queryFn: () => settingsApi.listFAQs(),
  });

  const saveMutation = useMutation({
    mutationFn: (body) => editItem ? settingsApi.updateFAQ(editItem.id, body) : settingsApi.createFAQ(body),
    onSuccess: () => { toast.success(editItem ? 'Updated' : 'Created'); qc.invalidateQueries(['settings', 'faqs']); setOpen(false); setEditItem(null); },
    onError: () => toast.error('Failed'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id) => settingsApi.deleteFAQ(id),
    onSuccess: () => { toast.success('Deleted'); qc.invalidateQueries(['settings', 'faqs']); setDeleteId(null); },
    onError: () => toast.error('Failed'),
  });

  const openEdit = (f) => {
    setEditItem(f);
    setForm({ question: f.question, answer: f.answer, category: f.category ?? '', position: f.position ?? 0 });
    setOpen(true);
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
        <button className="btn btn-primary" onClick={() => { setEditItem(null); setForm({ question:'', answer:'', category:'', position:0 }); setOpen(true); }}>+ New FAQ</button>
      </div>
      {isLoading ? <SkeletonTable rows={5} cols={3} /> : (
        <div className="admin-table-wrapper">
          <table className="admin-table">
            <thead><tr><th>Question</th><th>Category</th><th>Pos</th><th>Actions</th></tr></thead>
            <tbody>
              {faqs.map((f) => (
                <tr key={f.id}>
                  <td style={{ maxWidth: 360 }}>{f.question}</td>
                  <td>{f.category ?? '—'}</td>
                  <td>{f.position}</td>
                  <td>
                    <div style={{ display: 'flex', gap: 6 }}>
                      <button className="btn btn-secondary btn-sm" onClick={() => openEdit(f)}>Edit</button>
                      <button className="btn btn-danger btn-sm" onClick={() => setDeleteId(f.id)}>Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
              {!faqs.length && <tr><td colSpan={4} className="admin-table-empty">No FAQs</td></tr>}
            </tbody>
          </table>
        </div>
      )}
      <Modal open={open} onClose={() => setOpen(false)} title={editItem ? 'Edit FAQ' : 'New FAQ'}
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setOpen(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={() => saveMutation.mutate(form)} disabled={!form.question || saveMutation.isPending}>
              {saveMutation.isPending ? 'Saving…' : 'Save'}
            </button>
          </>
        }
      >
        <div className="form-group"><label className="form-label required">Question</label><input className="form-control" value={form.question} onChange={e => setForm(f => ({ ...f, question: e.target.value }))} /></div>
        <div className="form-group"><label className="form-label required">Answer</label><textarea className="form-control" rows={4} value={form.answer} onChange={e => setForm(f => ({ ...f, answer: e.target.value }))} /></div>
        <div className="form-row-2">
          <div className="form-group"><label className="form-label">Category</label><input className="form-control" value={form.category} onChange={e => setForm(f => ({ ...f, category: e.target.value }))} /></div>
          <div className="form-group"><label className="form-label">Position</label><input className="form-control" type="number" value={form.position} onChange={e => setForm(f => ({ ...f, position: parseInt(e.target.value) || 0 }))} /></div>
        </div>
      </Modal>
      <ConfirmDialog open={!!deleteId} onClose={() => setDeleteId(null)} onConfirm={() => deleteMutation.mutate(deleteId)}
        title="Delete FAQ" message="This FAQ will be deleted." danger loading={deleteMutation.isPending} />
    </div>
  );
}

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('app');

  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <h1>Platform Settings</h1>
          <p>Configure app settings, banners, and content</p>
        </div>
      </div>

      <div className="admin-tabs">
        {[['app', 'App Settings'], ['banners', 'Banners'], ['faqs', 'FAQs']].map(([key, label]) => (
          <button key={key} className={`admin-tab${activeTab === key ? ' active' : ''}`} onClick={() => setActiveTab(key)}>
            {label}
          </button>
        ))}
      </div>

      {activeTab === 'app' && <AppSettingsTab />}
      {activeTab === 'banners' && <BannersTab />}
      {activeTab === 'faqs' && <FAQsTab />}
    </div>
  );
}
