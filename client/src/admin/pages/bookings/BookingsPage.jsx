import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
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

export default function BookingsPage() {
  const navigate = useNavigate();
  const { page, perPage, setPage, reset } = usePagination();
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const debouncedSearch = useDebounce(search);

  const { data, isLoading } = useQuery({
    queryKey: ['bookings', { page, perPage, search: debouncedSearch, status }],
    queryFn: () => bookingsApi.list({ page, per_page: perPage, search: debouncedSearch || undefined, booking_status: status || undefined }),
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const pages = data?.pages ?? 1;

  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <h1>Booking Management</h1>
          <p>Track and manage all service bookings</p>
        </div>
      </div>

      <div className="admin-filters">
        <div className="admin-filters-search">
          <span style={{ color: 'var(--text-tertiary)' }}>⌕</span>
          <input
            placeholder="Search by customer, vendor, booking ID…"
            value={search}
            onChange={(e) => { setSearch(e.target.value); reset(); }}
          />
        </div>
        <select className="admin-filters-select" value={status} onChange={(e) => { setStatus(e.target.value); reset(); }}>
          {STATUS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </div>

      {isLoading ? (
        <SkeletonTable rows={10} cols={8} />
      ) : !items.length ? (
        <EmptyState title="No bookings found" />
      ) : (
        <div className="admin-table-wrapper">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Booking ID</th>
                <th>Customer</th>
                <th>Package</th>
                <th>Event Date</th>
                <th>Amount</th>
                <th>Status</th>
                <th>Payment</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((b) => (
                <tr key={b.id} style={{ cursor: 'pointer' }} onClick={() => navigate(`/admin/bookings/${b.id}`)}>
                  <td><code style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{b.booking_number ?? `${b.id?.slice(0, 8)}…`}</code></td>
                  {/* customer_* are filled by the backend for admin requests only */}
                  <td>
                    <div>{b.customer_name ?? '—'}</div>
                    {(b.customer_phone || b.customer_email) && (
                      <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                        {[b.customer_phone, b.customer_email].filter(Boolean).join(' · ')}
                      </div>
                    )}
                  </td>
                  <td style={{ maxWidth: 200 }}>
                    <span className="truncate">{b.package_name ?? '—'}</span>
                  </td>
                  {/* was: b.event_date — backend sends scheduled_date */}
                  <td>{formatDate(b.scheduled_date)}</td>
                  <td>{formatCurrency(b.total_amount)}</td>
                  {/* was: b.status — backend sends booking_status */}
                  <td><StatusBadge status={b.booking_status} /></td>
                  <td><StatusBadge status={b.payment_status} /></td>
                  <td>
                    <button className="btn btn-secondary btn-sm" onClick={(e) => { e.stopPropagation(); navigate(`/admin/bookings/${b.id}`); }}>
                      View
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <Pagination page={page} pages={pages} total={data?.cursor_mode ? null : total} hasNext={data?.has_next} perPage={perPage} onChange={setPage} />
        </div>
      )}
    </div>
  );
}
