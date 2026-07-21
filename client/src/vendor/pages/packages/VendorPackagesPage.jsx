import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { vendorProfileApi, vendorPackagesApi, vendorOccasionsApi, vendorThemesApi } from '../../api';
import { ConfirmDialog } from '../../../admin/components/ui/Modal';
import ImageUploadField from '../../components/ImageUploadField';

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

function PackageFormModal({ initial, occasions, themes, onClose, onSave, saving }) {
  const isEdit = !!initial;
  const [form, setForm] = useState({
    name: initial?.name ?? '',
    description: initial?.description ?? '',
    short_description: initial?.short_description ?? '',
    occasion_ids: initial?.occasion_ids ?? [],
    theme_ids: initial?.theme_ids ?? [],
    base_price: initial?.base_price ?? '',
    min_guests: initial?.min_guests ?? '',
    max_guests: initial?.max_guests ?? '',
    duration_hours: initial?.duration_hours ?? '',
    cover_image_url: initial?.cover_image_url ?? '',
    is_customizable: initial?.is_customizable ?? false,
    city_slug: initial?.city_slug ?? '',
  });
  const [errors, setErrors] = useState({});

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const toggleOccasion = (id) => {
    setForm((f) => ({
      ...f,
      occasion_ids: f.occasion_ids.includes(id)
        ? f.occasion_ids.filter((oid) => oid !== id)
        : [...f.occasion_ids, id],
    }));
  };

  const toggleTheme = (id) => {
    setForm((f) => ({
      ...f,
      theme_ids: f.theme_ids.includes(id)
        ? f.theme_ids.filter((tid) => tid !== id)
        : [...f.theme_ids, id],
    }));
  };

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
      occasion_ids: form.occasion_ids,
      // Themes only mean anything once customization is enabled — don't
      // silently carry over a stale selection if the vendor unchecks it.
      theme_ids: form.is_customizable ? form.theme_ids : [],
      base_price: Number(form.base_price),
      pricing_type: 'fixed',
      min_guests: form.min_guests !== '' ? Number(form.min_guests) : undefined,
      max_guests: form.max_guests !== '' ? Number(form.max_guests) : undefined,
      duration_hours: form.duration_hours !== '' ? Number(form.duration_hours) : undefined,
      cover_image_url: form.cover_image_url.trim() || undefined,
      is_customizable: form.is_customizable,
      city_slug: form.city_slug.trim().toLowerCase() || undefined,
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
          <div>
            <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 6 }}>Base Price (₹) *</label>
            <input className="admin-input" type="number" min="0" value={form.base_price} onChange={(e) => set('base_price', e.target.value)} placeholder="e.g. 15000" style={{ maxWidth: 220 }} />
            {errors.base_price && <p style={{ color: 'var(--color-error,#ef4444)', fontSize: 12, marginTop: 4 }}>{errors.base_price}</p>}
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 6 }}>Occasions</label>
            {!occasions.length ? (
              <p style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>No occasions available yet.</p>
            ) : (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {occasions.map((o) => {
                  const active = form.occasion_ids.includes(o.id);
                  return (
                    <button
                      type="button"
                      key={o.id}
                      onClick={() => toggleOccasion(o.id)}
                      className="btn btn-sm"
                      style={{
                        borderRadius: 99,
                        border: active ? '1px solid var(--color-primary,#6366f1)' : '1px solid var(--border-subtle)',
                        background: active ? 'rgba(99,102,241,0.12)' : 'transparent',
                        color: active ? 'var(--color-primary,#6366f1)' : 'var(--text-secondary)',
                      }}
                    >
                      {o.name}
                    </button>
                  );
                })}
              </div>
            )}
            <p style={{ margin: '6px 0 0', fontSize: 11, color: 'var(--text-tertiary)' }}>
              Select every occasion this package suits (e.g. Birthday, Baby Shower). Customers browsing by occasion will see it.
            </p>
          </div>
          <div className="form-row-3">
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
            <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 6 }}>Cover Image</label>
            <ImageUploadField
              value={form.cover_image_url}
              onChange={(url) => set('cover_image_url', url)}
              usage="package_image"
            />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 6 }}>
              Service City
              <span style={{ marginLeft: 6, fontSize: 11, fontWeight: 400, color: 'var(--text-tertiary)' }}>
                (city slug, e.g. noida, delhi, mumbai)
              </span>
            </label>
            <input
              className="admin-input"
              value={form.city_slug}
              onChange={(e) => set('city_slug', e.target.value.toLowerCase().replace(/\s+/g, '-'))}
              placeholder="e.g. noida"
            />
            <p style={{ margin: '4px 0 0', fontSize: 11, color: 'var(--text-tertiary)' }}>
              Customers in this city will see your package. Must match one of your operating cities set in your vendor profile.
            </p>
          </div>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, cursor: 'pointer', userSelect: 'none' }}>
            <input type="checkbox" checked={form.is_customizable} onChange={(e) => set('is_customizable', e.target.checked)} />
            Allow customers to customise this package
          </label>
          {form.is_customizable && (
            <div>
              <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 6 }}>Available Themes</label>
              {!themes.length ? (
                <p style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>No themes available yet.</p>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 10 }}>
                  {themes.map((t) => {
                    const active = form.theme_ids.includes(t.id);
                    const swatches = [t.colors?.primary, t.colors?.secondary, t.colors?.accent, t.colors?.background].filter(Boolean);
                    return (
                      <button
                        type="button"
                        key={t.id}
                        onClick={() => toggleTheme(t.id)}
                        className="btn btn-sm"
                        style={{
                          display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 8,
                          padding: '10px 12px', height: 'auto', textAlign: 'left',
                          borderRadius: 10,
                          border: active ? '1px solid var(--color-primary,#6366f1)' : '1px solid var(--border-subtle)',
                          background: active ? 'rgba(99,102,241,0.1)' : 'transparent',
                        }}
                      >
                        <div style={{ display: 'flex', gap: 4 }}>
                          {swatches.map((c, i) => (
                            <span key={i} style={{ width: 16, height: 16, borderRadius: '50%', background: c, border: '1px solid rgba(0,0,0,0.15)' }} />
                          ))}
                        </div>
                        <span style={{ fontSize: 12.5, fontWeight: 600, color: active ? 'var(--color-primary,#6366f1)' : 'var(--text-primary)' }}>
                          {t.name}
                        </span>
                      </button>
                    );
                  })}
                </div>
              )}
              <p style={{ margin: '6px 0 0', fontSize: 11, color: 'var(--text-tertiary)' }}>
                Not every theme suits every package — select only the ones you can actually deliver for this package. Customers will choose from these when booking.
              </p>
            </div>
          )}
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

