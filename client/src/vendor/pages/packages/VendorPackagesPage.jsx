import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { vendorProfileApi, vendorPackagesApi } from '../../api';
import { ConfirmDialog } from '../../../admin/components/ui/Modal';

// ── Constants ─────────────────────────────────────────────────────────────────

const STATUS_COLOR = {
  draft: 'var(--text-tertiary)',
  pending_review: '#f59e0b',
  active: '#22c55e',
  inactive: 'var(--text-tertiary)',
  archived: 'var(--text-tertiary)',
};
const STATUS_LABEL = {
  draft: 'Draft', pending_review: 'Pending Review',
  active: 'Active', inactive: 'Inactive', archived: 'Archived',
};

function StatusBadge({ status }) {
  const color = STATUS_COLOR[status] ?? 'var(--text-tertiary)';
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 5,
      padding: '3px 8px', borderRadius: 99,
      background: `${color}18`, border: `1px solid ${color}40`,
      fontSize: 12, fontWeight: 600, color,
    }}>
      <span style={{ width: 5, height: 5, borderRadius: '50%', background: color }} />
      {STATUS_LABEL[status] ?? status}
    </span>
  );
}

// ── Create Package Modal ───────────────────────────────────────────────────────

function PackageFormModal({ initial, categories, onClose, onSave, saving }) {
  const isEdit = !!initial;
  const [form, setForm] = useState({
    name: initial?.name ?? '',
    description: initial?.description ?? '',
    short_description: initial?.short_description ?? '',
    category_id: initial?.category?.id ?? initial?.category_id ?? '',
    base_price: initial?.base_price ?? '',
    min_guests: initial?.min_guests ?? '',
    max_guests: initial?.max_guests ?? '',
    duration_hours: initial?.duration_hours ?? '',
    cover_image_url: initial?.cover_image_url ?? '',
    is_customizable: initial?.is_customizable ?? false,
  });
  const [errors, setErrors] = useState({});

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const validate = () => {
    const e = {};
    if (!form.name.trim()) e.name = 'Package name is required.';
    if (!form.base_price || isNaN(Number(form.base_price))) e.base_price = 'Enter a valid price.';
    setErrors(e);
    return !Object.keys(e).length;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!validate()) return;
    const body = {
      name: form.name.trim(),
      description: form.description.trim() || undefined,
      short_description: form.short_description.trim() || undefined,
      category_id: form.category_id || undefined,
      base_price: Number(form.base_price),
      pricing_type: 'fixed',
      min_guests: form.min_guests !== '' ? Number(form.min_guests) : undefined,
      max_guests: form.max_guests !== '' ? Number(form.max_guests) : undefined,
      duration_hours: form.duration_hours !== '' ? Number(form.duration_hours) : undefined,
      cover_image_url: form.cover_image_url.trim() || undefined,
      is_customizable: form.is_customizable,
    };
    onSave(body);
  };

  return (
    <div className="admin-modal-overlay" onClick={onClose}>
      <div className="admin-modal" style={{ maxWidth: 560 }} onClick={(e) => e.stopPropagation()}>
        <div className="admin-modal-header">
          <h2 className="admin-modal-title">{isEdit ? 'Edit Package' : 'New Package'}</h2>
          <button className="admin-modal-close" onClick={onClose}>×</button>
        </div>
        <form onSubmit={handleSubmit} style={{ padding: '0 24px 24px', display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div>
            <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 6 }}>Package Name *</label>
            <input className="admin-input" value={form.name} onChange={(e) => set('name', e.target.value)} placeholder="e.g. Premium Wedding Decoration" />
            {errors.name && <p style={{ color: 'var(--color-error,#ef4444)', fontSize: 12, marginTop: 4 }}>{errors.name}</p>}
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 6 }}>Short Description</label>
            <input className="admin-input" value={form.short_description} onChange={(e) => set('short_description', e.target.value)} placeholder="One-liner shown in listing cards" maxLength={500} />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 6 }}>Full Description</label>
            <textarea className="admin-input" rows={3} value={form.description} onChange={(e) => set('description', e.target.value)} placeholder="What's included in this package?" />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 6 }}>Category</label>
              <select className="admin-input" value={form.category_id} onChange={(e) => set('category_id', e.target.value)}>
                <option value="">None</option>
                {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 6 }}>Base Price (₹) *</label>
              <input className="admin-input" type="number" min="0" value={form.base_price} onChange={(e) => set('base_price', e.target.value)} placeholder="e.g. 15000" />
              {errors.base_price && <p style={{ color: 'var(--color-error,#ef4444)', fontSize: 12, marginTop: 4 }}>{errors.base_price}</p>}
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
            <div>
              <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 6 }}>Min Guests</label>
              <input className="admin-input" type="number" min="1" value={form.min_guests} onChange={(e) => set('min_guests', e.target.value)} placeholder="e.g. 50" />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 6 }}>Max Guests</label>
              <input className="admin-input" type="number" min="1" value={form.max_guests} onChange={(e) => set('max_guests', e.target.value)} placeholder="e.g. 500" />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 6 }}>Duration (hrs)</label>
              <input className="admin-input" type="number" min="0" step="0.5" value={form.duration_hours} onChange={(e) => set('duration_hours', e.target.value)} placeholder="e.g. 8" />
            </div>
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 6 }}>Cover Image URL</label>
            <input className="admin-input" type="url" value={form.cover_image_url} onChange={(e) => set('cover_image_url', e.target.value)} placeholder="https://..." />
          </div>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, cursor: 'pointer', userSelect: 'none' }}>
            <input type="checkbox" checked={form.is_customizable} onChange={(e) => set('is_customizable', e.target.checked)} />
            Allow customers to customise this package
          </label>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 4 }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? (isEdit ? 'Saving…' : 'Creating…') : (isEdit ? 'Save Changes' : 'Create Package')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Package Items Modal ────────────────────────────────────────────────────────

