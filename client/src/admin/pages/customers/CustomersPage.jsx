import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { customersApi } from '../../api';
import { formatDate, timeAgo, initials, formatCurrency } from '../../utils/format';
import StatusBadge from '../../components/ui/StatusBadge';
import Pagination from '../../components/ui/Pagination';
import { SkeletonTable } from '../../components/ui/Skeleton';
import EmptyState from '../../components/ui/EmptyState';
import { useDebounce } from '../../hooks/useDebounce';
import { usePagination } from '../../hooks/usePagination';

export default function CustomersPage() {
  const navigate = useNavigate();
  const { page, perPage, setPage, reset } = usePagination();
  const [search, setSearch] = useState('');
  const debouncedSearch = useDebounce(search);

  const { data, isLoading } = useQuery({
    queryKey: ['customers', 'crm', { page, perPage, search: debouncedSearch }],
    queryFn: () => customersApi.crmList({ page, per_page: perPage, search: debouncedSearch || undefined }),
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const pages = data?.pages ?? 1;

  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <h1>Customer CRM</h1>
          <p>View and manage all customer accounts</p>
        </div>
      </div>

      <div className="admin-filters">
        <div className="admin-filters-search">
          <span style={{ color: 'var(--text-tertiary)' }}>⌕</span>
          <input
            placeholder="Search by name, email, phone…"
            value={search}
            onChange={(e) => { setSearch(e.target.value); reset(); }}
          />
        </div>
      </div>

      {isLoading ? (
        <SkeletonTable rows={8} cols={5} />
      ) : !items.length ? (
        <EmptyState title="No customers found" />
      ) : (
        <div className="admin-table-wrapper">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Customer</th>
                <th>Phone</th>
                <th>Bookings</th>
                <th>Total Spent</th>
                <th>Joined</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((c) => (
                <tr key={c.id} style={{ cursor: 'pointer' }} onClick={() => navigate(`/admin/customers/${c.id}`)}>
                  <td>
                    <div className="admin-user-row">
                      <div className="admin-avatar">{initials(c.name ?? c.full_name ?? 'U')}</div>
                      <div>
                        <div className="admin-user-name">{c.name ?? c.full_name ?? 'Unknown'}</div>
                        <div className="admin-user-email">{c.email}</div>
                      </div>
                    </div>
                  </td>
                  <td>{c.phone_number ?? '—'}</td>
                  <td>{c.total_bookings ?? 0}</td>
                  <td>{formatCurrency(c.total_spent ?? 0)}</td>
                  <td>{timeAgo(c.created_at)}</td>
                  <td>
                    <button className="btn btn-secondary btn-sm" onClick={(e) => { e.stopPropagation(); navigate(`/admin/customers/${c.id}`); }}>
                      360° View
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <Pagination page={page} pages={pages} total={total} perPage={perPage} onChange={setPage} />
        </div>
      )}
    </div>
  );
}
