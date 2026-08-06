/**
 * Presentational-only selection bar shown above a list when rows are
 * selected. Mutations, confirm dialogs, and per-resource copy stay
 * page-local — this only removes the repeated "N selected + Clear" markup.
 */
export default function BulkActionBar({ count, onClear, children }) {
  if (!count) return null;

  return (
    <div className="admin-bulk-action-bar" style={{
      display: 'flex', alignItems: 'center', gap: 12,
      padding: '10px 16px', marginBottom: 12,
      background: 'var(--surface-2, #f5f5f5)', borderRadius: 8,
    }}>
      <span style={{ fontWeight: 600 }}>{count} selected</span>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>{children}</div>
      <button className="btn btn-ghost" style={{ marginLeft: 'auto' }} onClick={onClear}>
        Clear
      </button>
    </div>
  );
}
