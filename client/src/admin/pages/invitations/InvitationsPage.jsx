import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { invitationsApi } from '../../api';
import { useAdminAuth } from '../../context/AuthContext';
import { useDebounce } from '../../hooks/useDebounce';
import { usePagination } from '../../hooks/usePagination';
import { formatDate, formatDateTime } from '../../utils/format';
import EmptyState from '../../components/ui/EmptyState';
import Modal from '../../components/ui/Modal';
import Pagination from '../../components/ui/Pagination';
import { SkeletonTable } from '../../components/ui/Skeleton';

const PASS_STATE = {
  valid: ['Pass active', 'success'],
  not_yet_valid: ['Pass ready', 'info'],
  checked_in: ['Inside', 'success'],
  checked_out: ['Checked out', 'neutral'],
  used: ['Used', 'neutral'],
  expired: ['Expired', 'neutral'],
  revoked: ['Revoked', 'error'],
  event_cancelled: ['Event cancelled', 'error'],
  postponed: ['Postponed', 'warning'],
};

const RESULT = {
  checked_in: ['Checked in', 'success'],
  checked_out: ['Checked out', 'success'],
  valid: ['Valid', 'success'],
  already_checked_in: ['Already inside', 'warning'],
  already_used: ['Already used', 'warning'],
  not_checked_in: ['Not checked in', 'warning'],
  not_yet_valid: ['Not yet valid', 'warning'],
  party_size_exceeded: ['Too many people', 'warning'],
  invalid: ['Invalid code', 'error'],
  expired: ['Expired', 'error'],
  revoked: ['Revoked', 'error'],
  event_cancelled: ['Event cancelled', 'error'],
  denied: ['Denied', 'error'],
};

const HISTORY = {
  invited: 'Invitation created',
  invitation_opened: 'Guest opened the invitation',
  rsvp_changed: 'RSVP changed',
  checked_in: 'Checked in',
  checked_out: 'Checked out',
  details_updated: 'Details edited',
  shared: 'Shared',
  email_sent: 'Emailed',
  email_failed: 'Email failed',
  link_rotated: 'New link & pass issued',
  revoked: 'Revoked',
};

const label = (s) => (s ? s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()) : '—');

function Badge({ map, value }) {
  const [text, color] = map[value] ?? [label(value), 'info'];
  return (
    <span className={`badge badge-${color}`}>
      <span className="badge-dot" />
      {text}
    </span>
  );
}

const muted = { color: 'var(--text-tertiary)' };

// ── Invitations tab ───────────────────────────────────────────────────────────

