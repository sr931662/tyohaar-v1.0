import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { vendorsApi, walletsApi } from '../../api';
import { formatDate, formatCurrency, initials, timeAgo } from '../../utils/format';
import StatusBadge from '../../components/ui/StatusBadge';
import Modal from '../../components/ui/Modal';
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

export default function VendorDetailPage() {
  const { vendorId } = useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [verifyOpen, setVerifyOpen] = useState(false);
  const [verifyAction, setVerifyAction] = useState('');
  const [verifyNote, setVerifyNote] = useState('');
  const [activeTab, setActiveTab] = useState('overview');
  const [creditOpen, setCreditOpen] = useState(false);
  const [creditForm, setCreditForm] = useState({ amount: '', description: '' });

  const { data: crm, isLoading } = useQuery({
    queryKey: ['vendor', 'crm', vendorId],
    queryFn: () => vendorsApi.crmProfile(vendorId),
  });

  const { data: documents } = useQuery({
    queryKey: ['vendor', vendorId, 'documents'],
    queryFn: () => vendorsApi.listDocuments(vendorId),
    enabled: activeTab === 'documents',
  });

  const { data: reviews } = useQuery({
    queryKey: ['vendor', vendorId, 'reviews'],
    queryFn: () => vendorsApi.listReviews(vendorId),
    enabled: activeTab === 'reviews',
  });

  const verifyMutation = useMutation({
    mutationFn: ({ action, note }) => vendorsApi.verify(vendorId, { action, note }),
    onSuccess: () => {
      toast.success(`Vendor ${verifyAction}d successfully`);
      qc.invalidateQueries(['vendor', 'crm', vendorId]);
      setVerifyOpen(false);
    },
    onError: () => toast.error('Verification action failed'),
  });

  const creditMutation = useMutation({
    mutationFn: ({ userId, amount, description }) =>
      walletsApi.credit(userId, { amount, description }),
    onSuccess: () => {
      toast.success('Wallet credited successfully');
      qc.invalidateQueries(['vendor', 'crm', vendorId]);
      setCreditOpen(false);
      setCreditForm({ amount: '', description: '' });
    },
    onError: () => toast.error('Failed to credit wallet'),
  });

  if (isLoading) return (
    <div>
      <div className="admin-page-header">
        <button className="btn btn-ghost" onClick={() => navigate(-1)}>← Back</button>
      </div>
      {[1, 2, 3].map(i => <SkeletonCard key={i} height={160} />)}
    </div>
  );

  if (!crm) return <div className="admin-empty"><div className="admin-empty-title">Vendor not found</div></div>;

  // CRM profile structure: { summary, kyc, financials, ratings, monthly_performance, recent_bookings, timeline }
  const s = crm.summary ?? {};
  const fin = crm.financials ?? {};
  const ratings = crm.ratings ?? {};
  const recentBookings = crm.recent_bookings ?? [];
  const monthlyPerf = crm.monthly_performance ?? [];

  const userId = s.user_id; // needed for wallet credit/debit

  const verifyStatus = s.verification_status?.toLowerCase();
  const tabs = ['overview', 'documents', 'reviews', 'bookings', 'financials'];

  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <button className="btn btn-ghost" onClick={() => navigate(-1)}>←</button>
            <div className="admin-avatar lg" style={{ background: 'var(--brand-100)', color: 'var(--brand-700)', fontSize: 18 }}>
              {s.logo_url ? (
                <img src={s.logo_url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: '50%' }} />
              ) : initials(s.business_name ?? 'V')}
            </div>
            <div>
              <h1 style={{ marginBottom: 2 }}>{s.business_name ?? '—'}</h1>
              <StatusBadge status={verifyStatus} />
            </div>
          </div>
        </div>
        <div className="admin-page-header-actions">
          {(verifyStatus === 'pending') && (
            <>
              <button className="btn btn-success" onClick={() => { setVerifyAction('approve'); setVerifyOpen(true); }}>Approve</button>
              <button className="btn btn-danger" onClick={() => { setVerifyAction('reject'); setVerifyOpen(true); }}>Reject</button>
            </>
          )}
          {verifyStatus === 'approved' && (
            <button className="btn btn-secondary" onClick={() => { setVerifyAction('suspend'); setVerifyOpen(true); }}>Suspend</button>
          )}
          {verifyStatus === 'suspended' && (
            <button className="btn btn-success" onClick={() => { setVerifyAction('activate'); setVerifyOpen(true); }}>Activate</button>
          )}
        </div>
      </div>

      {/* Metric row */}
      <div className="admin-metric-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)', marginBottom: 20 }}>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Total Bookings</div>
          <div className="admin-metric-value">{fin.total_bookings ?? 0}</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Lifetime Revenue</div>
          <div className="admin-metric-value">{formatCurrency(fin.total_revenue_lifetime ?? 0)}</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Avg Rating</div>
          <div className="admin-metric-value">⭐ {ratings.avg_rating ? Number(ratings.avg_rating).toFixed(1) : '—'}</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Wallet Balance</div>
          <div className="admin-metric-value">{formatCurrency(fin.wallet_balance ?? 0)}</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="admin-tabs">
        {tabs.map((t) => (
          <button key={t} className={`admin-tab${activeTab === t ? ' active' : ''}`} onClick={() => setActiveTab(t)}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {activeTab === 'overview' && (
        <div className="grid-2">
          <div className="admin-card">
            <div className="admin-card-header"><div className="admin-card-title">Business Info</div></div>
            <div className="admin-card-body">
              <Section>
                <Row label="Business Name" value={s.business_name} />
                <Row label="Email" value={s.email} />
                <Row label="Phone" value={s.phone} />
                <Row label="City" value={s.city} />
                <Row label="State" value={s.state} />
                <Row label="Verification" value={<StatusBadge status={verifyStatus} />} />
                <Row label="Account Status" value={<StatusBadge status={s.account_status?.toLowerCase()} />} />
                <Row label="Member Since" value={formatDate(s.onboarded_at)} />
              </Section>
            </div>
          </div>

          <div className="admin-card">
            <div className="admin-card-header"><div className="admin-card-title">Performance</div></div>
            <div className="admin-card-body">
              <Section>
                <Row label="Total Reviews" value={ratings.total_reviews ?? 0} />
                <Row label="Avg Rating" value={ratings.avg_rating ? `${Number(ratings.avg_rating).toFixed(1)} / 5.0` : '—'} />
                <Row label="Completed" value={fin.completed_bookings ?? 0} />
                <Row label="Cancelled" value={fin.cancelled_bookings ?? 0} />
                <Row label="Avg Booking Value" value={formatCurrency(fin.avg_booking_value ?? 0)} />
                <Row label="Pending Settlement" value={formatCurrency(fin.pending_settlement ?? 0)} />
              </Section>
            </div>
          </div>

          {monthlyPerf.length > 0 && (
            <div className="admin-card" style={{ gridColumn: '1 / -1' }}>
              <div className="admin-card-header"><div className="admin-card-title">Monthly Performance</div></div>
              <div className="admin-table-wrapper">
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>Month</th>
                      <th>Bookings</th>
                      <th>Revenue</th>
                    </tr>
                  </thead>
                  <tbody>
                    {monthlyPerf.map((m) => (
                      <tr key={m.label ?? `${m.year}-${m.month}`}>
                        <td>{m.label ?? `${m.year}-${m.month}`}</td>
                        <td>{m.bookings}</td>
                        <td>{formatCurrency(m.revenue)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'documents' && (
        <div className="admin-table-wrapper">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Document Type</th>
                <th>Status</th>
                <th>Uploaded</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {(documents ?? []).map((doc) => (
                <tr key={doc.id}>
                  <td>{doc.document_type?.replace(/_/g, ' ')}</td>
                  <td><StatusBadge status={doc.verification_status} /></td>
                  <td>{formatDate(doc.created_at)}</td>
                  <td>
                    {doc.document_url && (
                      <a href={doc.document_url} target="_blank" rel="noopener noreferrer" className="btn btn-secondary btn-sm">
                        View
                      </a>
                    )}
                  </td>
                </tr>
              ))}
              {!documents?.length && (
                <tr><td colSpan={4} className="admin-table-empty">No documents uploaded</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'reviews' && (
        <div className="admin-table-wrapper">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Reviewer</th>
                <th>Rating</th>
                <th>Comment</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {(reviews?.items ?? []).map((r) => (
                <tr key={r.id}>
                  <td>{r.reviewer_name ?? r.user?.name ?? '—'}</td>
                  <td>{'⭐'.repeat(r.rating ?? 0)}</td>
                  <td style={{ maxWidth: 300 }}>{r.comment ?? '—'}</td>
                  <td>{formatDate(r.created_at)}</td>
                </tr>
              ))}
              {!reviews?.items?.length && (
                <tr><td colSpan={4} className="admin-table-empty">No reviews yet</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'bookings' && (
        <div className="admin-table-wrapper">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Booking ID</th>
                <th>Status</th>
                <th>Amount</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {recentBookings.map((b) => (
                <tr key={b.id} style={{ cursor: 'pointer' }} onClick={() => navigate(`/admin/bookings/${b.id}`)}>
                  <td><code style={{ fontSize: 11 }}>{b.id?.slice(0, 8)}</code></td>
                  <td><StatusBadge status={b.status?.toLowerCase()} /></td>
                  <td>{formatCurrency(b.amount)}</td>
                  <td>{formatDate(b.date)}</td>
                </tr>
              ))}
              {!recentBookings.length && (
                <tr><td colSpan={4} className="admin-table-empty">No recent bookings</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'financials' && (
        <div className="grid-2">
          <div className="admin-card">
            <div className="admin-card-header">
              <div className="admin-card-title">Wallet</div>
              {userId && (
                <button className="btn btn-primary btn-sm" onClick={() => setCreditOpen(true)}>
                  Credit Wallet
                </button>
              )}
            </div>
            <div className="admin-card-body">
              <Section>
                <Row label="Wallet Balance" value={formatCurrency(fin.wallet_balance ?? 0)} />
                <Row label="Pending Settlement" value={formatCurrency(fin.pending_settlement ?? 0)} />
                <Row label="Commission Earned (Platform)" value={formatCurrency(fin.commission_earned_platform ?? 0)} />
              </Section>
            </div>
          </div>

          <div className="admin-card">
            <div className="admin-card-header"><div className="admin-card-title">Revenue Summary</div></div>
            <div className="admin-card-body">
              <Section>
                <Row label="Lifetime Revenue" value={formatCurrency(fin.total_revenue_lifetime ?? 0)} />
                <Row label="This Month" value={formatCurrency(fin.revenue_this_month ?? 0)} />
                <Row label="Last Month" value={formatCurrency(fin.revenue_last_month ?? 0)} />
                <Row label="Avg Booking Value" value={formatCurrency(fin.avg_booking_value ?? 0)} />
                <Row label="Completed Bookings" value={fin.completed_bookings ?? 0} />
                <Row label="Cancelled Bookings" value={fin.cancelled_bookings ?? 0} />
              </Section>
            </div>
          </div>
        </div>
      )}

      {/* Verify Modal */}
      <Modal
        open={verifyOpen}
        onClose={() => setVerifyOpen(false)}
        title={`${verifyAction?.charAt(0).toUpperCase()}${verifyAction?.slice(1)} Vendor`}
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setVerifyOpen(false)}>Cancel</button>
            <button
              className={`btn ${verifyAction === 'approve' || verifyAction === 'activate' ? 'btn-success' : 'btn-danger'}`}
              onClick={() => verifyMutation.mutate({ action: verifyAction, note: verifyNote })}
              disabled={verifyMutation.isPending}
            >
              {verifyMutation.isPending ? 'Processing…' : `Confirm ${verifyAction}`}
            </button>
          </>
        }
      >
        <div className="form-group">
          <label className="form-label">Note (optional)</label>
          <textarea
            className="form-control"
            value={verifyNote}
            onChange={(e) => setVerifyNote(e.target.value)}
            placeholder={`Reason for ${verifyAction}…`}
            rows={3}
          />
        </div>
      </Modal>

      {/* Credit Wallet Modal */}
      <Modal
        open={creditOpen}
        onClose={() => setCreditOpen(false)}
        title="Credit Vendor Wallet"
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setCreditOpen(false)}>Cancel</button>
            <button
              className="btn btn-primary"
              onClick={() => creditMutation.mutate({ userId, amount: creditForm.amount, description: creditForm.description })}
              disabled={creditMutation.isPending || !creditForm.amount}
            >
              {creditMutation.isPending ? 'Processing…' : 'Credit'}
            </button>
          </>
        }
      >
        <div className="form-group" style={{ marginBottom: 12 }}>
          <label className="form-label">Amount (₹) *</label>
          <input
            type="number"
            className="form-control"
            value={creditForm.amount}
            onChange={(e) => setCreditForm(f => ({ ...f, amount: e.target.value }))}
            placeholder="Enter amount"
            min="1"
          />
        </div>
        <div className="form-group">
          <label className="form-label">Description</label>
          <input
            className="form-control"
            value={creditForm.description}
            onChange={(e) => setCreditForm(f => ({ ...f, description: e.target.value }))}
            placeholder="Reason for credit"
          />
        </div>
      </Modal>
    </div>
  );
}