function PackageItemsModal({ pkg, onClose }) {
  const qc = useQueryClient();
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [newItem, setNewItem] = useState({ name: '', description: '', quantity: 1, unit: '', base_price: '', is_mandatory: true });
  const [confirmDelete, setConfirmDelete] = useState(null);

  const { data: items = [], isLoading } = useQuery({
    queryKey: ['pkg-items', pkg.id],
    queryFn: () => vendorPackagesApi.listItems(pkg.id),
  });

  const invalidate = () => qc.invalidateQueries(['pkg-items', pkg.id]);

  const addMutation = useMutation({
    mutationFn: (body) => vendorPackagesApi.addItem(pkg.id, { ...body, package_id: pkg.id }),
    onSuccess: () => { toast.success('Item added.'); invalidate(); setNewItem({ name: '', description: '', quantity: 1, unit: '', base_price: '', is_mandatory: true }); },
    onError: (err) => toast.error(err?.response?.data?.detail ?? 'Failed to add item.'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ itemId, body }) => vendorPackagesApi.updateItem(pkg.id, itemId, body),
    onSuccess: () => { toast.success('Item updated.'); invalidate(); setEditingId(null); },
    onError: (err) => toast.error(err?.response?.data?.detail ?? 'Failed to update item.'),
  });

  const deleteMutation = useMutation({
    mutationFn: (itemId) => vendorPackagesApi.deleteItem(pkg.id, itemId),
    onSuccess: () => { toast.success('Item removed.'); invalidate(); setConfirmDelete(null); },
    onError: () => toast.error('Failed to remove item.'),
  });

  const startEdit = (item) => {
    setEditingId(item.id);
    setEditForm({ name: item.name, description: item.description ?? '', quantity: item.quantity, unit: item.unit ?? '', base_price: item.base_price, is_mandatory: item.is_mandatory });
  };

  const setNF = (k, v) => setNewItem((f) => ({ ...f, [k]: v }));
  const setEF = (k, v) => setEditForm((f) => ({ ...f, [k]: v }));

  const handleAdd = (e) => {
    e.preventDefault();
    if (!newItem.name.trim()) return toast.error('Item name is required.');
    if (!newItem.base_price || isNaN(Number(newItem.base_price))) return toast.error('Enter a valid price.');
    addMutation.mutate({ ...newItem, quantity: Number(newItem.quantity), base_price: Number(newItem.base_price), unit: newItem.unit || undefined, description: newItem.description || undefined });
  };

  const handleUpdate = (itemId) => {
    if (!editForm.name.trim()) return toast.error('Item name is required.');
    updateMutation.mutate({ itemId, body: { ...editForm, quantity: Number(editForm.quantity), base_price: Number(editForm.base_price), unit: editForm.unit || undefined, description: editForm.description || undefined } });
  };

  const isLocked = pkg.status === 'pending_review';

  return (
    <div className="admin-modal-overlay" onClick={onClose}>
      <div className="admin-modal lg" onClick={(e) => e.stopPropagation()}>
        <div className="admin-modal-header">
          <div>
            <h2 className="admin-modal-title">Package Items</h2>
            <p style={{ margin: '2px 0 0', fontSize: 12, color: 'var(--text-tertiary)' }}>{pkg.name}</p>
          </div>
          <button className="admin-modal-close" onClick={onClose}>×</button>
        </div>
        <div style={{ padding: '20px 24px 24px' }}>
          {isLocked && (
            <div style={{ padding: '10px 14px', borderRadius: 8, background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.2)', fontSize: 13, color: '#f59e0b', marginBottom: 16 }}>
              This package is under review. Items cannot be edited.
            </div>
          )}

          {/* Existing items */}
          {isLoading ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 20 }}>
              {[0, 1].map((i) => <div key={i} className="skeleton skeleton-card" style={{ height: 56 }} />)}
            </div>
          ) : !items.length ? (
            <p style={{ color: 'var(--text-tertiary)', fontSize: 13, textAlign: 'center', padding: '16px 0', marginBottom: 4 }}>No items yet. Add one below.</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 20 }}>
              {items.map((item) => editingId === item.id ? (
                <div key={item.id} className="admin-card" style={{ padding: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 10 }}>
                    <input className="admin-input" value={editForm.name} onChange={(e) => setEF('name', e.target.value)} placeholder="Item name" />
                    <input className="admin-input" type="number" min="0" value={editForm.base_price} onChange={(e) => setEF('base_price', e.target.value)} placeholder="Price (₹)" />
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
                    <input className="admin-input" type="number" min="1" value={editForm.quantity} onChange={(e) => setEF('quantity', e.target.value)} placeholder="Qty" />
                    <input className="admin-input" value={editForm.unit} onChange={(e) => setEF('unit', e.target.value)} placeholder="Unit (hrs, pcs…)" />
                    <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, cursor: 'pointer' }}>
                      <input type="checkbox" checked={editForm.is_mandatory} onChange={(e) => setEF('is_mandatory', e.target.checked)} />
                      Mandatory
                    </label>
                  </div>
                  <input className="admin-input" value={editForm.description} onChange={(e) => setEF('description', e.target.value)} placeholder="Description (optional)" />
                  <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                    <button className="btn btn-secondary btn-sm" onClick={() => setEditingId(null)}>Cancel</button>
                    <button className="btn btn-primary btn-sm" onClick={() => handleUpdate(item.id)} disabled={updateMutation.isPending}>Save</button>
                  </div>
                </div>
              ) : (
                <div key={item.id} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 14px', borderRadius: 10, background: 'var(--bg-base)', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--text-primary)' }}>
                      {item.name}
                      {!item.is_mandatory && <span style={{ marginLeft: 6, fontSize: 11, color: 'var(--text-tertiary)', fontWeight: 400 }}>optional</span>}
                    </div>
                    {item.description && <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginTop: 1 }}>{item.description}</div>}
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
                    {item.quantity > 1 && `${item.quantity}${item.unit ? ' ' + item.unit : 'x'} · `}
                    ₹{Number(item.base_price).toLocaleString('en-IN')}
                  </div>
                  {!isLocked && (
                    <div style={{ display: 'flex', gap: 6 }}>
                      <button className="btn btn-secondary btn-sm" onClick={() => startEdit(item)}>Edit</button>
                      <button className="btn btn-sm" style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', color: '#ef4444' }} onClick={() => setConfirmDelete(item)}>✕</button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Add new item */}
          {!isLocked && (
            <div>
              <h4 style={{ margin: '0 0 12px', fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>Add New Item</h4>
              <form onSubmit={handleAdd} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 10 }}>
                  <input className="admin-input" value={newItem.name} onChange={(e) => setNF('name', e.target.value)} placeholder="Item name *" />
                  <input className="admin-input" type="number" min="0" value={newItem.base_price} onChange={(e) => setNF('base_price', e.target.value)} placeholder="Price (₹) *" />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
                  <input className="admin-input" type="number" min="1" value={newItem.quantity} onChange={(e) => setNF('quantity', e.target.value)} placeholder="Qty" />
                  <input className="admin-input" value={newItem.unit} onChange={(e) => setNF('unit', e.target.value)} placeholder="Unit (hrs, pcs…)" />
                  <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, cursor: 'pointer' }}>
                    <input type="checkbox" checked={newItem.is_mandatory} onChange={(e) => setNF('is_mandatory', e.target.checked)} />
                    Mandatory
                  </label>
                </div>
                <input className="admin-input" value={newItem.description} onChange={(e) => setNF('description', e.target.value)} placeholder="Description (optional)" />
                <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                  <button type="submit" className="btn btn-primary" disabled={addMutation.isPending}>
                    {addMutation.isPending ? 'Adding…' : '+ Add Item'}
                  </button>
                </div>
              </form>
            </div>
          )}
        </div>
      </div>

      <ConfirmDialog
        open={!!confirmDelete}
        onClose={() => setConfirmDelete(null)}
        onConfirm={() => deleteMutation.mutate(confirmDelete.id)}
        title="Remove Item"
        message={`Remove "${confirmDelete?.name}" from this package?`}
        loading={deleteMutation.isPending}
      />
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function VendorPackagesPage() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [editingPkg, setEditingPkg] = useState(null);
  const [managingItems, setManagingItems] = useState(null);
  const [confirmSubmit, setConfirmSubmit] = useState(null);
  const [confirmUnpublish, setConfirmUnpublish] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(null);

  const { data: vendor } = useQuery({
    queryKey: ['vendor', 'me'],
    queryFn: () => vendorProfileApi.getMe(),
    retry: (count, err) => err?.response?.status !== 404 && count < 2,
  });

  const { data: categories = [] } = useQuery({
    queryKey: ['package-categories'],
    queryFn: () => vendorPackagesApi.listCategories(),
  });

  const { data, isLoading } = useQuery({
    queryKey: ['vendor-packages'],
    queryFn: () => vendorPackagesApi.list({ per_page: 100 }),
    enabled: !!vendor,
  });

  const invalidate = () => qc.invalidateQueries(['vendor-packages']);

  const createMutation = useMutation({
    mutationFn: (body) => vendorPackagesApi.create({ ...body, vendor_id: vendor?.id }),
    onSuccess: () => { toast.success('Package created!'); invalidate(); setShowCreate(false); },
    onError: (err) => toast.error(err?.response?.data?.detail ?? 'Failed to create.'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, body }) => vendorPackagesApi.update(id, body),
    onSuccess: () => { toast.success('Package updated.'); invalidate(); setEditingPkg(null); },
    onError: (err) => toast.error(err?.response?.data?.detail ?? 'Failed to update.'),
  });

  const submitMutation = useMutation({
    mutationFn: (packageId) => vendorPackagesApi.submitForReview(packageId),
    onSuccess: () => { toast.success('Submitted for admin review.'); invalidate(); setConfirmSubmit(null); },
    onError: (err) => toast.error(err?.response?.data?.detail ?? 'Failed to submit.'),
  });

  const unpublishMutation = useMutation({
    mutationFn: (packageId) => vendorPackagesApi.unpublish(packageId),
    onSuccess: () => { toast.success('Package unpublished.'); invalidate(); setConfirmUnpublish(null); },
    onError: () => toast.error('Failed to unpublish.'),
  });

  const deleteMutation = useMutation({
    mutationFn: (packageId) => vendorPackagesApi.delete(packageId),
    onSuccess: () => { toast.success('Package deleted.'); invalidate(); setConfirmDelete(null); },
    onError: () => toast.error('Failed to delete.'),
  });

  const items = data?.items ?? [];

  if (!vendor) {
    return (
      <div style={{ padding: 48, textAlign: 'center' }}>
        <p style={{ color: 'var(--text-secondary)' }}>Please create your vendor profile first.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <h1>My Packages</h1>
          <p style={{ color: 'var(--text-secondary)' }}>Create packages and submit for admin approval to go live.</p>
        </div>
        <div className="admin-page-header-actions">
          <button className="btn btn-primary" onClick={() => setShowCreate(true)}>+ New Package</button>
        </div>
      </div>

      {/* Workflow hint */}
      <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start', background: 'rgba(59,130,246,0.07)', border: '1px solid rgba(59,130,246,0.18)', borderRadius: 10, padding: '11px 16px', marginBottom: 20, fontSize: 13, color: 'var(--color-info, #3b82f6)' }}>
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginTop: 1, flexShrink: 0 }}><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
        <span><strong>Workflow:</strong> Create → Add items → Submit for Review → Admin approves → Goes live on app.</span>
      </div>

      {isLoading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {[0, 1, 2].map((i) => <div key={i} className="skeleton skeleton-card" style={{ height: 68 }} />)}
        </div>
      ) : !items.length ? (
        <div style={{ textAlign: 'center', padding: 48 }}>
          <div style={{ fontSize: 40, marginBottom: 12 }}>📦</div>
          <p style={{ color: 'var(--text-secondary)', marginBottom: 16 }}>No packages yet. Create your first one.</p>
          <button className="btn btn-primary" onClick={() => setShowCreate(true)}>+ Create Package</button>
        </div>
      ) : (
        <div className="admin-table-wrapper">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Package</th>
                <th>Category</th>
                <th>Price</th>
                <th>Guests</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((p) => (
                <tr key={p.id}>
                  <td>
                    <div className="admin-user-name">{p.name}</div>
                    {p.short_description && (
                      <div className="admin-user-email" style={{ maxWidth: 280, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {p.short_description}
                      </div>
                    )}
                  </td>
                  <td style={{ color: 'var(--text-secondary)', fontSize: 13 }}>{p.category?.name ?? '—'}</td>
                  <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>₹{Number(p.base_price ?? 0).toLocaleString('en-IN')}</td>
                  <td style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                    {p.min_guests || p.max_guests
                      ? `${p.min_guests ?? '—'}–${p.max_guests ?? '—'}`
                      : '—'}
                  </td>
                  <td><StatusBadge status={p.status} /></td>
                  <td>
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                      <button className="btn btn-secondary btn-sm" onClick={() => setEditingPkg(p)}>Edit</button>
                      <button className="btn btn-secondary btn-sm" onClick={() => setManagingItems(p)}>Items</button>
                      {p.status === 'draft' && (
                        <button className="btn btn-primary btn-sm" onClick={() => setConfirmSubmit(p)}>Submit</button>
                      )}
                      {p.status === 'pending_review' && (
                        <span style={{ fontSize: 12, color: 'var(--text-tertiary)', display: 'flex', alignItems: 'center' }}>Under review…</span>
                      )}
                      {p.status === 'active' && (
                        <button className="btn btn-secondary btn-sm" onClick={() => setConfirmUnpublish(p)}>Unpublish</button>
                      )}
                      {(p.status === 'draft' || p.status === 'inactive' || p.status === 'archived') && (
                        <button className="btn btn-sm" style={{ background: 'transparent', border: '1px solid var(--border-subtle)', color: '#ef4444' }} onClick={() => setConfirmDelete(p)}>Delete</button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Modals */}
      {showCreate && (
        <PackageFormModal
          categories={categories}
          onClose={() => setShowCreate(false)}
          onSave={(body) => createMutation.mutate(body)}
          saving={createMutation.isPending}
        />
      )}
      {editingPkg && (
        <PackageFormModal
          initial={editingPkg}
          categories={categories}
          onClose={() => setEditingPkg(null)}
          onSave={(body) => updateMutation.mutate({ id: editingPkg.id, body })}
          saving={updateMutation.isPending}
        />
      )}
      {managingItems && (
        <PackageItemsModal pkg={managingItems} onClose={() => setManagingItems(null)} />
      )}

      <ConfirmDialog
        open={!!confirmSubmit}
        onClose={() => setConfirmSubmit(null)}
        onConfirm={() => submitMutation.mutate(confirmSubmit.id)}
        title="Submit for Review"
        message={`Submit "${confirmSubmit?.name}" for admin review? You won't be able to edit it until a decision is made.`}
        loading={submitMutation.isPending}
      />
      <ConfirmDialog
        open={!!confirmUnpublish}
        onClose={() => setConfirmUnpublish(null)}
        onConfirm={() => unpublishMutation.mutate(confirmUnpublish.id)}
        title="Unpublish Package"
        message={`Unpublish "${confirmUnpublish?.name}"? It will be hidden from the app.`}
        loading={unpublishMutation.isPending}
      />
      <ConfirmDialog
        open={!!confirmDelete}
        onClose={() => setConfirmDelete(null)}
        onConfirm={() => deleteMutation.mutate(confirmDelete.id)}
        title="Delete Package"
        message={`Permanently delete "${confirmDelete?.name}"? This cannot be undone.`}
        loading={deleteMutation.isPending}
      />
    </div>
  );
}