function InvitationsTab({ canRevoke, canExport }) {
  const { page, perPage, setPage, reset } = usePagination();
  const [search, setSearch] = useState('');
  const q = useDebounce(search, 350);
  const [filters, setFilters] = useState({ pass_status: '', entry_status: '', rsvp_status: '', date_from: '', date_to: '' });
  const [sort, setSort] = useState('created_at:desc');
  const [selectedId, setSelectedId] = useState(null);
  const [exporting, setExporting] = useState(false);

  const [sortKey, order] = sort.split(':');
  const params = {
    page,
    per_page: perPage,
    q: q || undefined,
    sort: sortKey,
    order,
    ...Object.fromEntries(Object.entries(filters).filter(([, v]) => v)),
  };

  const { data, isLoading, isError } = useQuery({
    queryKey: ['admin-invitations', params],
    queryFn: () => invitationsApi.list(params),
  });

  const setFilter = (key) => (e) => { setFilters((f) => ({ ...f, [key]: e.target.value })); reset(); };

  const doExport = async () => {
    setExporting(true);
    try {
      const { page: _p, per_page: _pp, sort: _s, order: _o, ...exportParams } = params;
      const blob = await invitationsApi.exportCsv(exportParams);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `invitations-${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error('Export failed.');
    } finally {
      setExporting(false);
    }
  };

  const items = data?.items ?? [];

  return (
    <>
      <div className="admin-filters">
        <input
          className="admin-filters-search"
          placeholder="Search guest, phone, event or pass code"
          value={search}
          onChange={(e) => { setSearch(e.target.value); reset(); }}
          style={{ minWidth: 260 }}
        />
        <select className="admin-filters-select" value={filters.pass_status} onChange={setFilter('pass_status')}>
          <option value="">Any pass</option>
          <option value="active">Active</option>
          <option value="revoked">Revoked</option>
        </select>
        <select className="admin-filters-select" value={filters.entry_status} onChange={setFilter('entry_status')}>
          <option value="">Any arrival</option>
          <option value="not_arrived">Not arrived</option>
          <option value="checked_in">Inside</option>
          <option value="checked_out">Checked out</option>
        </select>
        <select className="admin-filters-select" value={filters.rsvp_status} onChange={setFilter('rsvp_status')}>
          <option value="">Any RSVP</option>
          <option value="pending">No reply</option>
          <option value="attending">Attending</option>
          <option value="maybe">Maybe</option>
          <option value="declined">Declined</option>
        </select>
        <input type="date" className="admin-filters-input" value={filters.date_from} onChange={setFilter('date_from')} title="Event from" />
        <input type="date" className="admin-filters-input" value={filters.date_to} onChange={setFilter('date_to')} title="Event to" />
        <select className="admin-filters-select" value={sort} onChange={(e) => { setSort(e.target.value); reset(); }}>
          <option value="created_at:desc">Newest invitations</option>
          <option value="celebration_date:asc">Event date ↑</option>
          <option value="celebration_date:desc">Event date ↓</option>
          <option value="name:asc">Guest A–Z</option>
          <option value="checked_in_at:desc">Latest arrivals</option>
        </select>
        {canExport && (
          <button className="btn btn-secondary btn-sm" onClick={doExport} disabled={exporting}>
            {exporting ? 'Exporting…' : 'Export CSV'}
          </button>
        )}
      </div>

      {isLoading ? <SkeletonTable rows={10} cols={7} /> : isError ? (
        <EmptyState title="Couldn't load invitations" message="Please try again." />
      ) : !items.length ? (
        <EmptyState title="No invitations found" />
      ) : (
        <div className="admin-table-wrapper">
          <table className="admin-table">
            <thead>
              <tr><th>Guest</th><th>Event</th><th>Event date</th><th>Pass</th><th>RSVP</th><th>Arrival</th><th>Invited</th></tr>
            </thead>
            <tbody>
              {items.map((r) => (
                <tr key={r.id} onClick={() => setSelectedId(r.id)} style={{ cursor: 'pointer' }}>
                  <td>
                    <div style={{ fontWeight: 600 }}>{r.name}</div>
                    <div style={{ fontSize: 12, ...muted }}>{r.phone || '—'}{r.plus_ones_allowed ? ` · +${r.plus_ones_allowed}` : ''}</div>
                  </td>
                  <td>{r.celebration_title}</td>
                  <td>{formatDate(r.celebration_date)}</td>
                  <td><Badge map={PASS_STATE} value={r.pass_state} /></td>
                  <td>{label(r.rsvp_status)}</td>
                  <td>{r.checked_in_at ? formatDateTime(r.checked_in_at) : <span style={muted}>{label(r.entry_status)}</span>}</td>
                  <td>{formatDate(r.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <Pagination page={page} pages={data?.pages ?? 1} total={data?.total} hasNext={data?.has_next} perPage={perPage} onChange={setPage} />
        </div>
      )}

      <InvitationDetailModal guestId={selectedId} onClose={() => setSelectedId(null)} canRevoke={canRevoke} />
    </>
  );
}

function InvitationDetailModal({ guestId, onClose, canRevoke }) {
  const queryClient = useQueryClient();
  const [confirming, setConfirming] = useState(false);
  const [reason, setReason] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['admin-invitation', guestId],
    queryFn: () => invitationsApi.get(guestId),
    enabled: !!guestId,
  });
  const { data: summary } = useQuery({
    queryKey: ['admin-invitation-summary', data?.invitation?.celebration_id],
    queryFn: () => invitationsApi.celebrationSummary(data.invitation.celebration_id),
    enabled: !!data?.invitation?.celebration_id,
  });

  const revoke = useMutation({
    mutationFn: () => invitationsApi.revoke(guestId, reason.trim()),
    onSuccess: () => {
      toast.success('Invitation revoked. Its link and pass no longer work.');
      setConfirming(false);
      setReason('');
      queryClient.invalidateQueries({ queryKey: ['admin-invitation', guestId] });
      queryClient.invalidateQueries({ queryKey: ['admin-invitations'] });
    },
    onError: (e) => toast.error(e?.response?.data?.error?.message ?? 'Could not revoke.'),
  });

  const inv = data?.invitation;
  const close = () => { setConfirming(false); setReason(''); onClose(); };

  return (
    <Modal open={!!guestId} onClose={close} title={inv ? inv.name : 'Invitation'} size="lg">
      {isLoading || !inv ? <SkeletonTable rows={4} cols={2} /> : (
        <div style={{ display: 'grid', gap: 18 }}>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
            <Badge map={PASS_STATE} value={inv.pass_state} />
            <span className="badge badge-info">RSVP: {label(inv.rsvp_status)}</span>
            <span className="badge badge-neutral">{label(inv.entry_status)}</span>
          </div>

          <dl style={{ display: 'grid', gridTemplateColumns: '160px 1fr', gap: '8px 16px', margin: 0 }}>
            <dt style={muted}>Event</dt><dd style={{ margin: 0 }}>{inv.celebration_title} · {formatDate(inv.celebration_date)} ({label(inv.celebration_status)})</dd>
            <dt style={muted}>Phone</dt><dd style={{ margin: 0 }}>{inv.phone || '—'}</dd>
            <dt style={muted}>Email</dt><dd style={{ margin: 0 }}>{inv.email || '—'}</dd>
            <dt style={muted}>Allowance</dt><dd style={{ margin: 0 }}>Guest{inv.plus_ones_allowed ? ` + ${inv.plus_ones_allowed}` : ' only'}</dd>
            <dt style={muted}>Checked in</dt><dd style={{ margin: 0 }}>{inv.checked_in_at ? formatDateTime(inv.checked_in_at) : '—'}</dd>
            {inv.revoked_at && (<><dt style={muted}>Revoked</dt><dd style={{ margin: 0 }}>{formatDateTime(inv.revoked_at)}{data.revoked_reason ? ` — ${data.revoked_reason}` : ''}</dd></>)}
          </dl>

          {summary && (
            <div>
              <h3 style={{ fontSize: 14, margin: '0 0 8px' }}>Event totals</h3>
              <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', fontSize: 13 }}>
                <span>Invited <b>{summary.active}</b></span>
                <span>Attending <b>{summary.rsvp_attending}</b></span>
                <span>Arrived <b>{summary.arrived_guests}</b> ({summary.arrived_people} people)</span>
                <span>Still expected <b>{summary.still_expected}</b></span>
                <span>Revoked <b>{summary.revoked}</b></span>
              </div>
            </div>
          )}

          <div>
            <h3 style={{ fontSize: 14, margin: '0 0 8px' }}>Audit trail</h3>
            {!data.history.length ? <p style={muted}>No history.</p> : (
              <table className="admin-table">
                <thead><tr><th>When</th><th>Event</th><th>By</th></tr></thead>
                <tbody>
                  {data.history.map((h) => (
                    <tr key={h.id}>
                      <td>{formatDateTime(h.occurred_at)}</td>
                      <td>
                        {HISTORY[h.event_type] ?? label(h.event_type)}
                        {h.new_status ? ` → ${label(h.new_status)}` : ''}
                        {h.details?.fields ? ` (${h.details.fields.join(', ')})` : ''}
                        {h.details?.channel ? ` via ${label(h.details.channel)}` : ''}
                        {h.details?.reason ? ` — ${h.details.reason}` : ''}
                      </td>
                      <td>{h.actor_label || label(h.actor_type)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div>
            <h3 style={{ fontSize: 14, margin: '0 0 8px' }}>Gate attempts</h3>
            {!data.entries.length ? <p style={muted}>No gate activity.</p> : (
              <table className="admin-table">
                <thead><tr><th>When</th><th>Action</th><th>Result</th><th>Operator</th></tr></thead>
                <tbody>
                  {data.entries.map((e) => (
                    <tr key={e.id}>
                      <td>{formatDateTime(e.occurred_at)}</td>
                      <td>{label(e.action)} ({e.method})</td>
                      <td><Badge map={RESULT} value={e.result} /></td>
                      <td>{e.operator_label || label(e.operator_type)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {canRevoke && inv.pass_status === 'active' && (
            confirming ? (
              <div style={{ display: 'grid', gap: 8 }}>
                <p style={{ margin: 0 }}>Revoking stops this guest&apos;s link and pass immediately. It can&apos;t be undone.</p>
                <input className="admin-filters-input" placeholder="Reason (recorded in the audit trail)" value={reason} maxLength={300}
                  onChange={(e) => setReason(e.target.value)} />
                <div style={{ display: 'flex', gap: 8 }}>
                  <button className="btn btn-secondary" onClick={() => setConfirming(false)}>Keep</button>
                  <button className="btn btn-danger" onClick={() => revoke.mutate()} disabled={revoke.isPending}>
                    {revoke.isPending ? 'Revoking…' : 'Revoke invitation'}
                  </button>
                </div>
              </div>
            ) : (
              <button className="btn btn-danger" style={{ justifySelf: 'start' }} onClick={() => setConfirming(true)}>Revoke invitation</button>
            )
          )}
        </div>
      )}
    </Modal>
  );
}

// ── Entry activity tab ────────────────────────────────────────────────────────

function EntryActivityTab() {
  const { page, perPage, setPage, reset } = usePagination();
  const [failedOnly, setFailedOnly] = useState(true);
  const [result, setResult] = useState('');
  const params = { page, per_page: perPage, failed_only: failedOnly || undefined, result: result || undefined };
  const { data, isLoading } = useQuery({
    queryKey: ['admin-entry-logs', params],
    queryFn: () => invitationsApi.entryLogs(params),
  });
  const items = data?.items ?? [];
  return (
    <>
      <div className="admin-filters">
        <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <input type="checkbox" checked={failedOnly} onChange={(e) => { setFailedOnly(e.target.checked); reset(); }} />
          Failed attempts only
        </label>
        <select className="admin-filters-select" value={result} onChange={(e) => { setResult(e.target.value); reset(); }}>
          <option value="">Any result</option>
          {Object.entries(RESULT).map(([k, [t]]) => <option key={k} value={k}>{t}</option>)}
        </select>
      </div>
      {isLoading ? <SkeletonTable rows={10} cols={6} /> : !items.length ? (
        <EmptyState title="No gate activity" />
      ) : (
        <div className="admin-table-wrapper">
          <table className="admin-table">
            <thead><tr><th>When</th><th>Guest</th><th>Action</th><th>Result</th><th>Party</th><th>Operator</th></tr></thead>
            <tbody>
              {items.map((e) => (
                <tr key={e.id}>
                  <td>{formatDateTime(e.occurred_at)}</td>
                  <td>{e.guest_name ?? <span style={muted}>Unknown code</span>}</td>
                  <td>{label(e.action)} <span style={muted}>({e.method})</span></td>
                  <td><Badge map={RESULT} value={e.result} /></td>
                  <td>{e.party_size ?? '—'}</td>
                  <td>{e.operator_label || label(e.operator_type)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <Pagination page={page} pages={data?.pages ?? 1} total={data?.total} hasNext={data?.has_next} perPage={perPage} onChange={setPage} />
        </div>
      )}
    </>
  );
}

// ── Policy tab ────────────────────────────────────────────────────────────────

const POLICY_FIELDS = [
  ['max_plus_ones', 'Max accompanying guests per pass', 'number'],
  ['entry_grace_minutes_before', 'Entry opens (minutes before start)', 'number'],
  ['entry_grace_minutes_after', 'Entry closes (minutes after end)', 'number'],
  ['max_invite_days_in_advance', 'Invite at most this many days ahead', 'number'],
  ['bulk_create_limit', 'Max guests per bulk invite', 'number'],
  ['gate_access_max_hours', 'Max gate-link validity (hours)', 'number'],
  ['allow_reentry', 'Allow re-entry after check-out', 'checkbox'],
  ['notify_host_on_check_in', 'Notify host when staff check a guest in', 'checkbox'],
];

function PolicyTab({ canEdit }) {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ['admin-invitation-policy'], queryFn: invitationsApi.getPolicy });
  const [draft, setDraft] = useState(null);
  const form = draft ?? data;
  const save = useMutation({
    mutationFn: () => invitationsApi.updatePolicy(form),
    onSuccess: (saved) => {
      toast.success('Policy saved.');
      queryClient.setQueryData(['admin-invitation-policy'], saved);
      setDraft(null);
    },
    onError: (e) => toast.error(e?.response?.data?.error?.message ?? 'Invalid policy values.'),
  });
  if (isLoading || !form) return <SkeletonTable rows={6} cols={2} />;
  return (
    <div style={{ maxWidth: 560, display: 'grid', gap: 12 }}>
      {!canEdit && <p style={muted}>Only super-admins can change the invitation policy.</p>}
      {POLICY_FIELDS.map(([key, text, type]) => (
        <label key={key} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
          <span>{text}</span>
          {type === 'checkbox' ? (
            <input type="checkbox" disabled={!canEdit} checked={!!form[key]}
              onChange={(e) => setDraft({ ...form, [key]: e.target.checked })} />
          ) : (
            <input type="number" min={0} className="admin-filters-input" style={{ width: 110 }} disabled={!canEdit} value={form[key]}
              onChange={(e) => setDraft({ ...form, [key]: e.target.value === '' ? '' : Number(e.target.value) })} />
          )}
        </label>
      ))}
      {canEdit && (
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-primary" disabled={!draft || save.isPending} onClick={() => save.mutate()}>
            {save.isPending ? 'Saving…' : 'Save policy'}
          </button>
          {draft && <button className="btn btn-secondary" onClick={() => setDraft(null)}>Discard</button>}
        </div>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function InvitationsPage() {
  const { admin, isSuperAdmin } = useAdminAuth();
  const [tab, setTab] = useState('invitations');
  // The server enforces these too; the UI just doesn't offer what would 403.
  const isFullAdmin = admin?.role === 'admin' || isSuperAdmin;

  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <h1>Guest Invitations</h1>
          <p>Invitations, gate activity and entry policy across all celebrations</p>
        </div>
      </div>
      <div className="admin-tabs">
        {[['invitations', 'Invitations'], ['activity', 'Gate activity'], ...(isFullAdmin ? [['policy', 'Policy']] : [])].map(([key, text]) => (
          <button key={key} className={`admin-tab${tab === key ? ' active' : ''}`} onClick={() => setTab(key)}>{text}</button>
        ))}
      </div>
      {tab === 'invitations' && <InvitationsTab canRevoke={isFullAdmin} canExport={isFullAdmin} />}
      {tab === 'activity' && <EntryActivityTab />}
      {tab === 'policy' && isFullAdmin && <PolicyTab canEdit={isSuperAdmin} />}
    </div>
  );
}
