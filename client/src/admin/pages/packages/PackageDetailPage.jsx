import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { packagesApi } from '../../api';
import { formatDate, formatCurrency, initials } from '../../utils/format';
import StatusBadge from '../../components/ui/StatusBadge';
import { SkeletonCard } from '../../components/ui/Skeleton';
import { ConfirmDialog } from '../../components/ui/Modal';

const EMPTY_ITEM = { name: '', description: '', quantity: 1, unit: '', base_price: '', is_mandatory: true };

function Section({ title, children }) {
  return (
    <div className="admin-detail-section">
      {title && <div className="admin-detail-section-title">{title}</div>}
      {children}
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div className="admin-detail-row">
      <div className="admin-detail-label">{label}</div>
      <div className="admin-detail-value">{value ?? '—'}</div>
    </div>
  );
}

const VENDOR_TYPE_LABELS = {
  decorator: 'Decorator',
  caterer: 'Caterer',
  photographer: 'Photographer',
  videographer: 'Videographer',
  baker: 'Baker',
  florist: 'Florist',
  entertainer: 'Entertainer',
  venue: 'Venue',
  planner: 'Planner',
  makeup_artist: 'Makeup Artist',
  mehndi_artist: 'Mehndi Artist',
  music: 'Music',
  multi_service: 'Multi-Service',
  other: 'Other',
};

