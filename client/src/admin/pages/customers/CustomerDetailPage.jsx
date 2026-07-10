import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { customersApi } from '../../api';
import { formatDate, formatCurrency, initials, timeAgo } from '../../utils/format';
import StatusBadge from '../../components/ui/StatusBadge';
import { SkeletonCard } from '../../components/ui/Skeleton';

export default function CustomerDetailPage() {
  const { userId } = useParams();
  const navigate = useNavigate();

  const { data: crm, isLoading } = useQuery({
    queryKey: ['customer', 'crm', userId],
    queryFn: () => customersApi.crmProfile(userId),
  });

  if (isLoading) return (
    <div>
      <div className="admin-page-header"><button className="btn btn-ghost" onClick={() => navigate(-1)}>← Back</button></div>
      {[1, 2].map(i => <SkeletonCard key={i} height={200} />)}
    </div>
  );

  if (!crm) return <div className="admin-empty"><div className="admin-empty-title">Customer not found</div></div>;

  // CRM customer profile: { summary, financials, active_membership, recent_bookings, addresses, open_support_tickets, ... }
  const s = crm.summary ?? {};
  const fin = crm.financials ?? {};
  const recentBookings = crm.recent_bookings ?? [];
  const addresses = crm.addresses ?? [];
  const activeMembership = crm.active_membership;

  return (
    <div>
      <div className="admin-page-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button className="btn btn-ghost" onClick={() => navigate(-1)}>←</button>
          <div className="admin-avatar lg">{initials(s.full_name ?? 'U')}</div>
          <div>
            <h1 style={{ marginBottom: 2 }}>{s.full_name ?? 'Unknown'}</h1>
            <span className="text-secondary">{s.email}</span>
          </div>
        </div>
      </div>

      {/* Metric row */}
      <div className="admin-metric-grid" style={{ marginBottom: 20 }}>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Total Bookings</div>
          <div className="admin-metric-value">{fin.total_bookings ?? 0}</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Total Spent</div>
          <div className="admin-metric-value">{formatCurrency(fin.total_spent_lifetime ?? 0)}</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Avg Booking Value</div>
          <div className="admin-metric-value">{formatCurrency(fin.avg_booking_value ?? 0)}</div>
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
            <div className="admin-detail-row"><div className="admin-detail-label">Full Name</div><div className="admin-detail-value">{s.full_name ?? '—'}</div></div>
            <div className="admin-detail-row"><div className="admin-detail-label">Email</div><div className="admin-detail-value">{s.email ?? '—'}</div></div>
            <div className="admin-detail-row"><div className="admin-detail-label">Phone</div><div className="admin-detail-value">{s.phone ?? '—'}</div></div>
            <div className="admin-detail-row"><div className="admin-detail-label">Account Status</div><div className="admin-detail-value"><StatusBadge status={s.account_status?.toLowerCase()} /></div></div>
            <div className="admin-detail-row"><div className="admin-detail-label">Member Since</div><div className="admin-detail-value">{formatDate(s.registered_at)}</div></div>
            <div className="admin-detail-row"><div className="admin-detail-label">Last Login</div><div className="admin-detail-value">{s.last_login_at ? timeAgo(s.last_login_at) : '—'}</div></div>
            <div className="admin-detail-row"><div className="admin-detail-label">Open Tickets</div><div className="admin-detail-value">{crm.open_support_tickets ?? 0}</div></div>
          </div>
        </div>

        {/* Financial summary */}
        <div className="admin-card">
          <div className="admin-card-header"><div className="admin-card-title">Financials</div></div>
          <div className="admin-card-body">
            <div className="admin-detail-row"><div className="admin-detail-label">Lifetime Spent</div><div className="admin-detail-value">{formatCurrency(fin.total_spent_lifetime ?? 0)}</div></div>
            <div className="admin-detail-row"><div className="admin-detail-label">This Month</div><div className="admin-detail-value">{formatCurrency(fin.spent_this_month ?? 0)}</div></div>
            <div className="admin-detail-row"><div className="admin-detail-label">Avg Booking</div><div className="admin-detail-value">{formatCurrency(fin.avg_booking_value ?? 0)}</div></div>
            <div className="admin-detail-row"><div className="admin-detail-label">Completed</div><div className="admin-detail-value">{fin.completed_bookings ?? 0}</div></div>
            <div className="admin-detail-row"><div className="admin-detail-label">Cancelled</div><div className="admin-detail-value">{fin.cancelled_bookings ?? 0}</div></div>
            <div className="admin-detail-row"><div className="admin-detail-label">Reward Points</div><div className="admin-detail-value">{fin.reward_points ?? 0}</div></div>
            <div className="admin-detail-row"><div className="admin-detail-label">Total Refunds</div><div className="admin-detail-value">{formatCurrency(fin.total_refunds_received ?? 0)}</div></div>
          </div>
        </div>

        {/* Recent Bookings */}
        <div className="admin-card">
          <div className="admin-card-header"><div className="admin-card-title">Recent Bookings</div></div>
          <div className="admin-card-body" style={{ padding: '8px 20px' }}>
            {recentBookings.slice(0, 5).map((b) => (
              <div key={b.id} className="admin-data-list-item" style={{ cursor: 'pointer' }} onClick={() => navigate(`/admin/bookings/${b.id}`)}>
                <div>
                  <div style={{ fontSize: 13.5, fontWeight: 500 }}>{b.package_name ?? `Booking #${b.id?.slice(0, 8)}`}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{formatDate(b.date ?? b.created_at)}</div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
                  <StatusBadge status={b.status?.toLowerCase()} />
                  <span style={{ fontSize: 12 }}>{formatCurrency(b.amount ?? b.total_amount)}</span>
                </div>
              </div>
            ))}
            {!recentBookings.length && (
              <div style={{ padding: '16px 0', color: 'var(--text-secondary)', textAlign: 'center' }}>No bookings yet</div>
            )}
          </div>
        </div>

        {/* Addresses */}
        {addresses.length > 0 && (
          <div className="admin-card">
            <div className="admin-card-header"><div className="admin-card-title">Addresses</div></div>
            <div className="admin-card-body" style={{ padding: '8px 20px' }}>
              {addresses.map((a) => (
                <div key={a.id} className="admin-data-list-item">
                  <div>
                    <div style={{ fontSize: 13.5, fontWeight: 500 }}>{a.label ?? 'Address'}</div>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{a.city}</div>
                  </div>
                  {a.is_default && <span style={{ fontSize: 11, color: 'var(--brand-600)', fontWeight: 600 }}>Default</span>}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
