import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { vendorProfileApi, vendorPackagesApi } from '../../api';
import { useVendorAuth } from '../../context/VendorAuthContext';

function StatCard({ label, value, sub, color = 'var(--text-primary)' }) {
  return (
    <div className="admin-card" style={{ padding: 20 }}>
      <div style={{ fontSize: 26, fontWeight: 700, color }}>{value ?? '—'}</div>
      <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-secondary)', marginTop: 2 }}>{label}</div>
      {sub && <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginTop: 4 }}>{sub}</div>}
    </div>
  );
}

export default function VendorOverviewPage() {
  const { user } = useVendorAuth();
  const navigate = useNavigate();

  const { data: vendor, isLoading: vendorLoading } = useQuery({
    queryKey: ['vendor', 'me'],
    queryFn: () => vendorProfileApi.getMe(),
    retry: (count, err) => err?.response?.status !== 404 && count < 2,
  });

  const { data: packages } = useQuery({
    queryKey: ['vendor-packages'],
    queryFn: () => vendorPackagesApi.list({ per_page: 100 }),
    enabled: !!vendor,
  });

  if (vendorLoading) {
    return (
      <div style={{ padding: 32 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 24 }}>
          {[0, 1, 2].map((i) => <div key={i} className="skeleton skeleton-card" style={{ height: 90 }} />)}
        </div>
      </div>
    );
  }

  if (!vendor) {
    return (
      <div style={{ padding: 48, textAlign: 'center' }}>
        <div style={{ fontSize: 40, marginBottom: 16 }}>👋</div>
        <h2 style={{ margin: '0 0 8px', fontSize: 22, fontWeight: 700 }}>Welcome, {user?.full_name ?? 'Vendor'}!</h2>
        <p style={{ color: 'var(--text-secondary)', marginBottom: 24 }}>Start by creating your vendor profile to list packages on Tyohaar.</p>
        <button className="btn btn-primary" onClick={() => navigate('/vendor/profile')}>
          Create My Profile →
        </button>
      </div>
    );
  }

  const pkgItems = packages?.items ?? [];
  const pending = pkgItems.filter((p) => p.status === 'pending_review').length;
  const active = pkgItems.filter((p) => p.status === 'active').length;
  const draft = pkgItems.filter((p) => p.status === 'draft').length;

  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <h1>Overview</h1>
          <p>Welcome back, {vendor.business_name}</p>
        </div>
        <div className="admin-page-header-actions">
          <span className={`badge badge-${vendor.status === 'active' ? 'success' : vendor.status === 'pending' ? 'warning' : 'neutral'}`}>
            <span className="badge-dot" />
            {vendor.status?.replace(/_/g, ' ')}
          </span>
          {vendor.verification_status && (
            <span className={`badge badge-${vendor.verification_status === 'verified' ? 'success' : 'warning'}`}>
              <span className="badge-dot" />
              {vendor.verification_status?.replace(/_/g, ' ')}
            </span>
          )}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 24 }}>
        <StatCard label="Average Rating" value={vendor.average_rating ? Number(vendor.average_rating).toFixed(1) : '—'} sub={`${vendor.review_count ?? 0} reviews`} color="var(--color-warning)" />
        <StatCard label="Active Packages" value={active} color="var(--color-success)" />
        <StatCard label="Pending Review" value={pending} sub="Waiting for admin approval" color="var(--color-warning)" />
        <StatCard label="Draft Packages" value={draft} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 20 }}>
        <div className="admin-card" style={{ padding: 20 }}>
          <h3 style={{ margin: '0 0 16px', fontSize: 15, fontWeight: 600 }}>Quick Actions</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <button className="btn btn-primary" onClick={() => navigate('/vendor/packages')}>
              + Add New Package
            </button>
            <button className="btn btn-secondary" onClick={() => navigate('/vendor/profile')}>
              Edit Profile
            </button>
          </div>
        </div>

        <div className="admin-card" style={{ padding: 20 }}>
          <h3 style={{ margin: '0 0 12px', fontSize: 15, fontWeight: 600 }}>Business Info</h3>
          <div style={{ fontSize: 13, color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: 6 }}>
            <div><span style={{ color: 'var(--text-tertiary)' }}>Type: </span>{vendor.vendor_type?.replace(/_/g, ' ')}</div>
            {vendor.years_of_experience && <div><span style={{ color: 'var(--text-tertiary)' }}>Experience: </span>{vendor.years_of_experience} years</div>}
            {vendor.service_radius_km && <div><span style={{ color: 'var(--text-tertiary)' }}>Service radius: </span>{vendor.service_radius_km} km</div>}
            <div><span style={{ color: 'var(--text-tertiary)' }}>Completion rate: </span>{vendor.acceptance_rate_pct ?? 100}%</div>
          </div>
        </div>
      </div>
    </div>
  );
}
