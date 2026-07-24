import StarRating from './StarRating';

export default function RatingSummary({ reviews }) {
  if (!reviews.length) return null;
  const avg = reviews.reduce((sum, r) => sum + (r.rating ?? 0), 0) / reviews.length;
  const dist = [5, 4, 3, 2, 1].map((star) => ({
    star,
    count: reviews.filter((r) => Math.round(r.rating) === star).length,
  }));
  return (
    <div className="admin-card" style={{ marginBottom: 20, padding: 20 }}>
      <div style={{ display: 'flex', gap: 32, alignItems: 'center', flexWrap: 'wrap' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 48, fontWeight: 800, color: 'var(--text-primary)', lineHeight: 1 }}>
            {avg.toFixed(1)}
          </div>
          <StarRating rating={avg} />
          <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginTop: 4 }}>{reviews.length} review{reviews.length !== 1 ? 's' : ''}</div>
        </div>
        <div style={{ flex: 1, minWidth: 200 }}>
          {dist.map(({ star, count }) => (
            <div key={star} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
              <span style={{ fontSize: 12, color: 'var(--text-secondary)', width: 20, textAlign: 'right' }}>{star}</span>
              <span style={{ fontSize: 12, color: '#f59e0b' }}>★</span>
              <div style={{ flex: 1, height: 6, background: 'var(--bg-base)', borderRadius: 3, overflow: 'hidden' }}>
                <div style={{
                  height: '100%', borderRadius: 3,
                  background: '#f59e0b',
                  width: `${reviews.length ? (count / reviews.length) * 100 : 0}%`,
                  transition: 'width 0.4s ease',
                }} />
              </div>
              <span style={{ fontSize: 12, color: 'var(--text-tertiary)', width: 20 }}>{count}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
