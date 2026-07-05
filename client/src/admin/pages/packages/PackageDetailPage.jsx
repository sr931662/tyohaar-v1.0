import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { packagesApi } from '../../api';
import { formatDate, formatCurrency, initials } from '../../utils/format';
import StatusBadge from '../../components/ui/StatusBadge';
import { SkeletonCard } from '../../components/ui/Skeleton';

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

      <div className="admin-metric-grid" style={{ marginBottom: 20 }}>
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

      <div className="grid-2">
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

        <div className="admin-card" style={{ gridColumn: '1 / -1' }}>
          <div className="admin-card-header"><div className="admin-card-title">Items</div></div>
          <div className="admin-table-wrapper">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Quantity</th>
                  <th>Unit</th>
                  <th>Price</th>
                  <th>Mandatory</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id}>
                    <td>{item.name}</td>
                    <td>{item.quantity}</td>
                    <td>{item.unit ?? '—'}</td>
                    <td>{formatCurrency(item.base_price ?? 0)}</td>
                    <td>{item.is_mandatory ? 'Yes' : 'No'}</td>
                  </tr>
                ))}
                {!items.length && (
                  <tr><td colSpan={5} className="admin-table-empty">No items added yet</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
