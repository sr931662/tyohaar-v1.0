import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { vendorsApi, bulkApi } from '../../api';
import { formatDate, timeAgo, initials } from '../../utils/format';
import StatusBadge from '../../components/ui/StatusBadge';
import Pagination from '../../components/ui/Pagination';
import { SkeletonTable } from '../../components/ui/Skeleton';
import EmptyState from '../../components/ui/EmptyState';
import { ConfirmDialog } from '../../components/ui/Modal';
import { useDebounce } from '../../hooks/useDebounce';
import { usePagination } from '../../hooks/usePagination';

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'pending', label: 'Pending' },
  { value: 'approved', label: 'Approved' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'suspended', label: 'Suspended' },
];

export default function VendorsPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { page, perPage, setPage, reset } = usePagination();

  const [search, setSearch] = useState('');
  const debouncedSearch = useDebounce(search);
  const [status, setStatus] = useState('');
  const [selected, setSelected] = useState([]);
  const [bulkAction, setBulkAction] = useState('');
  const [confirmOpen, setConfirmOpen] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['vendors', 'crm', { page, perPage, search: debouncedSearch, status }],
    queryFn: () => vendorsApi.crmList({ page, per_page: perPage, search: debouncedSearch || undefined, status: status || undefined }),
  });

  const approveMutation = useMutation({
    mutationFn: (ids) => bulkApi.approveVendors(ids),
    onSuccess: () => { toast.success('Vendors approved'); qc.invalidateQueries(['vendors']); setSelected([]); },
    onError: () => toast.error('Bulk approve failed'),
  });

  const rejectMutation = useMutation({
    mutationFn: (ids) => bulkApi.rejectVendors(ids),
    onSuccess: () => { toast.success('Vendors rejected'); qc.invalidateQueries(['vendors']); setSelected([]); },
    onError: () => toast.error('Bulk reject failed'),
  });

  const suspendMutation = useMutation({
    mutationFn: (ids) => bulkApi.suspendVendors(ids),
    onSuccess: () => { toast.success('Vendors suspended'); qc.invalidateQueries(['vendors']); setSelected([]); },
    onError: () => toast.error('Bulk suspend failed'),
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const pages = data?.pages ?? 1;

  const handleBulkAction = () => {
    if (!selected.length) return;
    if (bulkAction === 'approve') approveMutation.mutate(selected);
    else if (bulkAction === 'reject') rejectMutation.mutate(selected);
    else if (bulkAction === 'suspend') suspendMutation.mutate(selected);
    setConfirmOpen(false);
  };

  const toggleSelect = (id) => {
    setSelected((s) => s.includes(id) ? s.filter((x) => x !== id) : [...s, id]);
  };

  const toggleAll = () => {
    setSelected((s) => s.length === items.length ? [] : items.map((v) => v.id));
  };

  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <h1>Vendor CRM</h1>
          <p>Manage vendor profiles, verification, and performance</p>
        </div>
      </div>

      {/* Filters */}
      <div className="admin-filters">
        <div className="admin-filters-search">
          <span style={{ color: 'var(--text-tertiary)' }}>⌕</span>
          <input
            placeholder="Search vendors by name, email, city…"
            value={search}
            onChange={(e) => { setSearch(e.target.value); reset(); }}
          />
        </div>
        <select
          className="admin-filters-select"
          value={status}
          onChange={(e) => { setStatus(e.target.value); reset(); }}
        >
          {STATUS_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>

        {selected.length > 0 && (
          <>
            <select
              className="admin-filters-select"
              value={bulkAction}
              onChange={(e) => setBulkAction(e.target.value)}
            >
              <option value="">Bulk action…</option>
              <option value="approve">Approve</option>
              <option value="reject">Reject</option>
              <option value="suspend">Suspend</option>
            </select>
            <button
              className="btn btn-primary btn-sm"
              disabled={!bulkAction}
              onClick={() => setConfirmOpen(true)}
            >
              Apply to {selected.length}
            </button>
            <button className="btn btn-ghost btn-sm" onClick={() => setSelected([])}>Clear</button>
          </>
        )}
      </div>

      {/* Table */}
      {isLoading ? (
        <SkeletonTable rows={8} cols={6} />
      ) : !items.length ? (
        <EmptyState title="No vendors found" message="Try changing your search or filters." />
      ) : (
        <div className="admin-table-wrapper">
          <table className="admin-table">
            <thead>
              <tr>
                <th style={{ width: 40 }}>
                  <input type="checkbox" checked={selected.length === items.length && items.length > 0} onChange={toggleAll} />
                </th>
                <th>Vendor</th>
                <th>City</th>
                <th>Status</th>
                <th>Rating</th>
                <th>Joined</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((v) => (
                <tr key={v.id}>
                  <td>
                    <input type="checkbox" checked={selected.includes(v.id)} onChange={() => toggleSelect(v.id)} />
                  </td>
                  <td>
                    <div className="admin-user-row">
                      <div className="admin-avatar">
                        {v.logo_url ? (
                          <img src={v.logo_url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: '50%' }} />
                        ) : (
                          initials(v.business_name ?? v.name ?? 'V')
                        )}
                      </div>
                      <div>
                        <div className="admin-user-name">{v.business_name ?? v.name}</div>
                        <div className="admin-user-email">{v.email ?? v.user?.email}</div>
                      </div>
                    </div>
                  </td>
                  <td><span className="text-secondary">{v.city ?? '—'}</span></td>
                  <td><StatusBadge status={v.status ?? v.verification_status} /></td>
                  <td>
                    {v.avg_rating != null ? (
                      <span>⭐ {Number(v.avg_rating).toFixed(1)}</span>
                    ) : '—'}
                  </td>
                  <td><span className="text-secondary">{timeAgo(v.created_at)}</span></td>
                  <td>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => navigate(`/admin/vendors/${v.id}`)}
                    >
                      View
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <Pagination page={page} pages={pages} total={total} perPage={perPage} onChange={setPage} />
        </div>
      )}

      <ConfirmDialog
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        onConfirm={handleBulkAction}
        title={`Bulk ${bulkAction}`}
        message={`Are you sure you want to ${bulkAction} ${selected.length} vendor(s)?`}
        danger={bulkAction === 'reject' || bulkAction === 'suspend'}
        loading={approveMutation.isPending || rejectMutation.isPending || suspendMutation.isPending}
      />
    </div>
  );
}
