import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { vendorProfileApi } from '../../api';
import { SkeletonTable } from '../../../admin/components/ui/Skeleton';
import EmptyState from '../../../admin/components/ui/EmptyState';
import Pagination from '../../../admin/components/ui/Pagination';
import StarRating from '../../../admin/components/ui/StarRating';
import RatingSummary from '../../../admin/components/ui/RatingSummary';
import { usePagination } from '../../../admin/hooks/usePagination';
import { formatDate } from '../../../admin/utils/format';

export default function VendorReviewsPage() {
  const { page, perPage, setPage } = usePagination();

  const { data: vendor } = useQuery({
    queryKey: ['vendor', 'me'],
    queryFn: () => vendorProfileApi.getMe(),
  });

  const vendorId = vendor?.id;

  const { data, isLoading } = useQuery({
    queryKey: ['vendor-reviews', vendorId, { page, perPage }],
    queryFn: () => vendorProfileApi.listReviews(vendorId, { page, per_page: perPage }),
    enabled: !!vendorId,
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const pages = data?.pages ?? 1;

  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <h1>Reviews</h1>
          <p style={{ color: 'var(--text-secondary)' }}>Customer feedback on your services</p>
        </div>
      </div>

      {!vendorId ? (
        <div style={{ padding: 48, textAlign: 'center' }}>
          <p style={{ color: 'var(--text-secondary)' }}>Please create your vendor profile first.</p>
        </div>
      ) : isLoading ? (
        <SkeletonTable rows={5} cols={4} />
      ) : (
        <>
          <RatingSummary reviews={items} />

          {!items.length ? (
            <EmptyState
              title="No reviews yet"
              description="Customer reviews for your services will appear here."
              icon="⭐"
            />
          ) : (
            <>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {items.map((review) => (
                  <div key={review.id} className="admin-card" style={{ padding: 20 }}>
                    <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <div className="admin-avatar" style={{ background: 'var(--brand-600)', color: 'white', fontSize: 13, width: 36, height: 36 }}>
                          {review.reviewer?.name?.charAt(0)?.toUpperCase() ?? 'C'}
                        </div>
                        <div>
                          <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--text-primary)' }}>
                            {review.reviewer?.name ?? 'Customer'}
                          </div>
                          <div style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>
                            {review.created_at ? formatDate(review.created_at) : ''}
                          </div>
                        </div>
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
                        <StarRating rating={review.rating ?? 0} />
                        <span style={{ fontSize: 13, fontWeight: 700, color: '#f59e0b' }}>
                          {(review.rating ?? 0).toFixed(1)}
                        </span>
                      </div>
                    </div>
                    {review.comment && (
                      <p style={{ margin: '14px 0 0', fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                        "{review.comment}"
                      </p>
                    )}
                    {review.booking_id && (
                      <div style={{ marginTop: 10, fontSize: 12, color: 'var(--text-tertiary)' }}>
                        Booking ID: <code style={{ background: 'var(--bg-base)', padding: '1px 5px', borderRadius: 3 }}>{review.booking_id?.slice(0, 8)}</code>
                      </div>
                    )}
                  </div>
                ))}
              </div>
              <div style={{ marginTop: 16 }}>
                <Pagination page={page} pages={pages} total={total} perPage={perPage} onPageChange={setPage} />
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
