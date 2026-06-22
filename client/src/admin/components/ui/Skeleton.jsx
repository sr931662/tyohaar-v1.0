export function SkeletonLine({ width = '100%', height = 14 }) {
  return <div className="skeleton" style={{ width, height, borderRadius: 4, marginBottom: 8 }} />;
}

export function SkeletonCard({ height = 120 }) {
  return <div className="skeleton skeleton-card" style={{ height, borderRadius: 12, marginBottom: 12 }} />;
}

export function SkeletonTable({ rows = 5, cols = 4 }) {
  return (
    <div className="admin-table-wrapper">
      <table className="admin-table">
        <thead>
          <tr>
            {Array.from({ length: cols }).map((_, i) => (
              <th key={i}><SkeletonLine width={80} /></th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: rows }).map((_, r) => (
            <tr key={r}>
              {Array.from({ length: cols }).map((_, c) => (
                <td key={c}><SkeletonLine width={c === 0 ? 140 : 80} /></td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function SkeletonMetrics({ count = 4 }) {
  return (
    <div className="admin-metric-grid">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="admin-metric-card">
          <SkeletonLine width={100} height={12} />
          <SkeletonLine width={80} height={28} />
          <SkeletonLine width={60} height={12} />
        </div>
      ))}
    </div>
  );
}
