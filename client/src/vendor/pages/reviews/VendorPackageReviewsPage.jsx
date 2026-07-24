import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { vendorPackagesApi } from '../../api';
import { SkeletonTable } from '../../../admin/components/ui/Skeleton';
import EmptyState from '../../../admin/components/ui/EmptyState';
import RatingSummary from '../../../admin/components/ui/RatingSummary';
import ReviewList from '../../../admin/components/reviews/ReviewList';

/**
 * Read-only view of customer reviews for the vendor's own packages and
 * package items. Vendors cannot moderate or reply — that's admin-only.
 */
export default function VendorPackageReviewsPage() {
  const [selectedPackageId, setSelectedPackageId] = useState(null);
  const [selectedItemId, setSelectedItemId] = useState(null);

  const { data: packagesPage, isLoading: loadingPackages } = useQuery({
    queryKey: ['vendor-packages-for-reviews'],
    queryFn: () => vendorPackagesApi.list({ per_page: 100 }),
  });
  const packages = packagesPage?.items ?? [];

  const activePackage = packages.find((p) => p.id === selectedPackageId) ?? packages[0] ?? null;
  const activePackageId = activePackage?.id ?? null;

  const { data: itemsList } = useQuery({
    queryKey: ['vendor-package-items-for-reviews', activePackageId],
    queryFn: () => vendorPackagesApi.listItems(activePackageId),
    enabled: !!activePackageId,
  });
  const items = itemsList ?? [];

  const { data: reviewsPage, isLoading: loadingReviews } = useQuery({
    queryKey: ['vendor-package-reviews', activePackageId],
    queryFn: () => vendorPackagesApi.listReviews(activePackageId, { limit: 50 }),
    enabled: !!activePackageId,
  });
  const reviews = reviewsPage?.items ?? [];

  const { data: itemReviewsPage, isLoading: loadingItemReviews } = useQuery({
    queryKey: ['vendor-package-item-reviews', activePackageId, selectedItemId],
    queryFn: () => vendorPackagesApi.listItemReviews(activePackageId, selectedItemId, { limit: 50 }),
    enabled: !!activePackageId && !!selectedItemId,
  });
  const itemReviews = itemReviewsPage?.items ?? [];

  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <h1>Package Reviews</h1>
          <p style={{ color: 'var(--text-secondary)' }}>Customer reviews for your packages and items</p>
        </div>
      </div>

      {loadingPackages ? (
        <SkeletonTable rows={5} cols={4} />
      ) : !packages.length ? (
        <EmptyState title="No packages yet" description="Create a package to start receiving reviews." icon="📦" />
      ) : (
        <>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 20 }}>
            {packages.map((p) => (
              <button
                key={p.id}
                className={`btn ${p.id === activePackageId ? 'btn-primary' : 'btn-secondary'} btn-sm`}
                onClick={() => { setSelectedPackageId(p.id); setSelectedItemId(null); }}
              >
                {p.name}
              </button>
            ))}
          </div>

          {loadingReviews ? (
            <SkeletonTable rows={4} cols={3} />
          ) : (
            <>
              <RatingSummary reviews={reviews} />
              <div className="admin-card" style={{ marginBottom: 20 }}>
                <div className="admin-card-header"><div className="admin-card-title">Package Reviews</div></div>
                <div className="admin-card-body">
                  <ReviewList reviews={reviews} canModerate={false} />
                </div>
              </div>
            </>
          )}

          {items.length > 0 && (
            <div className="admin-card">
              <div className="admin-card-header"><div className="admin-card-title">Item Reviews</div></div>
              <div className="admin-card-body">
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16 }}>
                  {items.map((item) => (
                    <button
                      key={item.id}
                      className={`btn ${item.id === selectedItemId ? 'btn-primary' : 'btn-secondary'} btn-sm`}
                      onClick={() => setSelectedItemId(item.id === selectedItemId ? null : item.id)}
                    >
                      {item.name} {item.review_count ? `(${item.review_count})` : ''}
                    </button>
                  ))}
                </div>
                {selectedItemId && (
                  loadingItemReviews ? (
                    <SkeletonTable rows={3} cols={3} />
                  ) : (
                    <ReviewList reviews={itemReviews} canModerate={false} />
                  )
                )}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
