import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { feedbackApi } from '../../api';
import { formatDateTime } from '../../utils/format';
import Pagination from '../../components/ui/Pagination';
import { SkeletonTable } from '../../components/ui/Skeleton';
import EmptyState from '../../components/ui/EmptyState';
import { usePagination } from '../../hooks/usePagination';

const CATEGORY_LABELS = {
  general: 'General',
  bug_report: 'Bug Report',
  feature_request: 'Feature Request',
  vendor_experience: 'Vendor Experience',
  app_experience: 'App Experience',
  other: 'Other',
};

function Stars({ rating }) {
  return (
    <span style={{ color: 'var(--saffron, #f59e0b)', letterSpacing: 1 }}>
      {'★'.repeat(rating)}
      <span style={{ color: 'var(--text-tertiary)' }}>{'★'.repeat(5 - rating)}</span>
    </span>
  );
}

export default function FeedbackPage() {
  const { page, perPage, setPage, reset } = usePagination();
  const [category, setCategory] = useState('');
  const [rating, setRating] = useState('');
  const [reviewedOnly, setReviewedOnly] = useState('');
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['feedback', { page, perPage, category, rating, reviewedOnly }],
    queryFn: () =>
      feedbackApi.listAll({
        page,
        per_page: perPage,
        category: category || undefined,
        rating: rating || undefined,
        is_reviewed: reviewedOnly === '' ? undefined : reviewedOnly === 'true',
      }),
  });

  const reviewMutation = useMutation({
    mutationFn: (feedbackId) => feedbackApi.markReviewed(feedbackId),
    onSuccess: () => {
      toast.success('Marked as reviewed.');
      queryClient.invalidateQueries({ queryKey: ['feedback'] });
    },
    onError: () => toast.error('Could not update feedback.'),
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const pages = data?.pages ?? 1;

  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <h1>Feedback</h1>
          <p>Customer app feedback and ratings</p>
        </div>
      </div>

      <div className="admin-filters">
        <select className="admin-filters-select" value={category} onChange={(e) => { setCategory(e.target.value); reset(); }}>
          <option value="">All Categories</option>
          {Object.entries(CATEGORY_LABELS).map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
        <select className="admin-filters-select" value={rating} onChange={(e) => { setRating(e.target.value); reset(); }}>
          <option value="">All Ratings</option>
          {[5, 4, 3, 2, 1].map((r) => (
            <option key={r} value={r}>{r} star{r > 1 ? 's' : ''}</option>
          ))}
        </select>
        <select className="admin-filters-select" value={reviewedOnly} onChange={(e) => { setReviewedOnly(e.target.value); reset(); }}>
          <option value="">All</option>
          <option value="false">Unreviewed</option>
          <option value="true">Reviewed</option>
        </select>
      </div>

      {isLoading ? <SkeletonTable rows={10} cols={6} /> : !items.length ? (
        <EmptyState title="No feedback found" />
      ) : (
        <div className="admin-table-wrapper">
          <table className="admin-table">
            <thead>
              <tr><th>Customer</th><th>Rating</th><th>Category</th><th>Comments</th><th>Submitted</th><th>Actions</th></tr>
            </thead>
            <tbody>
              {items.map((f) => (
                <tr key={f.id}>
                  <td><code style={{ fontSize: 11 }}>{f.customer_id?.slice(0, 8)}</code></td>
                  <td><Stars rating={f.rating} /></td>
                  <td>{CATEGORY_LABELS[f.category] ?? f.category}</td>
                  <td style={{ maxWidth: 320, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {f.comments || <span style={{ color: 'var(--text-tertiary)' }}>—</span>}
                  </td>
                  <td>{formatDateTime(f.created_at)}</td>
                  <td>
                    {f.is_reviewed ? (
                      <span style={{ color: 'var(--text-tertiary)' }}>Reviewed</span>
                    ) : (
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => reviewMutation.mutate(f.id)}
                        disabled={reviewMutation.isPending}
                      >
                        Mark Reviewed
                      </button>
                    )}
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