// ── Common Items Modal (vendor-wide item templates) ─────────────────────────────
// Reusable items owned by the vendor, not tied to any one package. Attached
// to individual packages from the Package Items modal below.

function CommonItemsModal({ onClose }) {
  const qc = useQueryClient();
  const [newItem, setNewItem] = useState({ name: '', description: '', quantity: 1, max_quantity: '', unit: '', base_price: '' });
  const [confirmDelete, setConfirmDelete] = useState(null);

  const { data: items = [], isLoading } = useQuery({
    queryKey: ['vendor-common-items'],
    queryFn: () => vendorPackagesApi.listCommonItems(),
  });

  const invalidate = () => qc.invalidateQueries(['vendor-common-items']);

  const addMutation = useMutation({
    mutationFn: (body) => vendorPackagesApi.createCommonItem(body),
    onSuccess: () => { toast.success('Common item created.'); invalidate(); setNewItem({ name: '', description: '', quantity: 1, max_quantity: '', unit: '', base_price: '' }); },
    onError: (err) => toast.error(err?.response?.data?.detail ?? 'Failed to create item.'),
  });

  const deleteMutation = useMutation({
    mutationFn: (itemId) => vendorPackagesApi.deleteCommonItem(itemId),
    onSuccess: () => { toast.success('Common item deleted.'); invalidate(); setConfirmDelete(null); },
    onError: (err) => toast.error(err?.response?.data?.detail ?? 'Failed to delete item.'),
  });

  const setNF = (k, v) => setNewItem((f) => ({ ...f, [k]: v }));

  const handleAdd = (e) => {
    e.preventDefault();
    if (!newItem.name.trim()) return toast.error('Item name is required.');
    if (!newItem.base_price || isNaN(Number(newItem.base_price))) return toast.error('Enter a valid price.');
    addMutation.mutate({
      ...newItem,
      quantity: Number(newItem.quantity),
      max_quantity: newItem.max_quantity !== '' ? Number(newItem.max_quantity) : undefined,
      base_price: Number(newItem.base_price),
      unit: newItem.unit || undefined,
      description: newItem.description || undefined,
    });
  };

  return (
    <div className="admin-modal-overlay" onClick={onClose}>
      <div className="admin-modal lg" onClick={(e) => e.stopPropagation()}>
        <div className="admin-modal-header">
          <div>
            <h2 className="admin-modal-title">Common Items</h2>
            <p style={{ margin: '2px 0 0', fontSize: 12, color: 'var(--text-tertiary)' }}>
              Reusable items you can attach to any of your packages instead of recreating them each time.
            </p>
          </div>
          <button className="admin-modal-close" onClick={onClose}>×</button>
        </div>
        <div style={{ padding: '20px 24px 24px' }}>
          {isLoading ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 20 }}>
              {[0, 1].map((i) => <div key={i} className="skeleton skeleton-card" style={{ height: 56 }} />)}
            </div>
          ) : !items.length ? (
            <p style={{ color: 'var(--text-tertiary)', fontSize: 13, textAlign: 'center', padding: '16px 0', marginBottom: 4 }}>No common items yet. Add one below.</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 20 }}>
              {items.map((item) => (
                <div key={item.id} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 14px', borderRadius: 10, background: 'var(--bg-base)', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--text-primary)' }}>{item.name}</div>
                    {item.description && <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginTop: 1 }}>{item.description}</div>}
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
                    {item.quantity > 1 && `${item.quantity}${item.unit ? ' ' + item.unit : 'x'} · `}
                    ₹{Number(item.base_price).toLocaleString('en-IN')}
                  </div>
                  <button className="btn btn-sm" style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', color: '#ef4444' }} onClick={() => setConfirmDelete(item)}>✕</button>
                </div>
              ))}
            </div>
          )}

          <h4 style={{ margin: '0 0 12px', fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>Add Common Item</h4>
          <form onSubmit={handleAdd} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div className="form-row-2-1" style={{ gap: 10 }}>
              <input className="admin-input" value={newItem.name} onChange={(e) => setNF('name', e.target.value)} placeholder="Item name *" />
              <input className="admin-input" type="number" min="0" value={newItem.base_price} onChange={(e) => setNF('base_price', e.target.value)} placeholder="Price (₹) *" />
            </div>
            <div className="form-row-3" style={{ gap: 10 }}>
              <input className="admin-input" type="number" min="1" value={newItem.quantity} onChange={(e) => setNF('quantity', e.target.value)} placeholder="Qty" />
              <input className="admin-input" value={newItem.unit} onChange={(e) => setNF('unit', e.target.value)} placeholder="Unit (hrs, pcs…)" />
              <input className="admin-input" type="number" min={newItem.quantity || 1} value={newItem.max_quantity} onChange={(e) => setNF('max_quantity', e.target.value)} placeholder="Max qty (optional)" />
            </div>
            <input className="admin-input" value={newItem.description} onChange={(e) => setNF('description', e.target.value)} placeholder="Description (optional)" />
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button type="submit" className="btn btn-primary" disabled={addMutation.isPending}>
                {addMutation.isPending ? 'Adding…' : '+ Add Common Item'}
              </button>
            </div>
          </form>
        </div>
      </div>

      <ConfirmDialog
        open={!!confirmDelete}
        onClose={() => setConfirmDelete(null)}
        onConfirm={() => deleteMutation.mutate(confirmDelete.id)}
        title="Delete Common Item"
        message={`Delete "${confirmDelete?.name}"? It will be removed from every package it's attached to.`}
        loading={deleteMutation.isPending}
      />
    </div>
  );
}

