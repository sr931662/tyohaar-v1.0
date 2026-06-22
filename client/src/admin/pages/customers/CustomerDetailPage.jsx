import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { customersApi } from '../../api';
import { formatDate, formatCurrency, initials, timeAgo } from '../../utils/format';
import StatusBadge from '../../components/ui/StatusBadge';
import { SkeletonCard } from '../../components/ui/Skeleton';

export default function CustomerDetailPage() {
  const { userId } = useParams();
  const navigate = useNavigate();

  const { data: profile, isLoading } = useQuery({
    queryKey: ['customer', 'crm', userId],
    queryFn: () => customersApi.crmProfile(userId),
  });

  if (isLoading) return (
    <div>
      <div className="admin-page-header"><button className="btn btn-ghost" onClick={() => navigate(-1)}>← Back</button></div>
      {[1,2].map(i => <SkeletonCard key={i} height={200} />)}
    </div>
  );

  const c = profile?.user ?? profile;
  const analytics = profile?.analytics ?? {};
  const recentBookings = profile?.recent_bookings ?? [];
  const wallet = profile?.wallet;
  const activeMembership = profile?.active_membership;

  return (
    <div>
      <div className="admin-page-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button className="btn btn-ghost" onClick={() => navigate(-1)}>←</button>
          <div className="admin-avatar lg">{initials(c?.full_name ?? c?.name ?? 'U')}</div>
          <div>
            <h1 style={{ marginBottom: 2 }}>{c?.full_name ?? c?.name ?? 'Unknown'}</h1>
            <span className="text-secondary">{c?.email}</span>
          </div>
        </div>
      </div>

      {/* Metric row */}
      <div className="admin-metric-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)', marginBottom: 20 }}>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Total Bookings</div>
          <div className="admin-metric-value">{analytics.total_bookings ?? 0}</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Total Spent</div>
          <div className="admin-metric-value">{formatCurrency(analytics.total_spent ?? 0)}</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Wallet Balance</div>
          <div className="admin-metric-value">{formatCurrency(wallet?.balance ?? 0)}</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Membership</div>
          <div className="admin-metric-value" style={{ fontSize: 16 }}>{activeMembership?.plan_name ?? 'None'}</div>
        </div>
      </div>

      <div className="grid-2">
        {/* Profile */}
        <div className="admin-card">
          <div className="admin-card-header"><div className="admin-card-title">Profile</div></div>
          <div className="admin-card-body">
            <div className="admin-detail-row"><div className="admin-detail-label">Full Name</div><div className="admin-detail-value">{c?.full_name ?? c?.name}</div></div>
            <div className="admin-detail-row"><div className="admin-detail-label">Email</div><div className="admin-detail-value">{c?.email}</div></div>
            <div className="admin-detail-row"><div className="admin-detail-label">Phone</div><div className="admin-detail-value">{c?.phone_number ?? '—'}</div></div>
            <div className="admin-detail-row"><div className="admin-detail-label">Member Since</div><div className="admin-detail-value">{formatDate(c?.created_at)}</div></div>
            <div className="admin-detail-row"><div className="admin-detail-label">Last Active</div><div className="admin-detail-value">{timeAgo(c?.last_active_at ?? c?.updated_at)}</div></div>
            <div className="admin-detail-row"><div className="admin-detail-label">Account Status</div><div className="admin-detail-value"><StatusBadge status={c?.is_active ? 'active' : 'inactive'} /></div></div>
          </div>
        </div>

        {/* Recent Bookings */}
        <div className="admin-card">
          <div className="admin-card-header"><div className="admin-card-title">Recent Bookings</div></div>
          <div className="admin-card-body" style={{ padding: '8px 20px' }}>
            {recentBookings.slice(0, 5).map((b) => (
              <div key={b.id} className="admin-data-list-item" style={{ cursor: 'pointer' }} onClick={() => navigate(`/admin/bookings/${b.id}`)}>
                <div>
                  <div style={{ fontSize: 13.5, fontWeight: 500 }}>{b.package_name ?? 'Booking'}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{formatDate(b.event_date ?? b.created_at)}</div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
                  <StatusBadge status={b.status} />
                  <span style={{ fontSize: 12 }}>{formatCurrency(b.total_amount)}</span>
                </div>
              </div>
            ))}
            {!recentBookings.length && <div style={{ padding: '16px 0', color: 'var(--text-secondary)', textAlign: 'center' }}>No bookings yet</div>}
          </div>
        </div>
      </div>
    </div>
  );
}
