export default function EmptyState({ title = 'Nothing here', message, action }) {
  return (
    <div className="admin-empty">
      <div className="admin-empty-icon">○</div>
      <div className="admin-empty-title">{title}</div>
      {message && <p className="admin-empty-text">{message}</p>}
      {action}
    </div>
  );
}
