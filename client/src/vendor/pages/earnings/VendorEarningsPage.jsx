import { useQuery } from '@tanstack/react-query';
import { vendorEarningsApi } from '../../api';
import { formatCurrency, formatDateTime } from '../../../admin/utils/format';
import { SkeletonMetrics } from '../../../admin/components/ui/Skeleton';
import EmptyState from '../../../admin/components/ui/EmptyState';

const STATUS_COLOR = {
  completed: '#22c55e',
  pending: '#f59e0b',
  initiated: '#f59e0b',
  processing: '#3b82f6',
  failed: '#ef4444',
  refunded: '#ef4444',
  partially_refunded: '#ef4444',
  cancelled: 'var(--text-tertiary)',
  expired: 'var(--text-tertiary)',
  disputed: '#ef4444',
};

const STATUS_LABEL = {
  completed: 'Completed',
  pending: 'Pending',
  initiated: 'Initiated',
  processing: 'Processing',
  failed: 'Failed',
  refunded: 'Refunded',
  partially_refunded: 'Partially Refunded',
  cancelled: 'Cancelled',
  expired: 'Expired',
  disputed: 'Disputed',
};

function MetricCard({ label, value, sub, color }) {
  return (
    <div className="admin-metric-card">
      <div className="admin-metric-label">{label}</div>
      <div className="admin-metric-value" style={color ? { color } : {}}>{value}</div>
      {sub && <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

export default function VendorEarningsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['vendor-earnings'],
    queryFn: () => vendorEarningsApi.get(),
    retry: 1,
  });

  const payments = data?.payments ?? [];

  if (error) {
    return (
      <div>
        <div className="admin-page-header">
          <div className="admin-page-header-left">
            <h1>Earnings</h1>
          </div>
        </div>
        <div style={{ padding: 48, textAlign: 'center' }}>
          <div style={{ fontSize: 40, marginBottom: 12 }}>💰</div>
          <p style={{ color: 'var(--text-secondary)' }}>Could not load earnings right now.</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <h1>Earnings</h1>
          <p style={{ color: 'var(--text-secondary)' }}>Payments collected on your bookings via Razorpay</p>
        </div>
      </div>

      {isLoading ? (
        <SkeletonMetrics count={3} />
      ) : (
        <div className="admin-metric-grid" style={{ marginBottom: 24 }}>
          <MetricCard
            label="Total Collected"
            value={formatCurrency(data?.total_collected ?? 0)}
            color="#22c55e"
          />
          <MetricCard
            label="Pending"
            value={formatCurrency(data?.pending_amount ?? 0)}
            sub="Payments not yet captured"
          />
          <MetricCard
            label="Bookings Paid"
            value={data?.total_bookings_paid ?? 0}
          />
        </div>
      )}

      <div className="admin-card">
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)', fontWeight: 600, fontSize: 15 }}>
          Payment History
        </div>

        {isLoading ? (
          <div style={{ padding: 24 }}>
            {[0, 1, 2, 3, 4].map((i) => (
              <div key={i} className="skeleton skeleton-card" style={{ height: 52, marginBottom: 8 }} />
            ))}
          </div>
        ) : !payments.length ? (
          <EmptyState
            title="No payments yet"
            description="Payments made on your bookings will appear here."
            icon="💳"
          />
        ) : (
          <div style={{ padding: '0 8px' }}>
            {payments.map((p) => {
              const status = p.payment_status?.toLowerCase();
              const color = STATUS_COLOR[status] ?? 'var(--text-tertiary)';
              return (
                <div
                  key={p.id}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 14,
                    padding: '14px 12px',
                    borderBottom: '1px solid var(--border-subtle)',
                  }}
                >
                  <div style={{
                    width: 36, height: 36, borderRadius: '50%', flexShrink: 0,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    background: `${color}15`, color, fontWeight: 700, fontSize: 14,
                  }}>
                    ₹
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 13.5, fontWeight: 500, color: 'var(--text-primary)' }}>
                      {p.payment_number}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginTop: 1 }}>
                      {p.payment_method && <span style={{ marginRight: 8, textTransform: 'capitalize' }}>{p.payment_method}</span>}
                      {formatDateTime(p.captured_at ?? p.created_at)}
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)' }}>
                      {formatCurrency(p.amount ?? 0)}
                    </div>
                    <div style={{
                      display: 'inline-flex', alignItems: 'center', gap: 4,
                      fontSize: 11, fontWeight: 600, color, marginTop: 2,
                    }}>
                      <span style={{ width: 5, height: 5, borderRadius: '50%', background: color }} />
                      {STATUS_LABEL[status] ?? p.payment_status}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