// ── Package Items Modal ────────────────────────────────────────────────────────

function PackageItemsModal({ pkg, onClose }) {
  const qc = useQueryClient();
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [newItem, setNewItem] = useState({ name: '', description: '', quantity: 1, max_quantity: '', unit: '', base_price: '', is_mandatory: true, cover_image_url: '' });
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [managingImagesFor, setManagingImagesFor] = useState(null);
  const [attachingId, setAttachingId] = useState('');

  const { data: items = [], isLoading } = useQuery({
    queryKey: ['pkg-items', pkg.id],
    queryFn: () => vendorPackagesApi.listItems(pkg.id),
  });

  const { data: commonItems = [] } = useQuery({
    queryKey: ['vendor-common-items'],
    queryFn: () => vendorPackagesApi.listCommonItems(),
  });

  const invalidate = () => qc.invalidateQueries(['pkg-items', pkg.id]);

  const addMutation = useMutation({
    mutationFn: (body) => vendorPackagesApi.addItem(pkg.id, { ...body, package_id: pkg.id }),
    onSuccess: () => { toast.success('Item added.'); invalidate(); setNewItem({ name: '', description: '', quantity: 1, max_quantity: '', unit: '', base_price: '', is_mandatory: true, cover_image_url: '' }); },
    onError: (err) => toast.error(err?.response?.data?.detail ?? 'Failed to add item.'),
  });

  const attachMutation = useMutation({
    mutationFn: (itemId) => vendorPackagesApi.attachCommonItem(pkg.id, itemId),
    onSuccess: () => { toast.success('Common item attached.'); invalidate(); setAttachingId(''); },
    onError: (err) => toast.error(err?.response?.data?.detail ?? 'Failed to attach item.'),
  });

  const detachMutation = useMutation({
    mutationFn: (itemId) => vendorPackagesApi.detachCommonItem(pkg.id, itemId),
    onSuccess: () => { toast.success('Common item detached.'); invalidate(); },
    onError: (err) => toast.error(err?.response?.data?.detail ?? 'Failed to detach item.'),
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
    setEditForm({ name: item.name, description: item.description ?? '', quantity: item.quantity, max_quantity: item.max_quantity ?? '', unit: item.unit ?? '', base_price: item.base_price, is_mandatory: item.is_mandatory, cover_image_url: item.cover_image_url ?? '' });
  };

  const setNF = (k, v) => setNewItem((f) => ({ ...f, [k]: v }));
  const setEF = (k, v) => setEditForm((f) => ({ ...f, [k]: v }));

  const handleAdd = (e) => {
    e.preventDefault();
    if (!newItem.name.trim()) return toast.error('Item name is required.');
    if (!newItem.base_price || isNaN(Number(newItem.base_price))) return toast.error('Enter a valid price.');
    addMutation.mutate({
      ...newItem,
      quantity: Number(newItem.quantity),
      max_quantity: newItem.max_quantity !== '' ? Number(newItem.max_quantity) : undefined,
      base_price: Number(newItem.base_price),
      unit: newItem.unit || undefined,
      description: newItem.description || undefined,
      cover_image_url: newItem.cover_image_url || undefined,
    });
  };

  const handleUpdate = (itemId) => {
    if (!editForm.name.trim()) return toast.error('Item name is required.');
    updateMutation.mutate({
      itemId,
      body: {
        ...editForm,
        quantity: Number(editForm.quantity),
        max_quantity: editForm.max_quantity !== '' ? Number(editForm.max_quantity) : null,
        base_price: Number(editForm.base_price),
        unit: editForm.unit || undefined,
        description: editForm.description || undefined,
        cover_image_url: editForm.cover_image_url || null,
      },
    });
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
                  <div className="form-row-2-1" style={{ gap: 10 }}>
                    <input className="admin-input" value={editForm.name} onChange={(e) => setEF('name', e.target.value)} placeholder="Item name" />
                    <input className="admin-input" type="number" min="0" value={editForm.base_price} onChange={(e) => setEF('base_price', e.target.value)} placeholder="Price (₹)" />
                  </div>
                  <div className="form-row-3" style={{ gap: 10 }}>
                    <input className="admin-input" type="number" min="1" value={editForm.quantity} onChange={(e) => setEF('quantity', e.target.value)} placeholder="Qty" />
                    <input className="admin-input" value={editForm.unit} onChange={(e) => setEF('unit', e.target.value)} placeholder="Unit (hrs, pcs…)" />
                    <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, cursor: 'pointer' }}>
                      <input type="checkbox" checked={editForm.is_mandatory} onChange={(e) => setEF('is_mandatory', e.target.checked)} />
                      Mandatory
                    </label>
                  </div>
                  <div>
                    <input className="admin-input" type="number" min={editForm.quantity || 1} value={editForm.max_quantity} onChange={(e) => setEF('max_quantity', e.target.value)} placeholder="Max customer can pick (optional)" />
                    <p style={{ margin: '4px 0 0', fontSize: 11, color: 'var(--text-tertiary)' }}>Leave blank for no cap — e.g. cap balloon bunches at 20.</p>
                  </div>
                  <input className="admin-input" value={editForm.description} onChange={(e) => setEF('description', e.target.value)} placeholder="Description (optional)" />
                  <ImageUploadField
                    label="Cover image"
                    value={editForm.cover_image_url}
                    onChange={(url) => setEF('cover_image_url', url)}
                    usage="package_image"
                    placeholder="Cover image URL (https://...)"
                  />
                  <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                    <button className="btn btn-secondary btn-sm" onClick={() => setEditingId(null)}>Cancel</button>
                    <button className="btn btn-primary btn-sm" onClick={() => handleUpdate(item.id)} disabled={updateMutation.isPending}>Save</button>
                  </div>
                </div>
              ) : (
                <div key={item.id} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 14px', borderRadius: 10, background: 'var(--bg-base)', border: '1px solid var(--border-subtle)' }}>
                  {(item.cover_image_url || item.images?.[0]?.image_url) && (
                    <img
                      src={item.cover_image_url || item.images[0].image_url}
                      alt=""
                      style={{ width: 42, height: 42, borderRadius: 8, objectFit: 'cover', border: '1px solid var(--border-subtle)', flexShrink: 0 }}
                      onError={(e) => { e.target.style.display = 'none'; }}
                    />
                  )}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--text-primary)' }}>
                      {item.name}
                      {item.is_common && <span style={{ marginLeft: 6, fontSize: 11, color: 'var(--color-primary,#6366f1)', fontWeight: 400 }}>common</span>}
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
                      {item.is_common ? (
                        <button
                          className="btn btn-sm"
                          style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', color: '#ef4444' }}
                          onClick={() => detachMutation.mutate(item.id)}
                          disabled={detachMutation.isPending}
                        >
                          Detach
                        </button>
                      ) : (
                        <>
                          <button className="btn btn-secondary btn-sm" onClick={() => setManagingImagesFor(item)}>
                            Photos{item.images?.length ? ` (${item.images.length})` : ''}
                          </button>
                          <button className="btn btn-secondary btn-sm" onClick={() => startEdit(item)}>Edit</button>
                          <button className="btn btn-sm" style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', color: '#ef4444' }} onClick={() => setConfirmDelete(item)}>✕</button>
                        </>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {!isLocked && commonItems.length > 0 && (
            <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 20 }}>
              <select
                className="admin-input"
                value={attachingId}
                onChange={(e) => setAttachingId(e.target.value)}
                style={{ flex: 1 }}
              >
                <option value="">Attach a common item…</option>
                {commonItems
                  .filter((ci) => !items.some((i) => i.id === ci.id))
                  .map((ci) => (
                    <option key={ci.id} value={ci.id}>
                      {ci.name} · ₹{Number(ci.base_price).toLocaleString('en-IN')}
                    </option>
                  ))}
              </select>
              <button
                className="btn btn-secondary"
                disabled={!attachingId || attachMutation.isPending}
                onClick={() => attachMutation.mutate(attachingId)}
              >
                {attachMutation.isPending ? 'Attaching…' : 'Attach'}
              </button>
            </div>
          )}

          {/* Add new item */}
          {!isLocked && (
            <div>
              <h4 style={{ margin: '0 0 12px', fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>Add New Item</h4>
              <form onSubmit={handleAdd} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div className="form-row-2-1" style={{ gap: 10 }}>
                  <input className="admin-input" value={newItem.name} onChange={(e) => setNF('name', e.target.value)} placeholder="Item name *" />
                  <input className="admin-input" type="number" min="0" value={newItem.base_price} onChange={(e) => setNF('base_price', e.target.value)} placeholder="Price (₹) *" />
                </div>
                <div className="form-row-3" style={{ gap: 10 }}>
                  <input className="admin-input" type="number" min="1" value={newItem.quantity} onChange={(e) => setNF('quantity', e.target.value)} placeholder="Qty" />
                  <input className="admin-input" value={newItem.unit} onChange={(e) => setNF('unit', e.target.value)} placeholder="Unit (hrs, pcs…)" />
                  <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, cursor: 'pointer' }}>
                    <input type="checkbox" checked={newItem.is_mandatory} onChange={(e) => setNF('is_mandatory', e.target.checked)} />
                    Mandatory
                  </label>
                </div>
                <div>
                  <input className="admin-input" type="number" min={newItem.quantity || 1} value={newItem.max_quantity} onChange={(e) => setNF('max_quantity', e.target.value)} placeholder="Max customer can pick (optional)" />
                  <p style={{ margin: '4px 0 0', fontSize: 11, color: 'var(--text-tertiary)' }}>Leave blank for no cap — e.g. cap balloon bunches at 20. More gallery photos can be added after creating the item.</p>
                </div>
                <input className="admin-input" value={newItem.description} onChange={(e) => setNF('description', e.target.value)} placeholder="Description (optional)" />
                <ImageUploadField
                  label="Cover image (optional)"
                  value={newItem.cover_image_url}
                  onChange={(url) => setNF('cover_image_url', url)}
                  usage="package_image"
                  placeholder="Cover image URL (https://...)"
                />
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

      {managingImagesFor && (
        <PackageItemImagesModal
          pkgId={pkg.id}
          item={managingImagesFor}
          onClose={() => setManagingImagesFor(null)}
          onChanged={invalidate}
        />
      )}
    </div>
  );
}

