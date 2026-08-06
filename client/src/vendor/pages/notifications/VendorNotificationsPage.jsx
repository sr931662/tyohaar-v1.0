import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { vendorNotificationsApi, vendorBulkApi } from '../../api';
import { SkeletonCard } from '../../../admin/components/ui/Skeleton';
import EmptyState from '../../../admin/components/ui/EmptyState';
import Pagination from '../../../admin/components/ui/Pagination';
import { ConfirmDialog } from '../../../admin/components/ui/Modal';
import BulkActionBar from '../../../admin/components/ui/BulkActionBar';
import { useRowSelection } from '../../../admin/hooks/useRowSelection';
import { reportBulkResult } from '../../../admin/utils/bulkToast';
import { usePagination } from '../../../admin/hooks/usePagination';
import { timeAgo } from '../../../admin/utils/format';

const TYPE_ICON = {
  BOOKING: '📋',
  PAYMENT: '💳',
  REVIEW: '⭐',
  REFERRAL: '🎁',
  SYSTEM: '🔔',
};

export default function VendorNotificationsPage() {
  const qc = useQueryClient();
  const { page, perPage, setPage } = usePagination(1, 20);

  const { data, isLoading } = useQuery({
    queryKey: ['vendor-notifications', { page, perPage }],
    queryFn: () => vendorNotificationsApi.list({ page, per_page: perPage }),
  });

  const { data: unreadCount } = useQuery({
    queryKey: ['vendor-notifications-unread'],
    queryFn: () => vendorNotificationsApi.unreadCount(),
    refetchInterval: 60_000,
  });

  const invalidate = () => {
    qc.invalidateQueries(['vendor-notifications']);
    qc.invalidateQueries(['vendor-notifications-unread']);
  };

  const markReadMutation = useMutation({
    mutationFn: (id) => vendorNotificationsApi.markRead(id),
    onSuccess: invalidate,
    onError: () => toast.error('Failed to mark as read'),
  });

  const markAllReadMutation = useMutation({
    mutationFn: () => vendorNotificationsApi.markAllRead(),
    onSuccess: () => { toast.success('All notifications marked as read'); invalidate(); },
    onError: () => toast.error('Failed to mark all as read'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id) => vendorNotificationsApi.remove(id),
    onSuccess: invalidate,
    onError: () => toast.error('Failed to delete notification'),
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const pages = data?.pages ?? 1;
  const unread = typeof unreadCount === 'number' ? unreadCount : unreadCount?.count ?? 0;

  const { selected, toggleItem, clear } = useRowSelection(items, [page, perPage]);
  const [confirmBulkDelete, setConfirmBulkDelete] = useState(false);

  const bulkDeleteMutation = useMutation({
    mutationFn: (ids) => vendorBulkApi.deleteNotifications(ids),
    onSuccess: (result) => reportBulkResult({
      result,
      verbPast: 'deleted',
      verbIng: 'delete',
      nounSingular: 'notification',
      nounPlural: 'notifications',
      onDone: () => { invalidate(); clear(); setConfirmBulkDelete(false); },
    }),
    onError: () => toast.error('Failed to delete notifications.'),
  });

  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <h1 style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            Notifications
            {unread > 0 && (
              <span style={{
                display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                minWidth: 22, height: 22, borderRadius: 99, padding: '0 6px',
                background: '#ef4444', color: 'white', fontSize: 11, fontWeight: 700,
              }}>
                {unread > 99 ? '99+' : unread}
              </span>
            )}
          </h1>
          <p style={{ color: 'var(--text-secondary)' }}>Your activity and alerts</p>
        </div>
        {unread > 0 && (
          <div className="admin-page-header-actions">
            <button
              className="btn btn-secondary"
              onClick={() => markAllReadMutation.mutate()}
              disabled={markAllReadMutation.isPending}
            >
              Mark All Read
            </button>
          </div>
        )}
      </div>

      {isLoading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {[0, 1, 2, 3, 4].map((i) => <SkeletonCard key={i} height={72} />)}
        </div>
      ) : !items.length ? (
        <EmptyState
          title="All caught up!"
          description="You have no notifications right now."
          icon="🔔"
        />
      ) : (
        <>
          <BulkActionBar count={selected.length} onClear={clear}>
            <button className="btn btn-danger btn-sm" onClick={() => setConfirmBulkDelete(true)}>Delete</button>
          </BulkActionBar>
          <div className="admin-card" style={{ overflow: 'hidden' }}>
            {items.map((n, idx) => (
              <div
                key={n.id}
                style={{
                  display: 'flex', alignItems: 'flex-start', gap: 14,
                  padding: '14px 20px',
                  borderBottom: idx < items.length - 1 ? '1px solid var(--border-subtle)' : 'none',
                  background: !n.is_read ? 'rgba(var(--brand-rgb, 99,102,241), 0.04)' : 'transparent',
                  transition: 'background 0.2s',
                }}
              >
                <input
                  type="checkbox"
                  checked={selected.includes(n.id)}
                  onChange={() => toggleItem(n.id)}
                  style={{ marginTop: 8, flexShrink: 0, width: 15, height: 15, cursor: 'pointer' }}
                />
                <div style={{
                  fontSize: 22, width: 36, height: 36, borderRadius: '50%',
                  background: 'var(--bg-base)', display: 'flex', alignItems: 'center',
                  justifyContent: 'center', flexShrink: 0,
                }}>
                  {TYPE_ICON[n.notification_type] ?? '🔔'}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8, justifyContent: 'space-between' }}>
                    <div>
                      {!n.is_read && (
                        <span style={{
                          display: 'inline-block', width: 7, height: 7, borderRadius: '50%',
                          background: '#3b82f6', marginRight: 6, verticalAlign: 'middle',
                        }} />
                      )}
                      <span style={{ fontSize: 14, fontWeight: n.is_read ? 400 : 600, color: 'var(--text-primary)' }}>
                        {n.title ?? n.notification_type}
                      </span>
                    </div>
                    <span style={{ fontSize: 11, color: 'var(--text-tertiary)', whiteSpace: 'nowrap', marginLeft: 8 }}>
                      {n.created_at ? timeAgo(n.created_at) : ''}
                    </span>
                  </div>
                  {n.body && (
                    <p style={{ margin: '4px 0 0', fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                      {n.body}
                    </p>
                  )}
                </div>
                <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                  {!n.is_read && (
                    <button
                      className="btn btn-ghost btn-sm"
                      title="Mark as read"
                      onClick={() => markReadMutation.mutate(n.id)}
                      disabled={markReadMutation.isPending}
                      style={{ fontSize: 13, padding: '3px 8px' }}
                    >
                      ✓
                    </button>
                  )}
                  <button
                    className="btn btn-ghost btn-sm"
                    title="Delete"
                    onClick={() => deleteMutation.mutate(n.id)}
                    disabled={deleteMutation.isPending}
                    style={{ fontSize: 13, padding: '3px 8px', color: '#ef4444' }}
                  >
                    ✕
                  </button>
                </div>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 16 }}>
            <Pagination page={page} pages={pages} total={total} perPage={perPage} onPageChange={setPage} />
          </div>
        </>
      )}

      <ConfirmDialog
        open={confirmBulkDelete}
        onClose={() => setConfirmBulkDelete(false)}
        onConfirm={() => bulkDeleteMutation.mutate(selected)}
        title="Delete Notifications"
        message={`Delete ${selected.length} notification${selected.length === 1 ? '' : 's'}? This cannot be undone.`}
        danger
        loading={bulkDeleteMutation.isPending}
      />
    </div>
  );
}