export default function PackageDetailPage() {
  const { packageId } = useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();

  const { data: pkg, isLoading } = useQuery({
    queryKey: ['package', packageId],
    queryFn: () => packagesApi.get(packageId),
  });

  const invalidate = () => qc.invalidateQueries(['package', packageId]);

  const approveMutation = useMutation({
    mutationFn: () => packagesApi.approve(packageId),
    onSuccess: () => { toast.success('Package approved and published'); invalidate(); },
    onError: () => toast.error('Failed to approve package'),
  });

  const rejectMutation = useMutation({
    mutationFn: () => packagesApi.reject(packageId),
    onSuccess: () => { toast.success('Package rejected — returned to draft'); invalidate(); },
    onError: () => toast.error('Failed to reject package'),
  });

  const [showAddItem, setShowAddItem] = useState(false);
  const [newItem, setNewItem] = useState(EMPTY_ITEM);
  const [editingItemId, setEditingItemId] = useState(null);
  const [editItemForm, setEditItemForm] = useState({});
  const [confirmDeleteItem, setConfirmDeleteItem] = useState(null);

  const addItemMutation = useMutation({
    mutationFn: (body) => packagesApi.addItem(packageId, { ...body, package_id: packageId }),
    onSuccess: () => { toast.success('Item added.'); invalidate(); setNewItem(EMPTY_ITEM); setShowAddItem(false); },
    onError: (err) => toast.error(err?.response?.data?.detail ?? 'Failed to add item.'),
  });

  const updateItemMutation = useMutation({
    mutationFn: ({ itemId, body }) => packagesApi.updateItem(packageId, itemId, body),
    onSuccess: () => { toast.success('Item updated.'); invalidate(); setEditingItemId(null); },
    onError: (err) => toast.error(err?.response?.data?.detail ?? 'Failed to update item.'),
  });

  const deleteItemMutation = useMutation({
    mutationFn: (itemId) => packagesApi.deleteItem(packageId, itemId),
    onSuccess: () => { toast.success('Item removed.'); invalidate(); setConfirmDeleteItem(null); },
    onError: () => toast.error('Failed to remove item.'),
  });

  const setNF = (k, v) => setNewItem((f) => ({ ...f, [k]: v }));
  const setEF = (k, v) => setEditItemForm((f) => ({ ...f, [k]: v }));

  const startEditItem = (item) => {
    setEditingItemId(item.id);
    setEditItemForm({
      name: item.name,
      description: item.description ?? '',
      quantity: item.quantity,
      unit: item.unit ?? '',
      base_price: item.base_price,
      is_mandatory: item.is_mandatory,
    });
  };

  const handleAddItem = (e) => {
    e.preventDefault();
    if (!newItem.name.trim()) return toast.error('Item name is required.');
    if (!newItem.base_price || isNaN(Number(newItem.base_price))) return toast.error('Enter a valid price.');
    addItemMutation.mutate({
      ...newItem,
      quantity: Number(newItem.quantity),
      base_price: Number(newItem.base_price),
      unit: newItem.unit || undefined,
      description: newItem.description || undefined,
    });
  };

  const handleUpdateItem = (itemId) => {
    if (!editItemForm.name.trim()) return toast.error('Item name is required.');
    updateItemMutation.mutate({
      itemId,
      body: {
        ...editItemForm,
        quantity: Number(editItemForm.quantity),
        base_price: Number(editItemForm.base_price),
        unit: editItemForm.unit || undefined,
        description: editItemForm.description || undefined,
      },
    });
  };

  if (isLoading) return (
    <div>
      <div className="admin-page-header">
        <button className="btn btn-ghost" onClick={() => navigate(-1)}>← Back</button>
      </div>
      {[1, 2, 3].map(i => <SkeletonCard key={i} height={160} />)}
    </div>
  );

  if (!pkg) return <div className="admin-empty"><div className="admin-empty-title">Package not found</div></div>;

  const status = pkg.status?.toLowerCase();
  const items = pkg.items ?? [];

  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <button className="btn btn-ghost" onClick={() => navigate(-1)}>←</button>
            {pkg.cover_image_url ? (
              <img
                src={pkg.cover_image_url}
                alt=""
                style={{ width: 44, height: 44, objectFit: 'cover', borderRadius: 8 }}
              />
            ) : (
              <div className="admin-avatar lg" style={{ background: 'var(--brand-100)', color: 'var(--brand-700)', fontSize: 18 }}>
                {pkg.name?.charAt(0) ?? 'P'}
              </div>
            )}
            <div>
              <h1 style={{ marginBottom: 2 }}>{pkg.name}</h1>
              <StatusBadge status={status} />
            </div>
          </div>
        </div>
        <div className="admin-page-header-actions">
          {status === 'pending_review' && (
            <>
              <button className="btn btn-success" onClick={() => approveMutation.mutate()} disabled={approveMutation.isPending}>
                Approve
              </button>
              <button className="btn btn-danger" onClick={() => rejectMutation.mutate()} disabled={rejectMutation.isPending}>
                Reject
              </button>
            </>
          )}
        </div>
      </div>

      <div className="admin-metric-grid" style={{ marginBottom: 28 }}>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Base Price</div>
          <div className="admin-metric-value">{formatCurrency(pkg.base_price ?? 0, pkg.currency)}</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Bookings</div>
          <div className="admin-metric-value">{pkg.booking_count ?? 0}</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Avg Rating</div>
          <div className="admin-metric-value">
            ⭐ {pkg.average_rating ? Number(pkg.average_rating).toFixed(1) : '—'}
          </div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Reviews</div>
          <div className="admin-metric-value">{pkg.review_count ?? 0}</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Inclusions</div>
          <div className="admin-metric-value">{pkg.inclusions_count ?? 0}</div>
        </div>
      </div>

      <div className="grid-2" style={{ gap: 24, rowGap: 28 }}>
        <div className="admin-card">
          <div className="admin-card-header"><div className="admin-card-title">Vendor</div></div>
          <div className="admin-card-body">
            {pkg.vendor ? (
              <>
                <div
                  style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16, cursor: 'pointer' }}
                  onClick={() => navigate(`/admin/vendors/${pkg.vendor.id}`)}
                  title="View vendor profile"
                >
                  <div className="admin-avatar lg" style={{ background: 'var(--brand-100)', color: 'var(--brand-700)', fontSize: 16 }}>
                    {initials(pkg.vendor.business_name)}
                  </div>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontWeight: 600, fontSize: 14.5, color: 'var(--text-primary)' }}>{pkg.vendor.business_name}</div>
                    <div style={{ fontSize: 12.5, color: 'var(--text-secondary)' }}>{pkg.vendor.owner_full_name ?? '—'}</div>
                  </div>
                </div>
                <Section>
                  <Row label="Vendor Code" value={<code className="admin-code">{pkg.vendor.slug}</code>} />
                  <Row label="Type" value={VENDOR_TYPE_LABELS[pkg.vendor.vendor_type] ?? pkg.vendor.vendor_type} />
                  <Row label="Business Name" value={pkg.vendor.business_name} />
                  <Row label="Owner" value={pkg.vendor.owner_full_name} />
                  <Row label="City" value={pkg.city_slug} />
                </Section>
              </>
            ) : (
              <p style={{ color: 'var(--text-secondary)' }}>No vendor assigned.</p>
            )}
          </div>
        </div>

        <div className="admin-card">
          <div className="admin-card-header"><div className="admin-card-title">Package Info</div></div>
          <div className="admin-card-body">
            <Section>
              <Row label="Name" value={pkg.name} />
              <Row label="Slug" value={<code className="admin-code">{pkg.slug}</code>} />
              <Row label="Short Description" value={pkg.short_description} />
              <Row label="Status" value={<StatusBadge status={status} />} />
              <Row label="Currency" value={pkg.currency} />
              <Row label="Guests" value={pkg.min_guests || pkg.max_guests ? `${pkg.min_guests ?? '—'} – ${pkg.max_guests ?? '—'}` : '—'} />
              <Row label="Duration" value={pkg.duration_hours ? `${pkg.duration_hours} hrs` : '—'} />
              <Row label="Display Order" value={pkg.display_order} />
              <Row label="Customizable" value={pkg.is_customizable ? 'Yes' : 'No'} />
              <Row label="Featured" value={pkg.is_featured ? 'Yes' : 'No'} />
              <Row label="Created" value={formatDate(pkg.created_at)} />
              <Row label="Updated" value={formatDate(pkg.updated_at)} />
            </Section>
          </div>
        </div>

        <div className="admin-card" style={{ gridColumn: '1 / -1' }}>
          <div className="admin-card-header"><div className="admin-card-title">Description</div></div>
          <div className="admin-card-body">
            <p style={{ whiteSpace: 'pre-wrap', color: 'var(--text-secondary)' }}>
              {pkg.description || 'No description provided.'}
            </p>
          </div>
        </div>

        <div className="admin-card">
          <div className="admin-card-header"><div className="admin-card-title">Pricing</div></div>
          <div className="admin-card-body">
            {pkg.pricing ? (
              <Section>
                <Row label="Pricing Type" value={pkg.pricing.pricing_type?.replace(/_/g, ' ')} />
                <Row label="Base Price" value={formatCurrency(pkg.pricing.base_price ?? 0, pkg.pricing.currency)} />
                <Row label="Min Price" value={pkg.pricing.min_price != null ? formatCurrency(pkg.pricing.min_price, pkg.pricing.currency) : '—'} />
                <Row label="Max Price" value={pkg.pricing.max_price != null ? formatCurrency(pkg.pricing.max_price, pkg.pricing.currency) : '—'} />
                <Row label="Price / Person" value={pkg.pricing.price_per_person != null ? formatCurrency(pkg.pricing.price_per_person, pkg.pricing.currency) : '—'} />
              </Section>
            ) : (
              <p style={{ color: 'var(--text-tertiary)', fontSize: 13, textAlign: 'center', padding: '16px 0' }}>No pricing configuration set.</p>
            )}
          </div>
        </div>

        <div className="admin-card">
          <div className="admin-card-header"><div className="admin-card-title">Active Discounts</div></div>
          <div className="admin-card-body">
            {pkg.discounts?.length ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {pkg.discounts.map((d) => (
                  <div key={d.id} style={{ padding: '10px 14px', borderRadius: 10, background: 'var(--bg-base)', border: '1px solid var(--border-subtle)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--text-primary)' }}>{d.title}</div>
                      <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--brand-600)' }}>
                        {d.discount_type === 'percentage' ? `${d.discount_value}%` : formatCurrency(d.discount_value)}
                      </div>
                    </div>
                    {d.description && <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginTop: 2 }}>{d.description}</div>}
                  </div>
                ))}
              </div>
            ) : (
              <p style={{ color: 'var(--text-tertiary)', fontSize: 13, textAlign: 'center', padding: '16px 0' }}>No active discounts.</p>
            )}
          </div>
        </div>

        <div className="admin-card" style={{ gridColumn: '1 / -1' }}>
          <div className="admin-card-header"><div className="admin-card-title">FAQs</div></div>
          <div className="admin-card-body">
            {pkg.faqs?.length ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {pkg.faqs.map((f) => (
                  <div key={f.id}>
                    <div style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--text-primary)' }}>{f.question}</div>
                    <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 2 }}>{f.answer}</div>
                  </div>
                ))}
              </div>
            ) : (
              <p style={{ color: 'var(--text-tertiary)', fontSize: 13, textAlign: 'center', padding: '16px 0' }}>No FAQs added.</p>
            )}
          </div>
        </div>

        <div className="admin-card" style={{ gridColumn: '1 / -1' }}>
          <div className="admin-card-header">
            <div className="admin-card-title">Items</div>
            {!showAddItem && (
              <button className="btn btn-secondary btn-sm" onClick={() => setShowAddItem(true)}>+ Add Item</button>
            )}
          </div>
          <div className="admin-card-body">
            {items.length > 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: showAddItem ? 20 : 0 }}>
                {items.map((item) => editingItemId === item.id ? (
                  <div key={item.id} className="admin-card" style={{ padding: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
                    <div className="form-row-2-1" style={{ gap: 10 }}>
                      <input className="admin-input" value={editItemForm.name} onChange={(e) => setEF('name', e.target.value)} placeholder="Item name" />
                      <input className="admin-input" type="number" min="0" value={editItemForm.base_price} onChange={(e) => setEF('base_price', e.target.value)} placeholder="Price (₹)" />
                    </div>
                    <div className="form-row-3" style={{ gap: 10 }}>
                      <input className="admin-input" type="number" min="1" value={editItemForm.quantity} onChange={(e) => setEF('quantity', e.target.value)} placeholder="Qty" />
                      <input className="admin-input" value={editItemForm.unit} onChange={(e) => setEF('unit', e.target.value)} placeholder="Unit (hrs, pcs…)" />
                      <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, cursor: 'pointer' }}>
                        <input type="checkbox" checked={editItemForm.is_mandatory} onChange={(e) => setEF('is_mandatory', e.target.checked)} />
                        Mandatory
                      </label>
                    </div>
                    <input className="admin-input" value={editItemForm.description} onChange={(e) => setEF('description', e.target.value)} placeholder="Description (optional)" />
                    <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                      <button className="btn btn-secondary btn-sm" onClick={() => setEditingItemId(null)}>Cancel</button>
                      <button className="btn btn-primary btn-sm" onClick={() => handleUpdateItem(item.id)} disabled={updateItemMutation.isPending}>Save</button>
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
                      {formatCurrency(item.base_price ?? 0)}
                    </div>
                    <div style={{ display: 'flex', gap: 6 }}>
                      <button className="btn btn-secondary btn-sm" onClick={() => startEditItem(item)}>Edit</button>
                      <button className="btn btn-sm" style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', color: '#ef4444' }} onClick={() => setConfirmDeleteItem(item)}>✕</button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {!items.length && !showAddItem && (
              <p style={{ color: 'var(--text-tertiary)', fontSize: 13, textAlign: 'center', padding: '16px 0' }}>No items added yet.</p>
            )}

            {showAddItem && (
              <div>
                <h4 style={{ margin: '0 0 12px', fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>Add New Item</h4>
                <form onSubmit={handleAddItem} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
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
                  <input className="admin-input" value={newItem.description} onChange={(e) => setNF('description', e.target.value)} placeholder="Description (optional)" />
                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
                    <button type="button" className="btn btn-secondary" onClick={() => { setShowAddItem(false); setNewItem(EMPTY_ITEM); }}>Cancel</button>
                    <button type="submit" className="btn btn-primary" disabled={addItemMutation.isPending}>
                      {addItemMutation.isPending ? 'Adding…' : '+ Add Item'}
                    </button>
                  </div>
                </form>
              </div>
            )}
          </div>
        </div>
      </div>

      <ConfirmDialog
        open={!!confirmDeleteItem}
        onClose={() => setConfirmDeleteItem(null)}
        onConfirm={() => deleteItemMutation.mutate(confirmDeleteItem.id)}
        title="Remove Item"
        message={`Remove "${confirmDeleteItem?.name}" from this package?`}
        loading={deleteItemMutation.isPending}
      />
    </div>
  );
}
