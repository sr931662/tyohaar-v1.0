import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { vendorBookingsApi } from '../../api';
import StatusBadge from '../../../admin/components/ui/StatusBadge';
import { SkeletonCard } from '../../../admin/components/ui/Skeleton';
import Modal, { ConfirmDialog } from '../../../admin/components/ui/Modal';
import { formatDate, formatDateTime, formatCurrency } from '../../../admin/utils/format';

function Section({ title, children }) {
  return (
    <div className="admin-detail-section">
      <div className="admin-detail-section-title">{title}</div>
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

const TAB_LABELS = ['Overview', 'Items', 'History'];

// ISO datetime → "YYYY-MM-DDTHH:mm" in local time for <input type="datetime-local">.
function toLocalInput(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (isNaN(d)) return '';
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export default function VendorBookingDetailPage() {
  const { bookingId } = useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState('Overview');
  const [confirmStart, setConfirmStart] = useState(false);
  const [confirmComplete, setConfirmComplete] = useState(false);
  const [pstModalOpen, setPstModalOpen] = useState(false);
  const [pstValue, setPstValue] = useState('');

  const { data: booking, isLoading } = useQuery({
    queryKey: ['vendor-booking', bookingId],
    queryFn: () => vendorBookingsApi.get(bookingId),
  });

  const { data: history = [] } = useQuery({
    queryKey: ['vendor-booking', bookingId, 'history'],
    queryFn: () => vendorBookingsApi.history(bookingId),
    enabled: activeTab === 'History',
  });

  const { data: statusHistory = [] } = useQuery({
    queryKey: ['vendor-booking', bookingId, 'status-history'],
    queryFn: () => vendorBookingsApi.statusHistory(bookingId),
    enabled: activeTab === 'History',
  });

  const invalidate = () => qc.invalidateQueries(['vendor-booking', bookingId]);

  const startMutation = useMutation({
    mutationFn: () => vendorBookingsApi.start(bookingId),
    onSuccess: () => { toast.success('Service started'); invalidate(); setConfirmStart(false); },
    onError: (err) => toast.error(err?.response?.data?.error?.message ?? 'Failed to start service'),
  });

  const completeMutation = useMutation({
    mutationFn: () => vendorBookingsApi.complete(bookingId),
    onSuccess: () => { toast.success('Service marked as completed'); invalidate(); setConfirmComplete(false); },
    onError: (err) => toast.error(err?.response?.data?.error?.message ?? 'Failed to complete service'),
  });

  const setPstMutation = useMutation({
    // datetime-local yields "YYYY-MM-DDTHH:mm"; send full ISO datetime.
    mutationFn: () => vendorBookingsApi.setPst(bookingId, new Date(pstValue).toISOString()),
    onSuccess: () => { toast.success('Preparation start time saved'); invalidate(); setPstModalOpen(false); },
    onError: (err) => toast.error(err?.response?.data?.error?.message ?? 'Failed to save preparation time'),
  });

  if (isLoading) return (
    <div>
      <div className="admin-page-header">
        <button className="btn btn-ghost" onClick={() => navigate(-1)}>← Back</button>
      </div>
      {[1, 2, 3].map((i) => <SkeletonCard key={i} height={120} />)}
    </div>
  );

  if (!booking) return (
    <div style={{ padding: 48, textAlign: 'center' }}>
      <p style={{ color: 'var(--text-secondary)' }}>Booking not found.</p>
      <button className="btn btn-secondary" onClick={() => navigate(-1)} style={{ marginTop: 12 }}>Go Back</button>
    </div>
  );

  const b = booking;
  const items = b.items ?? [];

  return (
    <div>
      {/* Header */}
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <button className="btn btn-ghost" onClick={() => navigate(-1)}>←</button>
            <div>
              <h1>
                Booking{' '}
                <code style={{ fontSize: 14, background: 'var(--bg-base)', padding: '2px 8px', borderRadius: 4 }}>
                  {b.booking_number ?? b.id?.slice(0, 8)}
                </code>
              </h1>
              <div style={{ marginTop: 4 }}>
                <StatusBadge status={b.booking_status} />
              </div>
            </div>
          </div>
        </div>
        <div className="admin-page-header-actions">
          {b.booking_status === 'confirmed' && (
            <button
              className="btn btn-secondary"
              onClick={() => { setPstValue(toLocalInput(b.preparation_start_at)); setPstModalOpen(true); }}
            >
              {b.preparation_start_at ? 'Update Prep Time' : 'Set Prep Time'}
            </button>
          )}
          {b.booking_status === 'confirmed' && (
            <button
              className="btn btn-primary"
              onClick={() => setConfirmStart(true)}
              disabled={startMutation.isPending}
            >
              Start Service
            </button>
          )}
          {b.booking_status === 'in_progress' && (
            <button
              className="btn btn-success"
              onClick={() => setConfirmComplete(true)}
              disabled={completeMutation.isPending}
            >
              Mark Complete
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="admin-tabs" style={{ marginBottom: 20 }}>
        {TAB_LABELS.map((tab) => (
          <button
            key={tab}
            className={`admin-tab${activeTab === tab ? ' active' : ''}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {activeTab === 'Overview' && (
        <div className="grid-2">
          <div className="admin-card">
            <Section title="Booking Details">
              <Row label="Booking Number" value={b.booking_number ?? b.id?.slice(0, 8)} />
              <Row label="Celebration" value={b.celebration_title} />
              <Row label="Status" value={<StatusBadge status={b.booking_status} />} />
              <Row label="Payment Status" value={<StatusBadge status={b.payment_status} />} />
              <Row label="Scheduled Date" value={b.scheduled_date ? formatDate(b.scheduled_date) : null} />
              <Row label="Start Time" value={b.scheduled_start_time} />
              <Row label="End Time" value={b.scheduled_end_time} />
              <Row label="Preparation Start" value={b.preparation_start_at ? formatDateTime(b.preparation_start_at) : null} />
              {b.theme_name && <Row label="Customization Theme" value={b.theme_name} />}
              {b.balloon_colors?.length > 0 && (
                <Row
                  label={`Balloon Colours (${b.balloon_color_mode})`}
                  value={
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      {b.balloon_colors.map((c, i) => (
                        <span key={i} title={c} style={{ width: 16, height: 16, borderRadius: '50%', background: c, border: '1px solid rgba(0,0,0,0.15)', display: 'inline-block' }} />
                      ))}
                    </div>
                  }
                />
              )}
              <Row label="Special Instructions" value={b.special_instructions} />
              <Row label="Customization Note" value={b.customization_note} />
            </Section>
          </div>

          <div className="admin-card">
            <Section title="Customer Info">
              {/* BookingResponse sends customer_id (UUID) only — no nested customer object */}
              <Row label="Customer ID" value={b.customer_id ? <code style={{ fontSize: 12 }}>{b.customer_id.slice(0, 8)}</code> : null} />
              {/* Address fields not in BookingResponse; address_id is available if needed */}
              <Row label="Address ID" value={b.address_id ? <code style={{ fontSize: 12 }}>{b.address_id.slice(0, 8)}</code> : null} />
            </Section>
          </div>

          <div className="admin-card">
            <Section title="Package">
              <Row label="Package" value={b.package_name ?? (b.package_id ? <code style={{ fontSize: 12 }}>{b.package_id.slice(0, 8)}</code> : null)} />
            </Section>
          </div>

          <div className="admin-card">
            <Section title="Financial">
              <Row label="Subtotal" value={formatCurrency(b.subtotal ?? 0)} />
              <Row label="Discount" value={b.discount_amount ? formatCurrency(b.discount_amount) : '—'} />
              <Row label="Tax" value={formatCurrency(b.tax_amount ?? 0)} />
              <Row
                label="Total"
                value={<strong style={{ color: 'var(--text-primary)' }}>{formatCurrency(b.total_amount ?? 0)}</strong>}
              />
              <Row label="Amount Paid" value={formatCurrency(b.amount_paid ?? 0)} />
              <Row label="Amount Due" value={formatCurrency(b.amount_due ?? 0)} />
            </Section>
          </div>
        </div>
      )}

      {/* Items Tab */}
      {activeTab === 'Items' && (
        <div className="admin-card">
          {!items.length ? (
            <p style={{ color: 'var(--text-tertiary)', padding: '24px 0', textAlign: 'center' }}>No items on this booking.</p>
          ) : (
            <div className="admin-table-wrapper">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Item</th>
                    <th>Qty</th>
                    <th>Unit Price</th>
                    <th>Final Price</th>
                    <th>Customizations</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={item.id}>
                      <td>
                        <div className="admin-user-name">{item.package_item?.name ?? item.name ?? '—'}</div>
                        {item.package_item?.description && (
                          <div className="admin-user-email">{item.package_item.description}</div>
                        )}
                      </td>
                      <td>{item.quantity ?? 1}</td>
                      <td>{formatCurrency(item.unit_price ?? 0)}</td>
                      <td style={{ fontWeight: 600 }}>{formatCurrency(item.final_price ?? 0)}</td>
                      <td style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>
                        {item.customizations
                          ? Object.entries(item.customizations).map(([k, v]) => `${k}: ${v}`).join(', ')
                          : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* History Tab */}
      {activeTab === 'History' && (
        <div className="grid-2">
          <div className="admin-card">
            <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)', fontWeight: 600, fontSize: 14 }}>
              Status Transitions
            </div>
            <div style={{ padding: 16 }}>
              {!statusHistory.length ? (
                <p style={{ color: 'var(--text-tertiary)', fontSize: 13 }}>No status history yet.</p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {statusHistory.map((h, i) => (
                    <div key={i} className="admin-activity-item">
                      <div className="admin-activity-icon" style={{ background: 'var(--bg-raised)' }}>→</div>
                      <div className="admin-activity-content">
                        <div className="admin-activity-text">
                          {/* was: h.old_status / h.new_status — backend sends from_status / to_status */}
                          <StatusBadge status={h.from_status} /> → <StatusBadge status={h.to_status} />
                        </div>
                        {h.reason && <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginTop: 2 }}>{h.reason}</div>}
                        <div className="admin-activity-time">{h.changed_at ? formatDateTime(h.changed_at) : ''}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="admin-card">
            <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)', fontWeight: 600, fontSize: 14 }}>
              Event Log
            </div>
            <div style={{ padding: 16 }}>
              {!history.length ? (
                <p style={{ color: 'var(--text-tertiary)', fontSize: 13 }}>No events yet.</p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {history.map((h, i) => (
                    <div key={i} className="admin-activity-item">
                      <div className="admin-activity-icon">📌</div>
                      <div className="admin-activity-content">
                        <div className="admin-activity-text">{h.event ?? h.action ?? JSON.stringify(h)}</div>
                        {h.timestamp && <div className="admin-activity-time">{formatDateTime(h.timestamp)}</div>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Set PST modal */}
      <Modal
        open={pstModalOpen}
        onClose={() => setPstModalOpen(false)}
        title="Preparation Start Date & Time"
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setPstModalOpen(false)}>Cancel</button>
            <button
              className="btn btn-primary"
              onClick={() => setPstMutation.mutate()}
              disabled={!pstValue || setPstMutation.isPending}
            >
              {setPstMutation.isPending ? <span className="spinner" style={{ width: 14, height: 14 }} /> : 'Save'}
            </button>
          </>
        }
      >
        <p style={{ color: 'var(--text-secondary)', marginBottom: 12 }}>
          Set the date and time you'll arrive and begin preparation at the customer's event location. The customer is notified by email, in-app and push once you save.
        </p>
        <input
          type="datetime-local"
          className="form-control"
          value={pstValue}
          onChange={(e) => setPstValue(e.target.value)}
        />
      </Modal>

      {/* Confirm dialogs */}
      <ConfirmDialog
        open={confirmStart}
        onClose={() => setConfirmStart(false)}
        onConfirm={() => startMutation.mutate()}
        title="Start Service"
        message="Confirm that you have arrived and the service has started?"
        loading={startMutation.isPending}
      />
      <ConfirmDialog
        open={confirmComplete}
        onClose={() => setConfirmComplete(false)}
        onConfirm={() => completeMutation.mutate()}
        title="Complete Service"
        message="Confirm that the service has been fully completed and delivered?"
        loading={completeMutation.isPending}
      />
    </div>
  );
}
