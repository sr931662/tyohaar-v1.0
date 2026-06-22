import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { occasionsApi } from '../../api';
import { formatDate } from '../../utils/format';
import StatusBadge from '../../components/ui/StatusBadge';
import Pagination from '../../components/ui/Pagination';
import { SkeletonTable } from '../../components/ui/Skeleton';
import Modal, { ConfirmDialog } from '../../components/ui/Modal';
import { usePagination } from '../../hooks/usePagination';

function ReferenceTab({ label, queryKey, listFn, createFn, fields }) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({});

  const { data: items = [] } = useQuery({ queryKey, queryFn: listFn });

  const createMutation = useMutation({
    mutationFn: () => createFn(form),
    onSuccess: () => { toast.success('Created'); qc.invalidateQueries(queryKey); setOpen(false); setForm({}); },
    onError: () => toast.error('Failed'),
  });

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
        <button className="btn btn-primary btn-sm" onClick={() => { setForm({}); setOpen(true); }}>+ New {label}</button>
      </div>
      <div className="admin-table-wrapper">
        <table className="admin-table">
          <thead>
            <tr>{fields.map(f => <th key={f.key}>{f.label}</th>)}<th>Created</th></tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                {fields.map(f => <td key={f.key}>{item[f.key] ?? '—'}</td>)}
                <td>{formatDate(item.created_at)}</td>
              </tr>
            ))}
            {!items.length && <tr><td colSpan={fields.length + 1} className="admin-table-empty">No {label.toLowerCase()}s yet</td></tr>}
          </tbody>
        </table>
      </div>

      <Modal open={open} onClose={() => setOpen(false)} title={`New ${label}`}
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setOpen(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={() => createMutation.mutate()} disabled={createMutation.isPending}>
              {createMutation.isPending ? 'Creating…' : 'Create'}
            </button>
          </>
        }
      >
        {fields.map(f => (
          <div className="form-group" key={f.key}>
            <label className="form-label">{f.label}</label>
            <input className="form-control" value={form[f.key] ?? ''} onChange={e => setForm(prev => ({ ...prev, [f.key]: e.target.value }))} />
          </div>
        ))}
      </Modal>
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
  const [form, setForm] = useState({ name: '', description: '', is_active: true });

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
    setEditItem(item); setForm({ name: item.name, description: item.description ?? '', is_active: item.is_active ?? true });
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
          <button className="btn btn-primary" onClick={() => { setEditItem(null); setForm({ name: '', description: '', is_active: true }); setNewOpen(true); }}>
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
        isLoading ? <SkeletonTable rows={8} cols={4} /> : (
          <div className="admin-table-wrapper">
            <table className="admin-table">
              <thead>
                <tr><th>Name</th><th>Description</th><th>Status</th><th>Created</th><th>Actions</th></tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id}>
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
                {!items.length && <tr><td colSpan={5} className="admin-table-empty">No occasions</td></tr>}
              </tbody>
            </table>
            <Pagination page={page} pages={pages} total={total} perPage={perPage} onChange={setPage} />
          </div>
        )
      )}

      {activeTab === 'categories' && (
        <ReferenceTab
          label="Category"
          queryKey={['occasions', 'categories']}
          listFn={() => occasionsApi.listCategories()}
          createFn={(body) => occasionsApi.createCategory(body)}
          fields={[{ key: 'name', label: 'Name' }, { key: 'slug', label: 'Slug' }]}
        />
      )}

      {activeTab === 'moods' && (
        <ReferenceTab
          label="Mood"
          queryKey={['occasions', 'moods']}
          listFn={() => occasionsApi.listMoods()}
          createFn={(body) => occasionsApi.createMood(body)}
          fields={[{ key: 'name', label: 'Name' }, { key: 'emoji', label: 'Emoji' }]}
        />
      )}

      {activeTab === 'tags' && (
        <ReferenceTab
          label="Tag"
          queryKey={['occasions', 'tags']}
          listFn={() => occasionsApi.listTags()}
          createFn={(body) => occasionsApi.createTag(body)}
          fields={[{ key: 'name', label: 'Name' }]}
        />
      )}

      {activeTab === 'themes' && (
        <ReferenceTab
          label="Theme"
          queryKey={['occasions', 'themes']}
          listFn={() => occasionsApi.listThemes()}
          createFn={(body) => occasionsApi.createTheme(body)}
          fields={[{ key: 'name', label: 'Name' }, { key: 'color_scheme', label: 'Color Scheme' }]}
        />
      )}

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
