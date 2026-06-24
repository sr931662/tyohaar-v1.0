import { useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { mediaApi } from '../../api';
import { timeAgo } from '../../utils/format';
import StatusBadge from '../../components/ui/StatusBadge';
import { SkeletonTable } from '../../components/ui/Skeleton';
import EmptyState from '../../components/ui/EmptyState';

export default function MediaPage() {
  const qc = useQueryClient();

  const {
    data,
    isLoading,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteQuery({
    queryKey: ['media', 'pending-moderation'],
    queryFn: ({ pageParam = null }) =>
      mediaApi.listPendingModeration({ cursor: pageParam, limit: 20 }),
    getNextPageParam: (lastPage) => lastPage?.next_cursor ?? undefined,
  });

  const moderateMutation = useMutation({
    mutationFn: ({ imageId, approved }) => mediaApi.moderateImage(imageId, approved),
    onSuccess: (_, { approved }) => {
      toast.success(approved ? 'Image approved' : 'Image rejected');
      qc.invalidateQueries(['media', 'pending-moderation']);
    },
    onError: () => toast.error('Moderation failed'),
  });

  const items = data?.pages.flatMap((p) => p?.items ?? []) ?? [];

  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <h1>Media Library</h1>
          <p>Review and moderate uploaded images pending content review</p>
        </div>
      </div>

      {isLoading ? (
        <SkeletonTable rows={8} cols={6} />
      ) : !items.length ? (
        <EmptyState
          title="No pending images"
          message="All uploads have been reviewed. Check back later."
        />
      ) : (
        <div className="admin-table-wrapper">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Preview</th>
                <th>Entity</th>
                <th>Owner</th>
                <th>Moderation</th>
                <th>Uploaded</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((img) => (
                <tr key={img.id}>
                  <td>
                    {img.url ? (
                      <img
                        src={img.url}
                        alt=""
                        style={{ width: 72, height: 52, objectFit: 'cover', borderRadius: 6, display: 'block' }}
                      />
                    ) : (
                      <div
                        style={{
                          width: 72, height: 52,
                          background: 'var(--bg-base)',
                          borderRadius: 6,
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          fontSize: 22, color: 'var(--text-tertiary)',
                        }}
                      >
                        🖼️
                      </div>
                    )}
                  </td>
                  <td>
                    <div className="text-sm font-medium" style={{ textTransform: 'capitalize' }}>
                      {img.entity_type?.replace(/_/g, ' ') ?? '—'}
                    </div>
                    {img.entity_id && (
                      <div className="text-sm text-tertiary">{img.entity_id.slice(0, 8)}…</div>
                    )}
                  </td>
                  <td>
                    <div className="text-sm text-secondary">
                      {img.owner_id ? img.owner_id.slice(0, 8) + '…' : '—'}
                    </div>
                    <div className="text-sm text-tertiary" style={{ textTransform: 'capitalize' }}>
                      {img.owner_type ?? ''}
                    </div>
                  </td>
                  <td>
                    <StatusBadge status={img.moderation_status ?? 'pending'} />
                  </td>
                  <td className="text-secondary text-sm">{timeAgo(img.created_at)}</td>
                  <td>
                    <div style={{ display: 'flex', gap: 6 }}>
                      <button
                        className="btn btn-success btn-sm"
                        disabled={moderateMutation.isPending}
                        onClick={() => moderateMutation.mutate({ imageId: img.id, approved: true })}
                      >
                        Approve
                      </button>
                      <button
                        className="btn btn-danger btn-sm"
                        disabled={moderateMutation.isPending}
                        onClick={() => moderateMutation.mutate({ imageId: img.id, approved: false })}
                      >
                        Reject
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {hasNextPage && (
            <div style={{ padding: '12px 16px', borderTop: '1px solid var(--border-subtle)', textAlign: 'center' }}>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => fetchNextPage()}
                disabled={isFetchingNextPage}
              >
                {isFetchingNextPage ? 'Loading…' : 'Load more'}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