// ── Package Item Photos Modal ───────────────────────────────────────────────────
// Same idea as the package-level gallery, scoped to one item — e.g. photos
// of the actual balloon arrangement, cake design, etc. Shown to customers as
// a swipeable slider on that item in the plan-flow booking screen.

function PackageItemImagesModal({ pkgId, item, onClose, onChanged }) {
  const qc = useQueryClient();
  const [uploadUrl, setUploadUrl] = useState('');
  const [confirmDelete, setConfirmDelete] = useState(null);

  const { data: liveItem, isLoading } = useQuery({
    queryKey: ['pkg-item-images', pkgId, item.id],
    queryFn: () => vendorPackagesApi.listItems(pkgId).then((items) => items.find((i) => i.id === item.id) ?? item),
    initialData: item,
  });
  const images = liveItem?.images ?? [];
  const coverUrl = liveItem?.cover_image_url ?? null;

  const invalidate = () => {
    qc.invalidateQueries(['pkg-item-images', pkgId, item.id]);
    qc.invalidateQueries(['pkg-items', pkgId]);
    onChanged?.();
  };

  const addMutation = useMutation({
    mutationFn: (imageUrl) => vendorPackagesApi.addItemImage(pkgId, item.id, { image_url: imageUrl }),
    onSuccess: () => { toast.success('Image added.'); invalidate(); setUploadUrl(''); },
    onError: (err) => toast.error(err?.response?.data?.detail ?? 'Failed to add image.'),
  });

  const deleteMutation = useMutation({
    mutationFn: (imageId) => vendorPackagesApi.deleteItemImage(pkgId, item.id, imageId),
    onSuccess: () => { toast.success('Image removed.'); invalidate(); setConfirmDelete(null); },
    onError: () => toast.error('Failed to remove image.'),
  });

  const coverMutation = useMutation({
    mutationFn: (imageUrl) => vendorPackagesApi.updateItem(pkgId, item.id, { cover_image_url: imageUrl }),
    onSuccess: () => { toast.success('Cover updated.'); invalidate(); },
    onError: () => toast.error('Failed to set cover.'),
  });

  return (
    <div className="admin-modal-overlay" onClick={onClose}>
      <div className="admin-modal" onClick={(e) => e.stopPropagation()}>
        <div className="admin-modal-header">
          <div>
            <h2 className="admin-modal-title">Item Photos</h2>
            <p style={{ margin: '2px 0 0', fontSize: 12, color: 'var(--text-tertiary)' }}>{item.name}</p>
          </div>
          <button className="admin-modal-close" onClick={onClose}>×</button>
        </div>
        <div style={{ padding: '20px 24px 24px' }}>
          {isLoading ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(110px, 1fr))', gap: 10, marginBottom: 20 }}>
              {[0, 1].map((i) => <div key={i} className="skeleton" style={{ height: 90, borderRadius: 10 }} />)}
            </div>
          ) : images.length > 0 ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(110px, 1fr))', gap: 10, marginBottom: 20 }}>
              {images.map((img) => {
                const isCover = coverUrl === img.image_url;
                return (
                  <div key={img.id} style={{ position: 'relative', borderRadius: 10, overflow: 'hidden', border: isCover ? '2px solid var(--color-primary,#6366f1)' : '1px solid var(--border-subtle)', aspectRatio: '1/1', background: 'var(--bg-base)' }}>
                    <img src={img.image_url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} onError={(e) => { e.target.style.display = 'none'; }} />
                    <button
                      onClick={() => setConfirmDelete(img)}
                      style={{ position: 'absolute', top: 4, right: 4, width: 20, height: 20, borderRadius: '50%', border: 'none', background: 'rgba(239,68,68,0.85)', color: '#fff', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11 }}
                    >×</button>
                    {isCover ? (
                      <span style={{ position: 'absolute', bottom: 4, left: 4, padding: '2px 7px', borderRadius: 6, background: 'var(--color-primary,#6366f1)', color: '#fff', fontSize: 10, fontWeight: 600 }}>Cover</span>
                    ) : (
                      <button
                        onClick={() => coverMutation.mutate(img.image_url)}
                        disabled={coverMutation.isPending}
                        style={{ position: 'absolute', bottom: 4, left: 4, padding: '2px 7px', borderRadius: 6, border: 'none', background: 'rgba(0,0,0,0.55)', color: '#fff', fontSize: 10, cursor: 'pointer' }}
                      >Set as cover</button>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <p style={{ color: 'var(--text-tertiary)', fontSize: 13, marginBottom: 16 }}>No photos yet for this item.</p>
          )}

          <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
            <div style={{ flex: 1 }}>
              <ImageUploadField value={uploadUrl} onChange={setUploadUrl} usage="package_image" placeholder="Image URL (https://...)" />
            </div>
            <button
              className="btn btn-primary"
              disabled={!uploadUrl || addMutation.isPending}
              onClick={() => addMutation.mutate(uploadUrl)}
            >
              {addMutation.isPending ? 'Adding…' : '+ Add'}
            </button>
          </div>
        </div>
      </div>

      <ConfirmDialog
        open={!!confirmDelete}
        onClose={() => setConfirmDelete(null)}
        onConfirm={() => deleteMutation.mutate(confirmDelete.id)}
        title="Remove Photo"
        message="Remove this photo from the item?"
        loading={deleteMutation.isPending}
      />
    </div>
  );
}

// ── Package Gallery Modal ───────────────────────────────────────────────────────
// Additional images beyond the single cover image (set in the main package
// form) — shown to customers as a swipeable slider on the package detail
// page, with the cover image always first.

function PackageGalleryModal({ pkg, onClose }) {
  const qc = useQueryClient();
  const [uploadUrl, setUploadUrl] = useState('');
  const [confirmDelete, setConfirmDelete] = useState(null);

  const { data: gallery = [], isLoading } = useQuery({
    queryKey: ['pkg-gallery', pkg.id],
    queryFn: () => vendorPackagesApi.listGallery(pkg.id),
  });

  const invalidate = () => qc.invalidateQueries(['pkg-gallery', pkg.id]);

  const addMutation = useMutation({
    mutationFn: (fileUrl) => vendorPackagesApi.addGalleryItem(pkg.id, { file_url: fileUrl }),
    onSuccess: () => { toast.success('Image added.'); invalidate(); setUploadUrl(''); },
    onError: (err) => toast.error(err?.response?.data?.detail ?? 'Failed to add image.'),
  });

  const deleteMutation = useMutation({
    mutationFn: (galleryId) => vendorPackagesApi.deleteGalleryItem(pkg.id, galleryId),
    onSuccess: () => { toast.success('Image removed.'); invalidate(); setConfirmDelete(null); },
    onError: () => toast.error('Failed to remove image.'),
  });

  return (
    <div className="admin-modal-overlay" onClick={onClose}>
      <div className="admin-modal lg" onClick={(e) => e.stopPropagation()}>
        <div className="admin-modal-header">
          <div>
            <h2 className="admin-modal-title">Package Photos</h2>
            <p style={{ margin: '2px 0 0', fontSize: 12, color: 'var(--text-tertiary)' }}>{pkg.name}</p>
          </div>
          <button className="admin-modal-close" onClick={onClose}>×</button>
        </div>
        <div style={{ padding: '20px 24px 24px' }}>
          <p style={{ fontSize: 12.5, color: 'var(--text-tertiary)', marginBottom: 16 }}>
            The cover image (set on the package form) always shows first to customers. Add more photos here — customers can swipe through all of them on the package page.
          </p>

          {isLoading ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 10, marginBottom: 20 }}>
              {[0, 1, 2].map((i) => <div key={i} className="skeleton" style={{ height: 100, borderRadius: 10 }} />)}
            </div>
          ) : gallery.length > 0 ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 10, marginBottom: 20 }}>
              {gallery.map((item) => (
                <div key={item.id} style={{ position: 'relative', borderRadius: 10, overflow: 'hidden', border: '1px solid var(--border-subtle)', aspectRatio: '4/3', background: 'var(--bg-base)' }}>
                  <img src={item.file_url} alt={item.caption ?? ''} style={{ width: '100%', height: '100%', objectFit: 'cover' }} onError={(e) => { e.target.style.display = 'none'; }} />
                  <button
                    onClick={() => setConfirmDelete(item)}
                    style={{ position: 'absolute', top: 5, right: 5, width: 22, height: 22, borderRadius: '50%', border: 'none', background: 'rgba(239,68,68,0.85)', color: '#fff', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12 }}
                  >×</button>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: 'var(--text-tertiary)', fontSize: 13, marginBottom: 16 }}>No additional photos yet. Add your first one below.</p>
          )}

          <h4 style={{ margin: '0 0 12px', fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>Add Photo</h4>
          <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
            <div style={{ flex: 1 }}>
              <ImageUploadField value={uploadUrl} onChange={setUploadUrl} usage="package_image" placeholder="Image URL (https://...)" />
            </div>
            <button
              className="btn btn-primary"
              disabled={!uploadUrl || addMutation.isPending}
              onClick={() => addMutation.mutate(uploadUrl)}
            >
              {addMutation.isPending ? 'Adding…' : '+ Add'}
            </button>
          </div>
        </div>
      </div>

      <ConfirmDialog
        open={!!confirmDelete}
        onClose={() => setConfirmDelete(null)}
        onConfirm={() => deleteMutation.mutate(confirmDelete.id)}
        title="Remove Photo"
        message="Remove this photo from the package gallery?"
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
  const [managingGallery, setManagingGallery] = useState(null);
  const [showCommonItems, setShowCommonItems] = useState(false);
  const [confirmSubmit, setConfirmSubmit] = useState(null);
  const [confirmUnpublish, setConfirmUnpublish] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(null);

  const { data: vendor } = useQuery({
    queryKey: ['vendor', 'me'],
    queryFn: () => vendorProfileApi.getMe(),
    retry: (count, err) => err?.response?.status !== 404 && count < 2,
  });

  const { data: occasionsPage } = useQuery({
    queryKey: ['vendor-occasions'],
    queryFn: () => vendorOccasionsApi.list({ is_active: true }),
  });
  const occasions = occasionsPage?.items ?? [];

  const { data: themes = [] } = useQuery({
    queryKey: ['vendor-themes'],
    queryFn: () => vendorThemesApi.list(),
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
          <button className="btn btn-secondary" onClick={() => setShowCommonItems(true)}>Common Items</button>
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
                <th>Occasions</th>
                <th>City</th>
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
                  <td style={{ color: 'var(--text-secondary)', fontSize: 13, maxWidth: 200 }}>
                    {(p.occasion_ids ?? []).length
                      ? p.occasion_ids
                          .map((id) => occasions.find((o) => o.id === id)?.name)
                          .filter(Boolean)
                          .join(', ')
                      : '—'}
                  </td>
                  <td style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                    {p.city_slug ? <code style={{ fontSize: 11 }}>{p.city_slug}</code> : <span style={{ color: 'var(--color-error,#ef4444)' }}>Not set</span>}
                  </td>
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
                      <button className="btn btn-secondary btn-sm" onClick={() => setManagingGallery(p)}>Photos</button>
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
          occasions={occasions}
          themes={themes}
          onClose={() => setShowCreate(false)}
          onSave={(body) => createMutation.mutate(body)}
          saving={createMutation.isPending}
        />
      )}
      {editingPkg && (
        <PackageFormModal
          initial={editingPkg}
          occasions={occasions}
          themes={themes}
          onClose={() => setEditingPkg(null)}
          onSave={(body) => updateMutation.mutate({ id: editingPkg.id, body })}
          saving={updateMutation.isPending}
        />
      )}
      {managingItems && (
        <PackageItemsModal pkg={managingItems} onClose={() => setManagingItems(null)} />
      )}
      {managingGallery && (
        <PackageGalleryModal pkg={managingGallery} onClose={() => setManagingGallery(null)} />
      )}
      {showCommonItems && (
        <CommonItemsModal onClose={() => setShowCommonItems(false)} />
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
