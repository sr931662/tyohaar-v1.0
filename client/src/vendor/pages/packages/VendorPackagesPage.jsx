import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { vendorProfileApi, vendorPackagesApi } from '../../api';
import { ConfirmDialog } from '../../../admin/components/ui/Modal';

const STATUS_COLORS = {
  draft: 'neutral',
  pending_review: 'warning',
  active: 'success',
  inactive: 'neutral',
  archived: 'neutral',
};

const STATUS_LABELS = {
  draft: 'Draft',
  pending_review: 'Pending Review',
  active: 'Active',
  inactive: 'Inactive',
  archived: 'Archived',
};

function StatusBadge({ status }) {
  const color = STATUS_COLORS[status] ?? 'info';
  return (
    <span className={`badge badge-${color}`}>
      <span className="badge-dot" />
      {STATUS_LABELS[status] ?? status}
    </span>
  );
}

// Modal for creating a new package
function CreatePackageModal({ vendorId, categories, onClose, onSuccess }) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [categoryId, setCategoryId] = useState('');
  const [basePrice, setBasePrice] = useState('');
  const [errors, setErrors] = useState({});

  const qc = useQueryClient();
  const mutation = useMutation({
    mutationFn: (body) => vendorPackagesApi.create(body),
    onSuccess: (data) => {
      toast.success('Package created! Add more details, then submit for review.');
      qc.invalidateQueries(['vendor-packages']);
      onSuccess?.(data);
      onClose();
    },
    onError: (err) => {
      const msg = err?.response?.data?.detail ?? 'Failed to create package.';
      toast.error(msg);
    },
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    const e2 = {};
    if (!name.trim()) e2.name = 'Package name is required.';
    if (!basePrice || isNaN(Number(basePrice))) e2.basePrice = 'Enter a valid price.';
    setErrors(e2);
    if (Object.keys(e2).length) return;

    mutation.mutate({
      name: name.trim(),
      description: description.trim() || undefined,
      category_id: categoryId || undefined,
      base_price: Number(basePrice),
      pricing_type: 'fixed',
    });
  };

  return (
    <div className="admin-modal-overlay" onClick={onClose}>
      <div className="admin-modal" style={{ maxWidth: 500 }} onClick={(e) => e.stopPropagation()}>
        <div className="admin-modal-header">
          <h2 className="admin-modal-title">New Package</h2>
          <button className="admin-modal-close" onClick={onClose}>×</button>
        </div>
        <form onSubmit={handleSubmit} style={{ padding: '0 24px 24px', display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div>
            <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 6 }}>Package Name *</label>
            <input className="admin-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Premium Wedding Decoration" />
            {errors.name && <p style={{ color: 'var(--color-error)', fontSize: 12, marginTop: 4 }}>{errors.name}</p>}
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 6 }}>Description</label>
            <textarea className="admin-input" rows={3} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="What's included in this package?" style={{ resize: 'vertical' }} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 6 }}>Category</label>
              <select className="admin-input" value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>
                <option value="">None</option>
                {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 6 }}>Base Price (₹) *</label>
              <input className="admin-input" type="number" min="0" value={basePrice} onChange={(e) => setBasePrice(e.target.value)} placeholder="e.g. 15000" />
              {errors.basePrice && <p style={{ color: 'var(--color-error)', fontSize: 12, marginTop: 4 }}>{errors.basePrice}</p>}
            </div>
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 8 }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={mutation.isPending}>
              {mutation.isPending ? 'Creating…' : 'Create Package'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function VendorPackagesPage() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [confirmSubmit, setConfirmSubmit] = useState(null); // { id, name }
  const [confirmUnpublish, setConfirmUnpublish] = useState(null);

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

  const submitMutation = useMutation({
    mutationFn: (packageId) => vendorPackagesApi.submitForReview(packageId),
    onSuccess: () => {
      toast.success('Package submitted for admin review.');
      qc.invalidateQueries(['vendor-packages']);
    },
    onError: (err) => {
      const msg = err?.response?.data?.detail ?? 'Failed to submit for review.';
      toast.error(msg);
    },
  });

  const unpublishMutation = useMutation({
    mutationFn: (packageId) => vendorPackagesApi.unpublish(packageId),
    onSuccess: () => {
      toast.success('Package unpublished.');
      qc.invalidateQueries(['vendor-packages']);
    },
    onError: () => toast.error('Failed to unpublish.'),
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
          <p>Create packages and submit them for admin approval to go live on the app.</p>
        </div>
        <div className="admin-page-header-actions">
          <button className="btn btn-primary" onClick={() => setShowCreate(true)}>+ New Package</button>
        </div>
      </div>

      {/* Workflow hint */}
      <div style={{ background: 'var(--color-info-bg, #eff6ff)', border: '1px solid var(--color-info-border, #bfdbfe)', borderRadius: 10, padding: '12px 16px', marginBottom: 20, fontSize: 13, color: 'var(--color-info, #1d4ed8)', display: 'flex', gap: 10, alignItems: 'flex-start' }}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginTop: 1, flexShrink: 0 }}>
          <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        <span><strong>How it works:</strong> Create a package (Draft) → Submit for Review → Admin approves → Package goes live on the app.</span>
      </div>

      {isLoading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {[0, 1, 2].map((i) => <div key={i} className="skeleton skeleton-card" style={{ height: 72 }} />)}
        </div>
      ) : !items.length ? (
        <div style={{ textAlign: 'center', padding: 48 }}>
          <div style={{ fontSize: 40, marginBottom: 12 }}>📦</div>
          <p style={{ color: 'var(--text-secondary)', marginBottom: 16 }}>No packages yet. Create your first one to get started.</p>
          <button className="btn btn-primary" onClick={() => setShowCreate(true)}>+ Create Package</button>
        </div>
      ) : (
        <div className="admin-table-wrapper">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Package</th>
                <th>Category</th>
                <th>Base Price</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((p) => (
                <tr key={p.id}>
                  <td>
                    <div className="admin-user-name">{p.name}</div>
                    {p.description && (
                      <div className="admin-user-email" style={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {p.description}
                      </div>
                    )}
                  </td>
                  <td style={{ color: 'var(--text-secondary)', fontSize: 13 }}>{p.category?.name ?? '—'}</td>
                  <td style={{ fontWeight: 500 }}>
                    ₹{Number(p.base_price ?? p.price ?? 0).toLocaleString('en-IN')}
                  </td>
                  <td><StatusBadge status={p.status} /></td>
                  <td>
                    <div style={{ display: 'flex', gap: 8 }}>
                      {p.status === 'draft' && (
                        <button
                          className="btn btn-primary btn-sm"
                          onClick={() => setConfirmSubmit({ id: p.id, name: p.name })}
                          disabled={submitMutation.isPending}
                        >
                          Submit for Review
                        </button>
                      )}
                      {p.status === 'pending_review' && (
                        <span style={{ fontSize: 12, color: 'var(--text-tertiary)', padding: '4px 0' }}>Under review…</span>
                      )}
                      {p.status === 'active' && (
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => setConfirmUnpublish({ id: p.id, name: p.name })}
                          disabled={unpublishMutation.isPending}
                        >
                          Unpublish
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && (
        <CreatePackageModal
          vendorId={vendor.id}
          categories={categories}
          onClose={() => setShowCreate(false)}
        />
      )}

      <ConfirmDialog
        open={!!confirmSubmit}
        onClose={() => setConfirmSubmit(null)}
        onConfirm={() => { submitMutation.mutate(confirmSubmit.id); setConfirmSubmit(null); }}
        title="Submit for Review"
        message={`Submit "${confirmSubmit?.name}" for admin review? Once submitted, it cannot be edited until approved or rejected.`}
        loading={submitMutation.isPending}
      />

      <ConfirmDialog
        open={!!confirmUnpublish}
        onClose={() => setConfirmUnpublish(null)}
        onConfirm={() => { unpublishMutation.mutate(confirmUnpublish.id); setConfirmUnpublish(null); }}
        title="Unpublish Package"
        message={`Unpublish "${confirmUnpublish?.name}"? It will be hidden from the app.`}
        loading={unpublishMutation.isPending}
      />
    </div>
  );
}
