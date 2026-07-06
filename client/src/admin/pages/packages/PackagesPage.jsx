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

const VERB_LABELS = {
  publish: { past: 'published', ing: 'publish' },
  unpublish: { past: 'unpublished', ing: 'unpublish' },
  archive: { past: 'archived', ing: 'archive' },
};

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

  const reportBulkResult = (result, verb) => {
    const { past, ing } = VERB_LABELS[verb];
    const noun = result.total_requested === 1 ? 'package' : 'packages';
    if (result.failed > 0 && result.succeeded === 0) {
      toast.error(`Failed to ${ing} ${result.failed === 1 ? 'the package' : `${result.failed} packages`}.`);
    } else if (result.failed > 0) {
      toast.warning(`${result.succeeded} ${noun} ${past}, ${result.failed} failed.`);
    } else {
      toast.success(`${result.total_requested === 1 ? 'Package' : 'Packages'} ${past}.`);
    }
    qc.invalidateQueries(['packages']);
    setSelected([]);
  };

  const publishMutation = useMutation({
    mutationFn: (ids) => bulkApi.publishPackages(ids),
    onSuccess: (result) => reportBulkResult(result, 'publish'),
    onError: () => toast.error('Failed to publish.'),
  });

  const unpublishMutation = useMutation({
    mutationFn: (ids) => bulkApi.unpublishPackages(ids),
    onSuccess: (result) => reportBulkResult(result, 'unpublish'),
    onError: () => toast.error('Failed to unpublish.'),
  });

  const archiveMutation = useMutation({
    mutationFn: (ids) => bulkApi.archivePackages(ids),
    onSuccess: (result) => reportBulkResult(result, 'archive'),
    onError: () => toast.error('Failed to archive.'),
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const pages = data?.pages ?? 1;

  const toggleAll = () => setSelected(s => s.length === items.length ? [] : items.map(i => i.id));
  const toggleItem = (id) => setSelected(s => s.includes(id) ? s.filter(x => x !== id) : [...s, id]);

  const handleBulk = () => {
    if (confirmBulk === 'publish') publishMutation.mutate(selected);
    else if (confirmBulk === 'unpublish') unpublishMutation.mutate(selected);
    else if (confirmBulk === 'archive') archiveMutation.mutate(selected);
    setConfirmBulk('');
  };

  const handleConfirmAction = () => {
    if (!confirmAction) return;
    const { type, packageId } = confirmAction;
    if (type === 'approve') approveMutation.mutate(packageId);
    else if (type === 'reject') rejectMutation.mutate(packageId);
    else if (type === 'publish') publishMutation.mutate([packageId]);
    else if (type === 'unpublish') unpublishMutation.mutate([packageId]);
    else if (type === 'archive') archiveMutation.mutate([packageId]);
    setConfirmAction(null);
  };

  const isRowActionPending =
    approveMutation.isPending || rejectMutation.isPending ||
    publishMutation.isPending || unpublishMutation.isPending || archiveMutation.isPending;

  const CONFIRM_ACTION_COPY = {
    approve: {
      title: 'Approve Package',
      message: (name) => `Approve "${name}"? It will become publicly visible on the app.`,
    },
    reject: {
      title: 'Reject Package',
      message: (name) => `Reject "${name}"? It will be returned to draft for the vendor to edit.`,
    },
    publish: {
      title: 'Publish Package',
      message: (name) => `Publish "${name}"? It will become publicly visible on the app.`,
    },
    unpublish: {
      title: 'Unpublish Package',
      message: (name) => `Unpublish "${name}"? It will be hidden from customers immediately.`,
    },
    archive: {
      title: 'Archive Package',
      message: (name) => `Archive "${name}"? It will be hidden from customers and vendor listings.`,
    },
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
            <button className="btn btn-danger btn-sm" onClick={() => setConfirmBulk('archive')}>Archive {selected.length}</button>
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
                    {/* PackageResponse sends category_id (UUID) — no nested category object */}
                    <div className="admin-user-email">{p.category_id ? <code style={{ fontSize: 11 }}>{p.category_id.slice(0, 8)}</code> : '—'}</div>
                  </td>
                  {/* PackageResponse sends vendor_id (UUID) — no nested vendor object */}
                  <td>{p.vendor_id ? <code style={{ fontSize: 11 }}>{p.vendor_id.slice(0, 8)}</code> : '—'}</td>
                  {/* was: p.price ?? p.base_price — backend sends base_price only */}
                  <td>{formatCurrency(p.base_price)}</td>
                  <td><StatusBadge status={p.status} /></td>
                  <td>{timeAgo(p.updated_at)}</td>
                  <td>
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                      {p.status === 'pending_review' && (
                        <>
                          <button
                            className="btn btn-success btn-sm"
                            disabled={isRowActionPending}
                            onClick={() => setConfirmAction({ type: 'approve', packageId: p.id, name: p.name })}
                          >
                            Approve
                          </button>
                          <button
                            className="btn btn-danger btn-sm"
                            disabled={isRowActionPending}
                            onClick={() => setConfirmAction({ type: 'reject', packageId: p.id, name: p.name })}
                          >
                            Reject
                          </button>
                        </>
                      )}
                      {(p.status === 'draft' || p.status === 'inactive' || p.status === 'archived') && (
                        <button
                          className="btn btn-success btn-sm"
                          disabled={isRowActionPending}
                          onClick={() => setConfirmAction({ type: 'publish', packageId: p.id, name: p.name })}
                        >
                          {p.status === 'archived' ? 'Restore' : 'Publish'}
                        </button>
                      )}
                      {p.status === 'active' && (
                        <button
                          className="btn btn-secondary btn-sm"
                          disabled={isRowActionPending}
                          onClick={() => setConfirmAction({ type: 'unpublish', packageId: p.id, name: p.name })}
                        >
                          Unpublish
                        </button>
                      )}
                      {(p.status === 'active' || p.status === 'inactive') && (
                        <button
                          className="btn btn-danger btn-sm"
                          disabled={isRowActionPending}
                          onClick={() => setConfirmAction({ type: 'archive', packageId: p.id, name: p.name })}
                        >
                          Archive
                        </button>
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
        title={confirmBulk ? `Bulk ${confirmBulk.charAt(0).toUpperCase()}${confirmBulk.slice(1)}` : ''}
        message={`${confirmBulk} ${selected.length} package(s)?`}
        loading={publishMutation.isPending || unpublishMutation.isPending || archiveMutation.isPending}
      />

      <ConfirmDialog
        open={!!confirmAction}
        onClose={() => setConfirmAction(null)}
        onConfirm={handleConfirmAction}
        title={confirmAction ? CONFIRM_ACTION_COPY[confirmAction.type].title : ''}
        message={confirmAction ? CONFIRM_ACTION_COPY[confirmAction.type].message(confirmAction.name) : ''}
        loading={isRowActionPending}
      />
    </div>
  );
}
