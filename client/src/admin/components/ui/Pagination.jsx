export default function Pagination({ page, pages, total, perPage, onChange }) {
  if (!total || pages <= 1) return null;

  const from = (page - 1) * perPage + 1;
  const to = Math.min(page * perPage, total);

  const pageNumbers = () => {
    const nums = [];
    const delta = 2;
    for (let i = Math.max(1, page - delta); i <= Math.min(pages, page + delta); i++) {
      nums.push(i);
    }
    return nums;
  };

  return (
    <div className="admin-pagination">
      <span className="admin-pagination-info">
        Showing {from}–{to} of {total}
      </span>
      <div className="admin-pagination-controls">
        <button className="admin-pagination-btn" onClick={() => onChange(1)} disabled={page === 1}>«</button>
        <button className="admin-pagination-btn" onClick={() => onChange(page - 1)} disabled={page === 1}>‹</button>
        {pageNumbers().map((n) => (
          <button
            key={n}
            className={`admin-pagination-btn${n === page ? ' active' : ''}`}
            onClick={() => onChange(n)}
          >
            {n}
          </button>
        ))}
        <button className="admin-pagination-btn" onClick={() => onChange(page + 1)} disabled={page === pages}>›</button>
        <button className="admin-pagination-btn" onClick={() => onChange(pages)} disabled={page === pages}>»</button>
      </div>
    </div>
  );
}
