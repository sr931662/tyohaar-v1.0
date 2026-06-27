import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { vendorBookingsApi } from '../../api';
import StatusBadge from '../../../admin/components/ui/StatusBadge';
import { SkeletonTable } from '../../../admin/components/ui/Skeleton';
import EmptyState from '../../../admin/components/ui/EmptyState';
import Pagination from '../../../admin/components/ui/Pagination';
import { useDebounce } from '../../../admin/hooks/useDebounce';
import { usePagination } from '../../../admin/hooks/usePagination';
import { formatDate, formatCurrency } from '../../../admin/utils/format';

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'pending', label: 'Pending' },
  { value: 'confirmed', label: 'Confirmed' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'completed', label: 'Completed' },
  { value: 'cancelled', label: 'Cancelled' },
];

export default function VendorBookingsPage() {
  const navigate = useNavigate();
  const { page, perPage, setPage, reset } = usePagination();
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const debouncedSearch = useDebounce(search);

  const { data, isLoading } = useQuery({
    queryKey: ['vendor-bookings', { page, perPage, search: debouncedSearch, status }],
    queryFn: () => vendorBookingsApi.list({
      page,
      per_page: perPage,
      search: debouncedSearch || undefined,
      status: status || undefined,
    }),
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const pages = data?.pages ?? 1;

  const handleSearchChange = (v) => { setSearch(v); reset(); };
  const handleStatusChange = (v) => { setStatus(v); reset(); };

  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <h1>My Bookings</h1>
          <p style={{ color: 'var(--text-secondary)' }}>Track service requests assigned to you</p>
        </div>
      </div>

      <div className="admin-filters">
        <div className="admin-filters-search">
          <span style={{ color: 'var(--text-tertiary)' }}>⌕</span>
          <input
            className="admin-input"
            placeholder="Search by booking ID or customer name…"
            value={search}
            onChange={(e) => handleSearchChange(e.target.value)}
            style={{ border: 'none', background: 'transparent', outline: 'none', flex: 1, fontSize: 14 }}
          />
        </div>
        <select
          className="admin-filters-select"
          value={status}
          onChange={(e) => handleStatusChange(e.target.value)}
        >
          {STATUS_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      {isLoading ? (
        <SkeletonTable rows={6} cols={6} />
      ) : !items.length ? (
        <EmptyState
          title="No bookings yet"
          description="Bookings assigned to you will appear here."
          icon="📋"
        />
      ) : (
        <>
          <div className="admin-table-wrapper">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Booking</th>
                  <th>Scheduled Date</th>
                  <th>Package</th>
                  <th>Amount</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((b) => (
                  <tr key={b.id} style={{ cursor: 'pointer' }} onClick={() => navigate(`/vendor/bookings/${b.id}`)}>
                    <td>
                      <div className="admin-user-name" style={{ fontFamily: 'monospace', fontSize: 13 }}>
                        {b.booking_number ?? b.id?.slice(0, 8)}
                      </div>
                      <div className="admin-user-email">
                        {b.customer_name ?? b.customer?.name ?? '—'}
                      </div>
                    </td>
                    <td style={{ fontSize: 13 }}>
                      {b.scheduled_date ? formatDate(b.scheduled_date) : '—'}
                      {b.scheduled_start_time && (
                        <div style={{ color: 'var(--text-tertiary)', fontSize: 12 }}>
                          {b.scheduled_start_time}
                          {b.scheduled_end_time ? ` – ${b.scheduled_end_time}` : ''}
                        </div>
                      )}
                    </td>
                    <td style={{ fontSize: 13, color: 'var(--text-secondary)', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {b.package?.name ?? b.package_name ?? '—'}
                    </td>
                    <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                      {formatCurrency(b.total_amount ?? b.amount ?? 0)}
                    </td>
                    <td>
                      <StatusBadge status={b.status} />
                    </td>
                    <td onClick={(e) => e.stopPropagation()}>
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => navigate(`/vendor/bookings/${b.id}`)}
                      >
                        View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination page={page} pages={pages} total={total} perPage={perPage} onPageChange={setPage} />
        </>
      )}
    </div>
  );
}
