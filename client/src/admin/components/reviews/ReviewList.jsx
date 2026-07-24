import { useState } from 'react';
import StarRating from '../ui/StarRating';
import { formatDate } from '../../utils/format';

const STATUS_COLORS = {
  pending: '#f59e0b',
  approved: '#22c55e',
  rejected: '#ef4444',
  flagged: '#f97316',
  hidden: 'var(--text-tertiary)',
};

/**
 * Shared review list with optional moderation actions and delete —
 * used for both package-level and package-item-level reviews, in
 * admin (moderation) and vendor (read-only) contexts.
 */
export default function ReviewList({ reviews, onModerate, onDelete, canModerate = true }) {
  const [busyId, setBusyId] = useState(null);

  if (!reviews.length) {
    return <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>No reviews yet.</p>;
  }

  const handleModerate = async (reviewId, status) => {
    if (!onModerate) return;
    setBusyId(reviewId);
    try {
      await onModerate(reviewId, status);
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {reviews.map((review) => (
        <div key={review.id} className="admin-card" style={{ padding: 16 }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
            <div>
              <StarRating rating={review.rating ?? 0} />
              {review.title && (
                <div style={{ fontWeight: 600, fontSize: 14, marginTop: 6, color: 'var(--text-primary)' }}>
                  {review.title}
                </div>
              )}
              <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginTop: 2 }}>
                {review.created_at ? formatDate(review.created_at) : ''}
              </div>
            </div>
            <span
              style={{
                fontSize: 11,
                fontWeight: 700,
                textTransform: 'uppercase',
                color: STATUS_COLORS[review.moderation_status] ?? 'var(--text-tertiary)',
              }}
            >
              {review.moderation_status}
            </span>
          </div>
          {review.body && (
            <p style={{ margin: '10px 0 0', fontSize: 13.5, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
              {review.body}
            </p>
          )}
          {(canModerate && onModerate) || onDelete ? (
            <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
              {canModerate && onModerate && (
                <>
                  <button
                    className="btn btn-success"
                    disabled={busyId === review.id}
                    onClick={() => handleModerate(review.id, 'approved')}
                  >
                    Approve
                  </button>
                  <button
                    className="btn btn-secondary"
                    disabled={busyId === review.id}
                    onClick={() => handleModerate(review.id, 'rejected')}
                  >
                    Reject
                  </button>
                  <button
                    className="btn btn-secondary"
                    disabled={busyId === review.id}
                    onClick={() => handleModerate(review.id, 'hidden')}
                  >
                    Hide
                  </button>
                </>
              )}
              {onDelete && (
                <button className="btn btn-danger" onClick={() => onDelete(review.id)}>
                  Delete
                </button>
              )}
            </div>
          ) : null}
        </div>
      ))}
    </div>
  );
}
