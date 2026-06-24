import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { vendorProfileApi, vendorPackagesApi } from '../../api';
import { useVendorAuth } from '../../context/VendorAuthContext';

const STATUS_COLOR = {
  active: 'var(--color-success, #22c55e)',
  pending: 'var(--color-warning, #f59e0b)',
  inactive: 'var(--text-tertiary)',
  suspended: 'var(--color-error, #ef4444)',
  under_review: 'var(--color-info, #3b82f6)',
};

const VERIFY_COLOR = {
  verified: 'var(--color-success, #22c55e)',
  unverified: 'var(--color-warning, #f59e0b)',
  under_review: 'var(--color-info, #3b82f6)',
  rejected: 'var(--color-error, #ef4444)',
};

function StatusPill({ label, color }) {
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 5,
      padding: '3px 10px', borderRadius: 99,
      background: `${color}18`, border: `1px solid ${color}40`,
      fontSize: 12, fontWeight: 600, color,
    }}>
      <span style={{ width: 6, height: 6, borderRadius: '50%', background: color, flexShrink: 0 }} />
      {label}
    </span>
  );
}

function StatCard({ icon, label, value, sub, accent }) {
  return (
    <div className="admin-card" style={{ padding: '20px 22px', display: 'flex', gap: 16, alignItems: 'flex-start' }}>
      {icon && (
        <div style={{
          width: 42, height: 42, borderRadius: 12, flexShrink: 0,
          background: `${accent}18`, display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 20,
        }}>
          {icon}
        </div>
      )}
      <div>
        <div style={{ fontSize: 26, fontWeight: 700, color: accent ?? 'var(--text-primary)', lineHeight: 1.1 }}>{value ?? '—'}</div>
        <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-secondary)', marginTop: 3 }}>{label}</div>
        {sub && <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginTop: 2 }}>{sub}</div>}
      </div>
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
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 24 }}>
          {[0, 1, 2, 3].map((i) => <div key={i} className="skeleton skeleton-card" style={{ height: 96 }} />)}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16 }}>
          <div className="skeleton skeleton-card" style={{ height: 160 }} />
          <div className="skeleton skeleton-card" style={{ height: 160 }} />
        </div>
      </div>
    );
  }

  if (!vendor) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: 400, textAlign: 'center', padding: 48 }}>
        <div style={{ fontSize: 56, marginBottom: 16 }}>👋</div>
        <h2 style={{ margin: '0 0 8px', fontSize: 24, fontWeight: 700, color: 'var(--text-primary)' }}>
          Welcome, {user?.full_name?.split(' ')[0] ?? 'Vendor'}!
        </h2>
        <p style={{ color: 'var(--text-secondary)', marginBottom: 28, maxWidth: 360, lineHeight: 1.6 }}>
          Start by creating your business profile to list packages on Tyohaar.
        </p>
        <button className="btn btn-primary" style={{ padding: '10px 28px', fontSize: 14 }} onClick={() => navigate('/vendor/profile')}>
          Create My Profile →
        </button>
      </div>
    );
  }

  const pkgItems = packages?.items ?? [];
  const pending = pkgItems.filter((p) => p.status === 'pending_review').length;
  const active  = pkgItems.filter((p) => p.status === 'active').length;
  const draft   = pkgItems.filter((p) => p.status === 'draft').length;
  const rating  = vendor.average_rating ? Number(vendor.average_rating).toFixed(1) : null;

  return (
    <div>
      {/* Header */}
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <h1>Overview</h1>
          <p style={{ color: 'var(--text-secondary)' }}>Welcome back, <strong>{vendor.business_name}</strong></p>
        </div>
        <div className="admin-page-header-actions" style={{ gap: 8 }}>
          <StatusPill
            label={vendor.status?.replace(/_/g, ' ')}
            color={STATUS_COLOR[vendor.status] ?? 'var(--text-tertiary)'}
          />
          {vendor.verification_status && (
            <StatusPill
              label={vendor.verification_status?.replace(/_/g, ' ')}
              color={VERIFY_COLOR[vendor.verification_status] ?? 'var(--text-tertiary)'}
            />
          )}
        </div>
      </div>

      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 24 }}>
        <StatCard
          icon="⭐"
          label="Average Rating"
          value={rating ?? 'New'}
          sub={`${vendor.review_count ?? 0} review${vendor.review_count !== 1 ? 's' : ''}`}
          accent="#f59e0b"
        />
        <StatCard
          icon="✅"
          label="Active Packages"
          value={active}
          sub="Visible on app"
          accent="#22c55e"
        />
        <StatCard
          icon="🕐"
          label="Pending Review"
          value={pending}
          sub="Waiting for admin"
          accent="#f59e0b"
        />
        <StatCard
          icon="📝"
          label="Draft Packages"
          value={draft}
          sub="Not submitted yet"
          accent="var(--text-tertiary)"
        />
      </div>

      {/* Cards row */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 20 }}>
        {/* Quick actions */}
        <div className="admin-card" style={{ padding: 24 }}>
          <h3 style={{ margin: '0 0 16px', fontSize: 15, fontWeight: 600, color: 'var(--text-primary)' }}>Quick Actions</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <button
              className="btn btn-primary"
              style={{ justifyContent: 'center', padding: '11px 20px' }}
              onClick={() => navigate('/vendor/packages')}
            >
              + Add New Package
            </button>
            <button
              className="btn btn-secondary"
              style={{ justifyContent: 'center', padding: '11px 20px' }}
              onClick={() => navigate('/vendor/profile')}
            >
              Edit Profile
            </button>
          </div>
          {pending > 0 && (
            <div style={{
              marginTop: 16, padding: '10px 14px', borderRadius: 10,
              background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.2)',
              fontSize: 13, color: 'var(--color-warning, #f59e0b)',
            }}>
              🕐 {pending} package{pending > 1 ? 's are' : ' is'} waiting for admin approval.
            </div>
          )}
        </div>

        {/* Business info */}
        <div className="admin-card" style={{ padding: 24 }}>
          <h3 style={{ margin: '0 0 14px', fontSize: 15, fontWeight: 600, color: 'var(--text-primary)' }}>Business Info</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {[
              { label: 'Type', value: vendor.vendor_type?.replace(/_/g, ' ') },
              { label: 'Experience', value: vendor.years_of_experience ? `${vendor.years_of_experience} years` : null },
              { label: 'Service radius', value: vendor.service_radius_km ? `${vendor.service_radius_km} km` : null },
              { label: 'Acceptance rate', value: `${vendor.acceptance_rate_pct ?? 100}%` },
              { label: 'Completed', value: `${vendor.completion_count ?? 0} bookings` },
            ].filter((r) => r.value).map((row) => (
              <div key={row.label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 13 }}>
                <span style={{ color: 'var(--text-tertiary)' }}>{row.label}</span>
                <span style={{ color: 'var(--text-secondary)', fontWeight: 500, textTransform: 'capitalize' }}>{row.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
