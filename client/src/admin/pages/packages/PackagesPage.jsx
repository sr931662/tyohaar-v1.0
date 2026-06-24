import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { packagesApi, bulkApi } from '../../api';
import { formatCurrency, timeAgo } from '../../utils/format';
import StatusBadge from '../../components/ui/StatusBadge';
import Pagination from '../../components/ui/Pagination';
import { SkeletonTable } from '../../components/ui/Skeleton';
import EmptyState from '../../components/ui/EmptyState';
import { ConfirmDialog } from '../../components/ui/Modal';
import { useDebounce } from '../../hooks/useDebounce';
import { usePagination } from '../../hooks/usePagination';

export default function PackagesPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { page, perPage, setPage, reset } = usePagination();
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [selected, setSelected] = useState([]);
  const [confirmBulk, setConfirmBulk] = useState('');
  const [confirmAction, setConfirmAction] = useState(null); // { type: 'approve'|'reject', packageId, name }
  const debouncedSearch = useDebounce(search);

  const { data, isLoading } = useQuery({
    queryKey: ['packages', { page, perPage, search: debouncedSearch, status }],
    queryFn: () => packagesApi.list({ page, per_page: perPage, search: debouncedSearch || undefined, status: status || undefined }),
  });

  const approveMutation = useMutation({
    mutationFn: (packageId) => packagesApi.approve(packageId),
    onSuccess: () => { toast.success('Package approved and published'); qc.invalidateQueries(['packages']); },
    onError: () => toast.error('Failed to approve package'),
  });

  const rejectMutation = useMutation({
    mutationFn: (packageId) => packagesApi.reject(packageId),
    onSuccess: () => { toast.success('Package rejected — returned to draft'); qc.invalidateQueries(['packages']); },
    onError: () => toast.error('Failed to reject package'),
  });

  const publishMutation = useMutation({
    mutationFn: (ids) => bulkApi.publishPackages(ids),
    onSuccess: () => { toast.success('Packages published'); qc.invalidateQueries(['packages']); setSelected([]); },
    onError: () => toast.error('Failed'),
  });

  const unpublishMutation = useMutation({
    mutationFn: (ids) => bulkApi.unpublishPackages(ids),
    onSuccess: () => { toast.success('Packages unpublished'); qc.invalidateQueries(['packages']); setSelected([]); },
    onError: () => toast.error('Failed'),
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const pages = data?.pages ?? 1;

  const toggleAll = () => setSelected(s => s.length === items.length ? [] : items.map(i => i.id));
  const toggleItem = (id) => setSelected(s => s.includes(id) ? s.filter(x => x !== id) : [...s, id]);

  const handleBulk = () => {
    if (confirmBulk === 'publish') publishMutation.mutate(selected);
    else if (confirmBulk === 'unpublish') unpublishMutation.mutate(selected);
    setConfirmBulk('');
  };

  const handleConfirmAction = () => {
    if (!confirmAction) return;
    if (confirmAction.type === 'approve') approveMutation.mutate(confirmAction.packageId);
    else rejectMutation.mutate(confirmAction.packageId);
    setConfirmAction(null);
  };

  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <h1>Package Management</h1>
          <p>Review pending submissions and manage all service packages</p>
        </div>
        <div className="admin-page-header-actions">
          <button className="btn btn-secondary" onClick={() => navigate('/admin/packages/categories')}>Categories</button>
        </div>
      </div>

      <div className="admin-filters">
        <div className="admin-filters-search">
          <span style={{ color: 'var(--text-tertiary)' }}>⌕</span>
          <input placeholder="Search packages…" value={search} onChange={(e) => { setSearch(e.target.value); reset(); }} />
        </div>
        <select className="admin-filters-select" value={status} onChange={(e) => { setStatus(e.target.value); reset(); }}>
          <option value="">All Statuses</option>
          <option value="pending_review">Pending Review</option>
          <option value="active">Active</option>
          <option value="draft">Draft</option>
          <option value="inactive">Inactive</option>
          <option value="archived">Archived</option>
        </select>
        {selected.length > 0 && (
          <>
            <button className="btn btn-success btn-sm" onClick={() => setConfirmBulk('publish')}>Publish {selected.length}</button>
            <button className="btn btn-secondary btn-sm" onClick={() => setConfirmBulk('unpublish')}>Unpublish {selected.length}</button>
            <button className="btn btn-ghost btn-sm" onClick={() => setSelected([])}>Clear</button>
          </>
        )}
      </div>

      {isLoading ? <SkeletonTable rows={8} cols={6} /> : !items.length ? (
        <EmptyState
          title={status === 'pending_review' ? 'No pending packages' : 'No packages found'}
          message={status === 'pending_review' ? 'No vendor packages are waiting for approval.' : undefined}
        />
      ) : (
        <div className="admin-table-wrapper">
          <table className="admin-table">
            <thead>
              <tr>
                <th><input type="checkbox" checked={selected.length === items.length && items.length > 0} onChange={toggleAll} /></th>
                <th>Package</th>
                <th>Vendor</th>
                <th>Price</th>
                <th>Status</th>
                <th>Updated</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((p) => (
                <tr key={p.id}>
                  <td><input type="checkbox" checked={selected.includes(p.id)} onChange={() => toggleItem(p.id)} /></td>
                  <td>
                    <div className="admin-user-name">{p.name}</div>
                    <div className="admin-user-email">{p.category?.name ?? '—'}</div>
                  </td>
                  <td>{p.vendor?.business_name ?? '—'}</td>
                  <td>{formatCurrency(p.price ?? p.base_price)}</td>
                  <td><StatusBadge status={p.status} /></td>
                  <td>{timeAgo(p.updated_at)}</td>
                  <td>
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                      {p.status === 'pending_review' && (
                        <>
                          <button
                            className="btn btn-success btn-sm"
                            disabled={approveMutation.isPending || rejectMutation.isPending}
                            onClick={() => setConfirmAction({ type: 'approve', packageId: p.id, name: p.name })}
                          >
                            Approve
                          </button>
                          <button
                            className="btn btn-danger btn-sm"
                            disabled={approveMutation.isPending || rejectMutation.isPending}
                            onClick={() => setConfirmAction({ type: 'reject', packageId: p.id, name: p.name })}
                          >
                            Reject
                          </button>
                        </>
                      )}
                      <button className="btn btn-secondary btn-sm" onClick={() => navigate(`/admin/packages/${p.id}`)}>View</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <Pagination page={page} pages={pages} total={total} perPage={perPage} onChange={setPage} />
        </div>
      )}

      <ConfirmDialog
        open={!!confirmBulk}
        onClose={() => setConfirmBulk('')}
        onConfirm={handleBulk}
        title={`Bulk ${confirmBulk}`}
        message={`${confirmBulk} ${selected.length} package(s)?`}
        loading={publishMutation.isPending || unpublishMutation.isPending}
      />

      <ConfirmDialog
        open={!!confirmAction}
        onClose={() => setConfirmAction(null)}
        onConfirm={handleConfirmAction}
        title={confirmAction?.type === 'approve' ? 'Approve Package' : 'Reject Package'}
        message={
          confirmAction?.type === 'approve'
            ? `Approve "${confirmAction?.name}"? It will become publicly visible on the app.`
            : `Reject "${confirmAction?.name}"? It will be returned to draft for the vendor to edit.`
        }
        loading={approveMutation.isPending || rejectMutation.isPending}
      />
    </div>
  );
}
