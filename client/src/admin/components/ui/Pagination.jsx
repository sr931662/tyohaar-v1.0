/**
 * Page controls for admin and vendor lists.
 *
 * Accepts both prop spellings used across the portals (`onChange` or
 * `onPageChange`, `pages` or `totalPages`). Pass `hasNext` from the list
 * response so cursor-paginated endpoints — which have no total — still get
 * working Prev/Next controls.
 */
export default function Pagination({
  page,
  pages,
  totalPages,
  total,
  perPage = 20,
  hasNext,
  onChange,
  onPageChange,
}) {
  const go = onChange ?? onPageChange;
  const pageCount = Math.max(1, pages ?? totalPages ?? 1);
  const cursorMode = total === null || total === undefined;

  if (cursorMode) {
    const canNext = hasNext ?? page < pageCount;
    if (page <= 1 && !canNext) return null;
    return (
      <div className="admin-pagination">
        <span className="admin-pagination-info">Page {page}</span>
        <div className="admin-pagination-controls">
          <button className="admin-pagination-btn" onClick={() => go(page - 1)} disabled={page <= 1}>‹</button>
          <button className="admin-pagination-btn active">{page}</button>
          <button className="admin-pagination-btn" onClick={() => go(page + 1)} disabled={!canNext}>›</button>
        </div>
      </div>
    );
  }

  if (!total || pageCount <= 1) return null;

  const current = Math.min(Math.max(1, page), pageCount);
  const from = (current - 1) * perPage + 1;
  const to = Math.min(current * perPage, total);

  const pageNumbers = [];
  const delta = 2;
  for (let i = Math.max(1, current - delta); i <= Math.min(pageCount, current + delta); i++) {
    pageNumbers.push(i);
  }

  return (
    <div className="admin-pagination">
      <span className="admin-pagination-info">
        Showing {from}–{to} of {total}
      </span>
      <div className="admin-pagination-controls">
        <button className="admin-pagination-btn" onClick={() => go(1)} disabled={current === 1}>«</button>
        <button className="admin-pagination-btn" onClick={() => go(current - 1)} disabled={current === 1}>‹</button>
        {pageNumbers.map((n) => (
          <button
            key={n}
            className={`admin-pagination-btn${n === current ? ' active' : ''}`}
            onClick={() => go(n)}
          >
            {n}
          </button>
        ))}
        <button className="admin-pagination-btn" onClick={() => go(current + 1)} disabled={current === pageCount}>›</button>
        <button className="admin-pagination-btn" onClick={() => go(pageCount)} disabled={current === pageCount}>»</button>
      </div>
    </div>
  );
}
