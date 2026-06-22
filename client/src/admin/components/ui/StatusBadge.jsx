import { statusColor } from '../../utils/format';

export default function StatusBadge({ status }) {
  if (!status) return null;
  const color = statusColor(status);
  const label = status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  return (
    <span className={`badge badge-${color}`}>
      <span className="badge-dot" />
      {label}
    </span>
  );
}
