import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { bookingsApi } from '../../api';
import { formatDate, formatDateTime, formatCurrency } from '../../utils/format';
import StatusBadge from '../../components/ui/StatusBadge';
import Modal, { ConfirmDialog } from '../../components/ui/Modal';
import { SkeletonCard } from '../../components/ui/Skeleton';

export default function BookingDetailPage() {
  const { bookingId } = useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState('overview');
  const [cancelOpen, setCancelOpen] = useState(false);

  const { data: booking, isLoading } = useQuery({
    queryKey: ['booking', bookingId],
    queryFn: () => bookingsApi.get(bookingId),
  });

  const { data: history } = useQuery({
    queryKey: ['booking', bookingId, 'history'],
    queryFn: () => bookingsApi.history(bookingId),
    enabled: activeTab === 'history',
  });

  const { data: statusHistory } = useQuery({
    queryKey: ['booking', bookingId, 'status-history'],
    queryFn: () => bookingsApi.statusHistory(bookingId),
    enabled: activeTab === 'history',
  });

  const confirmMutation = useMutation({
    mutationFn: () => bookingsApi.confirm(bookingId),
    onSuccess: () => { toast.success('Booking confirmed'); qc.invalidateQueries(['booking', bookingId]); },
    onError: () => toast.error('Failed to confirm booking'),
  });

  const cancelMutation = useMutation({
    mutationFn: () => bookingsApi.processCancellation(bookingId, false),
    onSuccess: () => { toast.success('Booking cancelled'); qc.invalidateQueries(['booking', bookingId]); setCancelOpen(false); },
    onError: () => toast.error('Failed to cancel booking'),
  });

  const generateInvoiceMutation = useMutation({
    mutationFn: () => bookingsApi.generateInvoice(bookingId),
    onSuccess: () => { toast.success('Invoice generated'); },
    onError: () => toast.error('Failed to generate invoice'),
  });

  if (isLoading) return (
    <div>
      <div className="admin-page-header"><button className="btn btn-ghost" onClick={() => navigate(-1)}>← Back</button></div>
      {[1,2,3].map(i => <SkeletonCard key={i} height={120} />)}
    </div>
  );

  if (!booking) return <div className="admin-empty"><div className="admin-empty-title">Booking not found</div></div>;

  const b = booking;

  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <button className="btn btn-ghost" onClick={() => navigate(-1)}>←</button>
            <div>
              <h1>Booking <code style={{ fontSize: 14, background: 'var(--bg-base)', padding: '2px 8px', borderRadius: 4 }}>{b.booking_number ?? b.id?.slice(0, 8)}</code></h1>
              {/* booking_status is the correct field name from BookingResponse */}
              <StatusBadge status={b.booking_status} />
            </div>
          </div>
        </div>
        <div className="admin-page-header-actions">
          {b.booking_status === 'pending' && (
            <button className="btn btn-success" onClick={() => confirmMutation.mutate()} disabled={confirmMutation.isPending}>
              Confirm Booking
            </button>
          )}
          {['pending', 'confirmed'].includes(b.booking_status) && (
            <button className="btn btn-danger" onClick={() => setCancelOpen(true)}>Cancel</button>
          )}
          {b.booking_status === 'completed' && (
            <button className="btn btn-secondary" onClick={() => generateInvoiceMutation.mutate()}>Generate Invoice</button>
          )}
        </div>
      </div>

      {/* Metrics */}
      <div className="admin-metric-grid" style={{ marginBottom: 20 }}>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Total Amount</div>
          <div className="admin-metric-value">{formatCurrency(b.total_amount)}</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Paid Amount</div>
          {/* was: b.paid_amount — backend sends amount_paid */}
          <div className="admin-metric-value">{formatCurrency(b.amount_paid ?? 0)}</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Event Date</div>
          {/* was: b.event_date — backend sends scheduled_date */}
          <div className="admin-metric-value" style={{ fontSize: 16 }}>{formatDate(b.scheduled_date)}</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Created</div>
          <div className="admin-metric-value" style={{ fontSize: 16 }}>{formatDate(b.created_at)}</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="admin-tabs">
        {['overview', 'items', 'history'].map((t) => (
          <button key={t} className={`admin-tab${activeTab === t ? ' active' : ''}`} onClick={() => setActiveTab(t)}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {activeTab === 'overview' && (
        <div className="grid-2">
          <div className="admin-card">
            <div className="admin-card-header"><div className="admin-card-title">Customer</div></div>
            <div className="admin-card-body">
              {/* BookingDetailResponse.customer is admin/support-only — populated by get_booking */}
              <div className="admin-detail-row"><div className="admin-detail-label">Name</div><div className="admin-detail-value">{b.customer?.full_name ?? '—'}</div></div>
              <div className="admin-detail-row"><div className="admin-detail-label">Email</div><div className="admin-detail-value">{b.customer?.email ?? '—'}</div></div>
              <div className="admin-detail-row"><div className="admin-detail-label">Phone</div><div className="admin-detail-value">{b.customer?.phone ?? '—'}</div></div>
              <div className="admin-detail-row"><div className="admin-detail-label">Customer ID</div><div className="admin-detail-value"><code style={{ fontSize: 12 }}>{b.customer_id?.slice(0, 8) ?? '—'}</code></div></div>
            </div>
          </div>
          <div className="admin-card">
            <div className="admin-card-header"><div className="admin-card-title">Vendor</div></div>
            <div className="admin-card-body">
              {/* BookingDetailResponse.vendor is the package-owner vendor, admin/support-only */}
              <div className="admin-detail-row"><div className="admin-detail-label">Business Name</div><div className="admin-detail-value">{b.vendor?.business_name ?? 'Not assigned'}</div></div>
              <div className="admin-detail-row"><div className="admin-detail-label">Email</div><div className="admin-detail-value">{b.vendor?.email ?? '—'}</div></div>
              <div className="admin-detail-row"><div className="admin-detail-label">Phone</div><div className="admin-detail-value">{b.vendor?.phone ?? '—'}</div></div>
              <div className="admin-detail-row"><div className="admin-detail-label">Verification</div><div className="admin-detail-value">{b.vendor?.verification_status ? <StatusBadge status={b.vendor.verification_status} /> : '—'}</div></div>
            </div>
          </div>
          <div className="admin-card">
            <div className="admin-card-header"><div className="admin-card-title">Booking Details</div></div>
            <div className="admin-card-body">
              <div className="admin-detail-row"><div className="admin-detail-label">Celebration</div><div className="admin-detail-value">{b.celebration_title ?? <code style={{ fontSize: 12 }}>{b.celebration_id?.slice(0, 8) ?? '—'}</code>}</div></div>
              {/* was: b.event_date — backend sends scheduled_date */}
              <div className="admin-detail-row"><div className="admin-detail-label">Event Date</div><div className="admin-detail-value">{formatDateTime(b.scheduled_date)}</div></div>
              {/* Vendor-provided PST [Preparation Starting Time] — set via PATCH /bookings/{id}/pst, auto-synced here */}
              <div className="admin-detail-row"><div className="admin-detail-label">Preparation Start Time (PST)</div><div className="admin-detail-value">{b.preparation_start_time ?? '—'}</div></div>
              {/* guest_count is on CelebrationResponse, not BookingResponse */}
              <div className="admin-detail-row"><div className="admin-detail-label">Package ID</div><div className="admin-detail-value"><code style={{ fontSize: 12 }}>{b.package_id?.slice(0, 8) ?? '—'}</code></div></div>
              {b.theme_name && (
                <div className="admin-detail-row"><div className="admin-detail-label">Customization Theme</div><div className="admin-detail-value">{b.theme_name}</div></div>
              )}
              {/* was: b.special_notes — backend sends special_instructions */}
              <div className="admin-detail-row"><div className="admin-detail-label">Special Notes</div><div className="admin-detail-value">{b.special_instructions ?? '—'}</div></div>
            </div>
          </div>
          <div className="admin-card">
            <div className="admin-card-header"><div className="admin-card-title">Financials</div></div>
            <div className="admin-card-body">
              <div className="admin-detail-row"><div className="admin-detail-label">Subtotal</div><div className="admin-detail-value">{formatCurrency(b.subtotal ?? 0)}</div></div>
              <div className="admin-detail-row"><div className="admin-detail-label">Discount</div><div className="admin-detail-value">{b.discount_amount ? formatCurrency(b.discount_amount) : '—'}</div></div>
              <div className="admin-detail-row"><div className="admin-detail-label">Tax</div><div className="admin-detail-value">{formatCurrency(b.tax_amount ?? 0)}</div></div>
              <div className="admin-detail-row"><div className="admin-detail-label">Amount Due</div><div className="admin-detail-value">{formatCurrency(b.amount_due ?? 0)}</div></div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'items' && (
        <div className="admin-table-wrapper">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Item</th>
                <th>Quantity</th>
                <th>Unit Price</th>
                <th>Final Price</th>
              </tr>
            </thead>
            <tbody>
              {(b.items ?? []).map((item, i) => (
                <tr key={item.id ?? i}>
                  {/* BookingItemResponse.name is the item name snapshotted at booking time */}
                  <td>{item.name ?? `Item ${i + 1}`}</td>
                  <td>{item.quantity ?? 1}</td>
                  <td>{formatCurrency(item.unit_price)}</td>
                  {/* was: item.total_price — backend sends final_price */}
                  <td>{formatCurrency(item.final_price)}</td>
                </tr>
              ))}
              {!b.items?.length && <tr><td colSpan={4} className="admin-table-empty">No items</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'history' && (
        <div className="grid-2">
          <div className="admin-card">
            <div className="admin-card-header"><div className="admin-card-title">Status History</div></div>
            <div style={{ padding: '8px 20px 16px' }}>
              {(statusHistory ?? []).map((s, i) => (
                <div key={i} className="admin-activity-item">
                  <div className="admin-activity-icon">→</div>
                  <div className="admin-activity-content">
                    <div className="admin-activity-text">
                      <StatusBadge status={s.from_status} /> → <StatusBadge status={s.to_status} />
                    </div>
                    {/* changed_by_id is a UUID; show truncated since no name is embedded */}
                    <div className="admin-activity-time">{formatDateTime(s.changed_at)} by {s.changed_by_id ? s.changed_by_id.slice(0, 8) : 'System'}</div>
                  </div>
                </div>
              ))}
              {!statusHistory?.length && <div style={{ padding: '16px 0', color: 'var(--text-secondary)', textAlign: 'center' }}>No status history</div>}
            </div>
          </div>
          <div className="admin-card">
            <div className="admin-card-header"><div className="admin-card-title">Event Log</div></div>
            <div style={{ padding: '8px 20px 16px' }}>
              {(history ?? []).map((h, i) => (
                <div key={i} className="admin-activity-item">
                  <div className="admin-activity-icon">📌</div>
                  <div className="admin-activity-content">
                    <div className="admin-activity-text">{h.description ?? h.event ?? h.action}</div>
                    <div className="admin-activity-time">{formatDateTime(h.created_at)}</div>
                  </div>
                </div>
              ))}
              {!history?.length && <div style={{ padding: '16px 0', color: 'var(--text-secondary)', textAlign: 'center' }}>No events logged</div>}
            </div>
          </div>
        </div>
      )}

      <ConfirmDialog
        open={cancelOpen}
        onClose={() => setCancelOpen(false)}
        onConfirm={() => cancelMutation.mutate()}
        title="Cancel Booking"
        message="Are you sure you want to cancel this booking? This action may trigger a refund."
        danger
        loading={cancelMutation.isPending}
      />
    </div>
  );
}
