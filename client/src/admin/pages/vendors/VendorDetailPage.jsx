import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { vendorsApi } from '../../api';
import { formatDate, formatCurrency, initials, timeAgo } from '../../utils/format';
import StatusBadge from '../../components/ui/StatusBadge';
import Modal from '../../components/ui/Modal';
import { SkeletonCard } from '../../components/ui/Skeleton';

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

export default function VendorDetailPage() {
  const { vendorId } = useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [verifyOpen, setVerifyOpen] = useState(false);
  const [verifyAction, setVerifyAction] = useState('');
  const [verifyNote, setVerifyNote] = useState('');
  const [activeTab, setActiveTab] = useState('overview');

  const { data: vendor, isLoading } = useQuery({
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

  if (isLoading) return (
    <div>
      <div className="admin-page-header">
        <button className="btn btn-ghost" onClick={() => navigate(-1)}>← Back</button>
      </div>
      {[1,2,3].map(i => <SkeletonCard key={i} height={160} />)}
    </div>
  );

  if (!vendor) return <div className="admin-empty"><div className="admin-empty-title">Vendor not found</div></div>;

  const v = vendor?.vendor ?? vendor;
  const analytics = vendor?.analytics ?? {};
  const recentBookings = vendor?.recent_bookings ?? [];

  const tabs = ['overview', 'documents', 'reviews', 'bookings'];

  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <button className="btn btn-ghost" onClick={() => navigate(-1)}>←</button>
            <div className="admin-avatar lg" style={{ background: 'var(--brand-100)', color: 'var(--brand-700)', fontSize: 18 }}>
              {v.logo_url ? (
                <img src={v.logo_url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: '50%' }} />
              ) : initials(v.business_name ?? 'V')}
            </div>
            <div>
              <h1 style={{ marginBottom: 2 }}>{v.business_name ?? v.name}</h1>
              <StatusBadge status={v.status ?? v.verification_status} />
            </div>
          </div>
        </div>
        <div className="admin-page-header-actions">
          {(v.status === 'pending' || v.verification_status === 'pending') && (
            <>
              <button className="btn btn-success" onClick={() => { setVerifyAction('approve'); setVerifyOpen(true); }}>Approve</button>
              <button className="btn btn-danger" onClick={() => { setVerifyAction('reject'); setVerifyOpen(true); }}>Reject</button>
            </>
          )}
          {v.status === 'approved' && (
            <button className="btn btn-secondary" onClick={() => { setVerifyAction('suspend'); setVerifyOpen(true); }}>Suspend</button>
          )}
          {v.status === 'suspended' && (
            <button className="btn btn-success" onClick={() => { setVerifyAction('activate'); setVerifyOpen(true); }}>Activate</button>
          )}
        </div>
      </div>

      {/* Metric row */}
      <div className="admin-metric-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)', marginBottom: 20 }}>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Total Bookings</div>
          <div className="admin-metric-value">{analytics.total_bookings ?? 0}</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Total Revenue</div>
          <div className="admin-metric-value">{formatCurrency(analytics.total_revenue ?? 0)}</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Avg Rating</div>
          <div className="admin-metric-value">⭐ {analytics.avg_rating ? Number(analytics.avg_rating).toFixed(1) : '—'}</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Completion Rate</div>
          <div className="admin-metric-value">{analytics.completion_rate != null ? `${analytics.completion_rate}%` : '—'}</div>
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
              <Section title="">
                <Row label="Business Name" value={v.business_name} />
                <Row label="Email" value={v.email ?? v.user?.email} />
                <Row label="Phone" value={v.phone ?? v.user?.phone_number} />
                <Row label="City" value={v.city} />
                <Row label="State" value={v.state} />
                <Row label="Member Since" value={formatDate(v.created_at)} />
                <Row label="Last Active" value={timeAgo(v.updated_at)} />
              </Section>
            </div>
          </div>

          <div className="admin-card">
            <div className="admin-card-header"><div className="admin-card-title">Profile Details</div></div>
            <div className="admin-card-body">
              <Section title="">
                <Row label="Category" value={v.categories?.map(c => c.name).join(', ')} />
                <Row label="GST Number" value={v.gst_number ?? 'Not provided'} />
                <Row label="PAN Number" value={v.pan_number ?? 'Not provided'} />
                <Row label="Legal Name" value={v.legal_name ?? 'Not provided'} />
                <Row label="Priority Score" value={v.priority_score} />
                <Row label="Account Manager" value={v.assigned_account_manager_id ?? 'Unassigned'} />
              </Section>
            </div>
          </div>
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
                <th>Customer</th>
                <th>Status</th>
                <th>Amount</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {recentBookings.map((b) => (
                <tr key={b.id} style={{ cursor: 'pointer' }} onClick={() => navigate(`/admin/bookings/${b.id}`)}>
                  <td><code style={{ fontSize: 11 }}>{b.id?.slice(0, 8)}</code></td>
                  <td>{b.customer_name ?? b.user?.name ?? '—'}</td>
                  <td><StatusBadge status={b.status} /></td>
                  <td>{formatCurrency(b.total_amount)}</td>
                  <td>{formatDate(b.event_date ?? b.created_at)}</td>
                </tr>
              ))}
              {!recentBookings.length && (
                <tr><td colSpan={5} className="admin-table-empty">No recent bookings</td></tr>
              )}
            </tbody>
          </table>
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
    </div>
  );
}
