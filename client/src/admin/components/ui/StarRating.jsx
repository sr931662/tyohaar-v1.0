export default function StarRating({ rating }) {
  return (
    <div style={{ display: 'flex', gap: 2 }}>
      {[1, 2, 3, 4, 5].map((s) => (
        <span key={s} style={{ fontSize: 14, color: s <= Math.round(rating) ? '#f59e0b' : 'var(--border-subtle)' }}>
          ★
        </span>
      ))}
    </div>
  );
}
