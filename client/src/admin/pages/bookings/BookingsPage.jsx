import { useState } from 'react';
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { bookingsApi } from '../../api';
import { formatDate, formatCurrency, timeAgo } from '../../utils/format';
import StatusBadge from '../../components/ui/StatusBadge';
import Pagination from '../../components/ui/Pagination';
import { SkeletonTable } from '../../components/ui/Skeleton';
import EmptyState from '../../components/ui/EmptyState';
import { useDebounce } from '../../hooks/useDebounce';
import { usePagination } from '../../hooks/usePagination';

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'pending', label: 'Pending' },
  { value: 'confirmed', label: 'Confirmed' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'completed', label: 'Completed' },
  { value: 'cancelled', label: 'Cancelled' },
];

const PAYMENT_OPTIONS = [
  { value: '', label: 'Any Payment' },
  { value: 'pending', label: 'Unpaid' },
  { value: 'completed', label: 'Paid' },
  { value: 'failed', label: 'Failed' },
  { value: 'refunded', label: 'Refunded' },
];

/** "18:30:00" → "6:30 PM". */
function clock(t) {
  if (!t) return null;
  const [h, m] = String(t).split(':').map(Number);
  if (Number.isNaN(h)) return null;
  return `${((h + 11) % 12) + 1}:${String(m || 0).padStart(2, '0')} ${h >= 12 ? 'PM' : 'AM'}`;
}

const sub = { fontSize: 11, color: 'var(--text-secondary)' };

export default function BookingsPage() {
  const navigate = useNavigate();
  const { page, perPage, setPage, reset } = usePagination();
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [payment, setPayment] = useState('');
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const debouncedSearch = useDebounce(search);

  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ['bookings', { page, perPage, search: debouncedSearch, status, payment, from, to }],
    queryFn: () => bookingsApi.list({
      page,
      per_page: perPage,
      search: debouncedSearch || undefined,
      booking_status: status || undefined,
      payment_status: payment || undefined,
      from_date: from || undefined,
      to_date: to || undefined,
    }),
    placeholderData: keepPreviousData,
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const pages = data?.pages ?? 1;
  const filtered = Boolean(debouncedSearch || status || payment || from || to);
  const clearFilters = () => { setSearch(''); setStatus(''); setPayment(''); setFrom(''); setTo(''); reset(); };

  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <h1>Booking Management</h1>
          <p>Track and manage all service bookings</p>
        </div>
      </div>

      <div className="admin-filters" style={{ flexWrap: 'wrap' }}>
        <div className="admin-filters-search">
          <span style={{ color: 'var(--text-tertiary)' }}>⌕</span>
          <input
            placeholder="Search by booking no., customer name / email / phone, or vendor…"
            value={search}
            onChange={(e) => { setSearch(e.target.value); reset(); }}
          />
        </div>
        <select className="admin-filters-select" value={status} onChange={(e) => { setStatus(e.target.value); reset(); }} aria-label="Booking status">
          {STATUS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <select className="admin-filters-select" value={payment} onChange={(e) => { setPayment(e.target.value); reset(); }} aria-label="Payment status">
          {PAYMENT_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--text-secondary)' }}>
          Event from
          <input type="date" className="admin-filters-select" value={from} max={to || undefined} onChange={(e) => { setFrom(e.target.value); reset(); }} />
        </label>
        <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--text-secondary)' }}>
          to
          <input type="date" className="admin-filters-select" value={to} min={from || undefined} onChange={(e) => { setTo(e.target.value); reset(); }} />
        </label>
        {filtered && <button className="btn btn-ghost btn-sm" onClick={clearFilters}>Clear filters</button>}
      </div>

      {isLoading ? (
        <SkeletonTable rows={10} cols={9} />
      ) : isError ? (
        <div className="admin-empty">
          <div className="admin-empty-title">Couldn't load bookings</div>
          <button className="btn btn-secondary" style={{ marginTop: 12 }} onClick={() => refetch()}>Try again</button>
        </div>
      ) : !items.length ? (
        <EmptyState
          title={filtered ? 'No bookings match these filters' : 'No bookings yet'}
          action={filtered ? <button className="btn btn-secondary" onClick={clearFilters}>Clear filters</button> : undefined}
        />
      ) : (
        <div className="admin-table-wrapper" style={{ opacity: isFetching ? 0.7 : 1, transition: 'opacity .15s' }}>
          <table className="admin-table">
            <thead>
              <tr>
                <th>Booking</th>
                <th>Customer</th>
                <th>Package</th>
                <th>Vendor</th>
                <th>Event</th>
                <th>Amount</th>
                <th>Status</th>
                <th>Payment</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((b) => {
                // customer_* and vendor_name are filled by the backend for admin requests only.
                const who = b.customer_name ?? b.customer_email ?? b.customer_phone ?? 'Unknown customer';
                const contact = [b.customer_phone, b.customer_email].filter((x) => x && x !== who);
                const time = clock(b.scheduled_start_time);
                const paid = Number(b.amount_paid ?? 0);
                const due = Number(b.amount_due ?? 0);
                return (
                  <tr key={b.id} style={{ cursor: 'pointer' }} onClick={() => navigate(`/admin/bookings/${b.id}`)}>
                    <td>
                      <code style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{b.booking_number ?? `${b.id?.slice(0, 8)}…`}</code>
                      {b.created_at && <div style={sub} title={formatDate(b.created_at)}>Booked {timeAgo(b.created_at)}</div>}
                    </td>
                    <td>
                      <div>{who}</div>
                      {contact.length > 0 && <div style={sub}>{contact.join(' · ')}</div>}
                    </td>
                    <td style={{ maxWidth: 200 }}>
                      <span className="truncate">{b.package_name ?? '—'}</span>
                      {b.celebration_title && <div style={sub} className="truncate">{b.celebration_title}</div>}
                    </td>
                    <td style={{ maxWidth: 160 }}><span className="truncate">{b.vendor_name ?? '—'}</span></td>
                    <td>
                      {formatDate(b.scheduled_date)}
                      {time && <div style={sub}>{time}</div>}
                    </td>
                    <td>
                      {formatCurrency(b.total_amount)}
                      {paid > 0 && due > 0.009 && <div style={sub}>Paid {formatCurrency(paid)} · Due {formatCurrency(due)}</div>}
                    </td>
                    <td><StatusBadge status={b.booking_status} /></td>
                    <td><StatusBadge status={b.payment_status} /></td>
                    <td>
                      <button className="btn btn-secondary btn-sm" onClick={(e) => { e.stopPropagation(); navigate(`/admin/bookings/${b.id}`); }}>
                        View
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <Pagination page={page} pages={pages} total={data?.cursor_mode ? null : total} hasNext={data?.has_next} perPage={perPage} onChange={setPage} />
        </div>
      )}
    </div>
  );
}
