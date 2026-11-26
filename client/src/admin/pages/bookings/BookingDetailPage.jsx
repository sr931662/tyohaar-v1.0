import { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { bookingsApi } from '../../api';
import { formatDate, formatDateTime, formatCurrency } from '../../utils/format';
import StatusBadge from '../../components/ui/StatusBadge';
import { ConfirmDialog } from '../../components/ui/Modal';
import { SkeletonCard } from '../../components/ui/Skeleton';
import BalloonMix from '../../../components/BalloonMix';
import { formatLineQuantity } from '../../../constants/packageUnits';

// ── helpers ──────────────────────────────────────────────────────────────────

const NONE = '—';

/** "credit_card" → "Credit Card"; "upi" → "UPI". */
function human(value) {
  if (!value) return NONE;
  const v = String(value).replace(/_/g, ' ');
  return v.length <= 3 ? v.toUpperCase() : v.replace(/\b\w/g, (c) => c.toUpperCase());
}

/** "18:30:00" → "6:30 PM". */
function formatTime(t) {
  if (!t) return null;
  const [h, m] = String(t).split(':').map(Number);
  if (Number.isNaN(h)) return String(t);
  const hour12 = ((h + 11) % 12) + 1;
  return `${hour12}:${String(m || 0).padStart(2, '0')} ${h >= 12 ? 'PM' : 'AM'}`;
}

const num = (v) => Number(v ?? 0);

function errorMessage(err, fallback) {
  return err?.response?.data?.error?.message ?? err?.response?.data?.message ?? fallback;
}

const LINE_KINDS = {
  rental: { label: 'Rental', hint: 'Returned after the event', color: 'info' },
  keep: { label: 'Keep', hint: 'Customer keeps it', color: 'success' },
  service: { label: 'Service', hint: 'Done by the vendor', color: 'warning' },
};

function mapsHref(address) {
  if (!address) return null;
  if (address.maps_link) return address.maps_link;
  if (address.latitude != null && address.longitude != null) {
    return `https://www.google.com/maps?q=${address.latitude},${address.longitude}`;
  }
  return null;
}

function Row({ label, children, muted }) {
  const empty = children == null || children === '' || children === false;
  return (
    <div className="admin-detail-row">
      <div className="admin-detail-label">{label}</div>
      <div className="admin-detail-value" style={empty || muted ? { color: 'var(--text-tertiary)' } : undefined}>
        {empty ? NONE : children}
      </div>
    </div>
  );
}

function Card({ title, children, right }) {
  return (
    <div className="admin-card">
      <div className="admin-card-header" style={right ? { display: 'flex', justifyContent: 'space-between', alignItems: 'center' } : undefined}>
        <div className="admin-card-title">{title}</div>
        {right}
      </div>
      <div className="admin-card-body">{children}</div>
    </div>
  );
}

const linkStyle = { color: 'var(--text-brand)', textDecoration: 'none', fontWeight: 600 };

// ── page ─────────────────────────────────────────────────────────────────────

export default function BookingDetailPage() {
  const { bookingId } = useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState('overview');
  const [cancelOpen, setCancelOpen] = useState(false);

  const { data: booking, isLoading, isError, refetch } = useQuery({
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

  const refresh = () => qc.invalidateQueries({ queryKey: ['booking', bookingId] });

  const confirmMutation = useMutation({
    mutationFn: () => bookingsApi.confirm(bookingId),
    onSuccess: () => { toast.success('Booking confirmed'); refresh(); },
    onError: (e) => toast.error(errorMessage(e, 'Failed to confirm booking')),
  });

  // "Cancel" cancels: it APPROVES a cancellation. (It used to send approved=false,
  // which is the "decline a cancellation request" action and put the booking
  // back to Confirmed instead of cancelling it.)
  const cancelMutation = useMutation({
    mutationFn: () => bookingsApi.processCancellation(bookingId, true),
    onSuccess: () => { toast.success('Booking cancelled'); refresh(); setCancelOpen(false); },
    onError: (e) => { toast.error(errorMessage(e, 'Failed to cancel booking')); setCancelOpen(false); },
  });

  const generateInvoiceMutation = useMutation({
    mutationFn: () => bookingsApi.generateInvoice(bookingId),
    onSuccess: () => { toast.success('Invoice generated'); refresh(); },
    onError: (e) => toast.error(errorMessage(e, 'Failed to generate invoice')),
  });

  if (isLoading) return (
    <div>
      <div className="admin-page-header"><button className="btn btn-ghost" onClick={() => navigate(-1)}>← Back</button></div>
      {[1, 2, 3].map((i) => <SkeletonCard key={i} height={120} />)}
    </div>
  );

  if (isError) return (
    <div className="admin-empty">
      <div className="admin-empty-title">Couldn't load this booking</div>
      <button className="btn btn-secondary" style={{ marginTop: 12 }} onClick={() => refetch()}>Try again</button>
    </div>
  );

  if (!booking) return <div className="admin-empty"><div className="admin-empty-title">Booking not found</div></div>;

  const b = booking;
  const lines = b.lines ?? [];
  const payments = b.payments ?? [];
  // "Paid" means what the server means by it: Razorpay-confirmed AND nothing left to pay.
  const paid = b.payment_status === 'completed' && num(b.amount_due) <= 0.009;
  const customerName = b.customer?.full_name || b.customer?.email || b.customer?.phone || null;
  const addr = b.address;
  const mapLink = mapsHref(addr);
  const startTime = formatTime(b.scheduled_start_time);
  const endTime = formatTime(b.scheduled_end_time);

  // The price, rebuilt line by line, so the page shows how the total was reached.
  const basePrice = b.package_base_price != null ? num(b.package_base_price) : null;
  const includedTotal = lines.filter((l) => !l.is_addon).reduce((s, l) => s + num(l.final_price), 0);
  const addonsTotal = lines.filter((l) => l.is_addon).reduce((s, l) => s + num(l.final_price), 0);
  const explained = (basePrice ?? 0) + includedTotal + addonsTotal;
  // Anything the lines do not account for (an older booking, a price changed
  // since) is shown rather than hidden, so the rows always add up.
  const otherAdjustments = basePrice == null ? 0 : num(b.subtotal) - explained;

  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <button className="btn btn-ghost" onClick={() => navigate(-1)} aria-label="Back">←</button>
            <div>
              <h1>
                Booking{' '}
                <code style={{ fontSize: 14, background: 'var(--bg-base)', padding: '2px 8px', borderRadius: 4 }}>
                  {b.booking_number ?? b.id?.slice(0, 8)}
                </code>
              </h1>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginTop: 4 }}>
                <StatusBadge status={b.booking_status} />
                <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Payment</span>
                <StatusBadge status={b.payment_status} />
                {b.package_name && (
                  <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                    · {b.package_name}{b.occasion_name ? ` · ${b.occasion_name}` : ''}
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
        <div className="admin-page-header-actions">
          {b.booking_status === 'pending' && (
            <button
              className="btn btn-success"
              onClick={() => confirmMutation.mutate()}
              disabled={confirmMutation.isPending || !paid}
              title={paid ? undefined : "Can be confirmed once Razorpay has confirmed the customer's full payment"}
            >
              Confirm Booking
            </button>
          )}
          {['pending', 'confirmed'].includes(b.booking_status) && (
            <button className="btn btn-danger" onClick={() => setCancelOpen(true)}>Cancel</button>
          )}
          {b.booking_status === 'completed' && (
            <button className="btn btn-secondary" onClick={() => generateInvoiceMutation.mutate()} disabled={generateInvoiceMutation.isPending}>
              Generate Invoice
            </button>
          )}
        </div>
      </div>

      {b.booking_status === 'pending' && !paid && (
        <div style={{ margin: '0 0 16px', padding: '10px 14px', borderRadius: 8, background: 'var(--bg-surface)', border: '1px solid var(--border-default)', fontSize: 13, color: 'var(--text-secondary)' }}>
          Waiting for the customer's payment. A booking is confirmed automatically once Razorpay confirms the full amount, and can't be confirmed before that.
        </div>
      )}

      {/* Metrics */}
      <div className="admin-metric-grid" style={{ marginBottom: 20 }}>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Total Amount</div>
          <div className="admin-metric-value">{formatCurrency(b.total_amount)}</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Paid</div>
          <div className="admin-metric-value">{formatCurrency(b.amount_paid ?? 0)}</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Balance Due</div>
          <div className="admin-metric-value">{formatCurrency(b.amount_due ?? 0)}</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Event</div>
          <div className="admin-metric-value" style={{ fontSize: 16 }}>
            {formatDate(b.scheduled_date)}
            {startTime && <div style={{ fontSize: 12.5, fontWeight: 500, color: 'var(--text-secondary)', marginTop: 2 }}>{startTime}{endTime ? ` – ${endTime}` : ''}</div>}
          </div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Booked On</div>
          <div className="admin-metric-value" style={{ fontSize: 16 }}>{formatDateTime(b.created_at)}</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="admin-tabs">
        {[
          ['overview', 'Overview'],
          ['items', `Items${lines.length ? ` (${lines.length})` : ''}`],
          ['payments', `Payments${payments.length ? ` (${payments.length})` : ''}`],
          ['history', 'History'],
        ].map(([key, label]) => (
          <button key={key} className={`admin-tab${activeTab === key ? ' active' : ''}`} onClick={() => setActiveTab(key)}>
            {label}
          </button>
        ))}
      </div>

      {activeTab === 'overview' && (
        <div className="grid-2">
          <Card title="Customer">
            <Row label="Name">
              {b.customer_id && customerName
                ? <Link to={`/admin/customers/${b.customer_id}`} style={linkStyle}>{customerName}</Link>
                : customerName}
            </Row>
            <Row label="Email">{b.customer?.email}</Row>
            <Row label="Phone">{b.customer?.phone}</Row>
          </Card>

          <Card title="Vendor">
            <Row label="Business Name">
              {b.vendor?.id && b.vendor?.business_name
                ? <Link to={`/admin/vendors/${b.vendor.id}`} style={linkStyle}>{b.vendor.business_name}</Link>
                : (b.vendor?.business_name ?? 'Not assigned')}
            </Row>
            <Row label="Email">{b.vendor?.email}</Row>
            <Row label="Phone">{b.vendor?.phone}</Row>
            <Row label="Verification">{b.vendor?.verification_status ? <StatusBadge status={b.vendor.verification_status} /> : null}</Row>
          </Card>

          <Card title="Event">
            <Row label="Celebration">{b.celebration_title}</Row>
            <Row label="Occasion">{b.occasion_name}</Row>
            <Row label="Package">
              {b.package_id && b.package_name
                ? <Link to={`/admin/packages/${b.package_id}`} style={linkStyle}>{b.package_name}</Link>
                : b.package_name}
            </Row>
            <Row label="Event Date">{formatDate(b.scheduled_date)}</Row>
            <Row label="Time">{startTime ? `${startTime}${endTime ? ` – ${endTime}` : ''}` : null}</Row>
            <Row label="Preparation Start (PST)">
              {b.preparation_start_at ? formatDateTime(b.preparation_start_at) : formatTime(b.preparation_start_time)}
            </Row>
            <Row label="Booked On">{formatDateTime(b.created_at)}</Row>
            {b.confirmed_at && <Row label="Confirmed On">{formatDateTime(b.confirmed_at)}</Row>}
            {b.completed_at && <Row label="Completed On">{formatDateTime(b.completed_at)}</Row>}
          </Card>

          <Card title="Delivery & Contact">
            <Row label="Contact Person">{b.recipient_name || addr?.recipient_name}</Row>
            <Row label="Contact Phone">{b.recipient_phone || addr?.recipient_phone}</Row>
            <Row label="Address">
              {addr?.full_address
                ? <>{addr.label && <strong>{addr.label}: </strong>}{addr.full_address}</>
                : b.venue_address}
            </Row>
            {addr?.full_address && b.venue_address && b.venue_address !== addr.full_address && (
              <Row label="Venue (as entered)">{b.venue_address}</Row>
            )}
            {b.venue_name && <Row label="Venue Name">{b.venue_name}</Row>}
            {addr?.delivery_instructions && <Row label="Instructions">{addr.delivery_instructions}</Row>}
            <Row label="Map">
              {mapLink
                ? <a href={mapLink} target="_blank" rel="noopener noreferrer" style={linkStyle}>Open in Google Maps ↗</a>
                : null}
            </Row>
          </Card>

          <Card title="Customisation">
            {b.theme_name && <Row label="Theme">{b.theme_name}</Row>}
            <Row label={`Balloon Colours${b.balloon_color_mode ? ` (${human(b.balloon_color_mode)})` : ''}`}>
              {b.balloon_colors?.length > 0 ? <BalloonMix colors={b.balloon_colors} ratios={b.balloon_color_ratios} /> : null}
            </Row>
            <Row label="Balloon Finish">{b.balloon_finish}</Row>
            <Row label="Special Instructions">{b.special_instructions}</Row>
            <Row label="Customisation Note">{b.customization_note}</Row>
          </Card>

          <Card title="Price Breakdown">
            {basePrice != null && <Row label="Package Price">{formatCurrency(basePrice)}</Row>}
            {includedTotal > 0 && <Row label="Included Items & Services">{formatCurrency(includedTotal)}</Row>}
            {addonsTotal > 0 && <Row label="Add-ons">{formatCurrency(addonsTotal)}</Row>}
            {Math.abs(otherAdjustments) > 0.009 && <Row label="Other Adjustments">{formatCurrency(otherAdjustments)}</Row>}
            <Row label="Subtotal">{formatCurrency(b.subtotal ?? 0)}</Row>
            <Row label={`Discount${b.applied_coupon_codes?.length ? ` (${b.applied_coupon_codes.join(', ')})` : ''}`}>
              {num(b.discount_amount) > 0 ? `− ${formatCurrency(b.discount_amount)}` : null}
            </Row>
            {num(b.tax_amount) > 0 && <Row label="Tax (GST)">{formatCurrency(b.tax_amount)}</Row>}
            {num(b.platform_fee) > 0 && <Row label="Platform Fee">{formatCurrency(b.platform_fee)}</Row>}
            <Row label="Total"><strong>{formatCurrency(b.total_amount)}</strong></Row>
            <Row label="Paid">{formatCurrency(b.amount_paid ?? 0)}</Row>
            <Row label="Balance Due">{formatCurrency(b.amount_due ?? 0)}</Row>
          </Card>

          {b.cancellation && (
            <Card title="Cancellation">
              <Row label="Reason">{human(b.cancellation.reason)}</Row>
              <Row label="Details">{b.cancellation.reason_detail}</Row>
              <Row label="Cancelled On">{formatDateTime(b.cancellation.cancelled_at)}</Row>
              <Row label="Cancellation Fee">{b.cancellation.cancellation_fee != null ? formatCurrency(b.cancellation.cancellation_fee) : null}</Row>
              <Row label="Refund Amount">{b.cancellation.refund_amount != null ? formatCurrency(b.cancellation.refund_amount) : null}</Row>
            </Card>
          )}

          {!b.cancellation && b.cancellation_reason && (
            <Card title="Cancellation">
              <Row label="Reason">{human(b.cancellation_reason)}</Row>
            </Card>
          )}

          {(b.reschedules ?? []).length > 0 && (
            <Card title="Reschedules">
              {b.reschedules.map((r) => (
                <Row key={r.id} label={formatDate(r.rescheduled_at ?? r.created_at)}>
                  {formatDate(r.previous_date)} → {formatDate(r.new_date)}{r.reason ? ` · ${r.reason}` : ''}
                </Row>
              ))}
            </Card>
          )}

          {(b.invoices ?? []).length > 0 && (
            <Card title="Invoice">
              {b.invoices.map((inv) => (
                <div key={inv.id}>
                  <Row label="Invoice No.">{inv.invoice_number}</Row>
                  <Row label="Status"><StatusBadge status={inv.invoice_status} /></Row>
                  <Row label="Amount">{formatCurrency(inv.total_amount)}</Row>
                  <Row label="Issued">{inv.issued_at ? formatDateTime(inv.issued_at) : null}</Row>
                </div>
              ))}
            </Card>
          )}
        </div>
      )}

      {activeTab === 'items' && (
        <div className="admin-table-wrapper">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Item</th>
                <th>Type</th>
                <th>Quantity</th>
                <th>Unit Price</th>
                <th>Final Price</th>
              </tr>
            </thead>
            <tbody>
              {basePrice != null && (
                <tr>
                  <td><strong>{b.package_name ?? 'Package'}</strong><div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Package base price</div></td>
                  <td>{NONE}</td>
                  <td>1</td>
                  <td>{formatCurrency(basePrice)}</td>
                  <td>{formatCurrency(basePrice)}</td>
                </tr>
              )}
              {lines.map((l, i) => {
                const kind = LINE_KINDS[l.kind] ?? { label: human(l.kind), color: 'info' };
                return (
                  <tr key={`${l.name}-${i}`}>
                    <td>
                      <strong>{l.name}</strong>
                      {l.is_addon && <span className="badge badge-info" style={{ marginLeft: 8 }}>Add-on</span>}
                      {l.description && <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{l.description}</div>}
                      {l.note && <div style={{ fontSize: 12.5, marginTop: 2 }}>Customer asked for: <strong>{l.note}</strong></div>}
                    </td>
                    <td><span className={`badge badge-${kind.color}`} title={kind.hint}>{kind.label}</span></td>
                    <td>{formatLineQuantity(l)}</td>
                    <td>{formatCurrency(l.unit_price)}</td>
                    <td>{formatCurrency(l.final_price)}</td>
                  </tr>
                );
              })}
              {!lines.length && basePrice == null && <tr><td colSpan={5} className="admin-table-empty">No items on this booking</td></tr>}
            </tbody>
            {(lines.length > 0 || basePrice != null) && (
              <tfoot>
                {Math.abs(otherAdjustments) > 0.009 && (
                  <tr><td colSpan={4} style={{ textAlign: 'right' }}>Other adjustments</td><td>{formatCurrency(otherAdjustments)}</td></tr>
                )}
                <tr><td colSpan={4} style={{ textAlign: 'right' }}><strong>Subtotal</strong></td><td><strong>{formatCurrency(b.subtotal ?? 0)}</strong></td></tr>
                {num(b.discount_amount) > 0 && (
                  <tr><td colSpan={4} style={{ textAlign: 'right' }}>Discount</td><td>− {formatCurrency(b.discount_amount)}</td></tr>
                )}
                {num(b.tax_amount) > 0 && (
                  <tr><td colSpan={4} style={{ textAlign: 'right' }}>Tax (GST)</td><td>{formatCurrency(b.tax_amount)}</td></tr>
                )}
                <tr><td colSpan={4} style={{ textAlign: 'right' }}><strong>Total</strong></td><td><strong>{formatCurrency(b.total_amount)}</strong></td></tr>
              </tfoot>
            )}
          </table>
        </div>
      )}

      {activeTab === 'payments' && (
        <div className="admin-table-wrapper">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Payment</th>
                <th>Status</th>
                <th>Method</th>
                <th>Gateway Ref</th>
                <th>Amount</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {payments.map((p) => (
                <tr key={p.id}>
                  <td><code style={{ fontSize: 12 }}>{p.payment_number ?? p.id.slice(0, 8)}</code></td>
                  <td><StatusBadge status={p.payment_status} /></td>
                  <td>{human(p.payment_method)}{p.gateway ? ` · ${human(p.gateway)}` : ''}</td>
                  <td>{p.gateway_payment_id ? <code style={{ fontSize: 12 }}>{p.gateway_payment_id}</code> : NONE}</td>
                  <td>{formatCurrency(p.final_amount)}</td>
                  <td>{formatDateTime(p.captured_at ?? p.failed_at ?? p.created_at)}</td>
                </tr>
              ))}
              {!payments.length && <tr><td colSpan={6} className="admin-table-empty">No payment has been attempted yet</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'history' && (
        <div className="grid-2">
          <Card title="Status History">
            {(statusHistory ?? []).map((s) => (
              <div key={s.id} className="admin-activity-item">
                <div className="admin-activity-icon">→</div>
                <div className="admin-activity-content">
                  <div className="admin-activity-text">
                    {s.from_status ? <><StatusBadge status={s.from_status} /> → </> : 'Created as '}
                    <StatusBadge status={s.to_status} />
                  </div>
                  {s.reason && <div style={{ fontSize: 12.5, color: 'var(--text-secondary)' }}>{s.reason}</div>}
                  <div className="admin-activity-time">{formatDateTime(s.changed_at)} · {s.changed_by_name ?? (s.changed_by_id ? 'Unknown user' : 'System')}</div>
                </div>
              </div>
            ))}
            {!statusHistory?.length && <div style={{ padding: '16px 0', color: 'var(--text-secondary)', textAlign: 'center' }}>No status history</div>}
          </Card>
          <Card title="Event Log">
            {(history ?? []).map((h) => (
              <div key={h.id} className="admin-activity-item">
                <div className="admin-activity-icon">•</div>
                <div className="admin-activity-content">
                  <div className="admin-activity-text">{h.event_label ?? human(h.event_type)}</div>
                  {h.description && <div style={{ fontSize: 12.5, color: 'var(--text-secondary)' }}>{h.description}</div>}
                  <div className="admin-activity-time">
                    {formatDateTime(h.occurred_at)} · {h.actor_name ?? human(h.actor_type)}
                  </div>
                </div>
              </div>
            ))}
            {!history?.length && <div style={{ padding: '16px 0', color: 'var(--text-secondary)', textAlign: 'center' }}>No events logged</div>}
          </Card>
        </div>
      )}

      <ConfirmDialog
        open={cancelOpen}
        onClose={() => setCancelOpen(false)}
        onConfirm={() => cancelMutation.mutate()}
        title="Cancel Booking"
        message={
          num(b.amount_paid) > 0
            ? `Cancel booking ${b.booking_number}? The customer has already paid ${formatCurrency(b.amount_paid)}; a refund will be processed under the cancellation policy.`
            : `Cancel booking ${b.booking_number}? No payment has been received for it.`
        }
        danger
        loading={cancelMutation.isPending}
      />
    </div>
  );
}
