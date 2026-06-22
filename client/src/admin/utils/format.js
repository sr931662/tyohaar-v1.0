import { format, formatDistanceToNow, parseISO } from 'date-fns';

export function formatCurrency(amount, currency = 'INR') {
  if (amount == null) return '—';
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency }).format(amount);
}

export function formatNumber(n) {
  if (n == null) return '—';
  return new Intl.NumberFormat('en-IN').format(n);
}

export function formatDate(dateStr, fmt = 'dd MMM yyyy') {
  if (!dateStr) return '—';
  try { return format(parseISO(dateStr), fmt); } catch { return dateStr; }
}

export function formatDateTime(dateStr) {
  return formatDate(dateStr, 'dd MMM yyyy, hh:mm a');
}

export function timeAgo(dateStr) {
  if (!dateStr) return '—';
  try { return formatDistanceToNow(parseISO(dateStr), { addSuffix: true }); } catch { return dateStr; }
}

export function initials(name = '') {
  return name.split(' ').slice(0, 2).map((w) => w[0]).join('').toUpperCase();
}

export function truncate(str, len = 40) {
  if (!str) return '';
  return str.length > len ? str.slice(0, len) + '…' : str;
}

export function statusColor(status = '') {
  const s = status.toLowerCase();
  if (['active', 'approved', 'confirmed', 'completed', 'paid', 'success', 'verified', 'published'].some(k => s.includes(k))) return 'success';
  if (['pending', 'processing', 'in_progress', 'scheduled', 'partial'].some(k => s.includes(k))) return 'warning';
  if (['cancelled', 'rejected', 'failed', 'expired', 'suspended', 'frozen', 'closed', 'inactive'].some(k => s.includes(k))) return 'error';
  if (['draft', 'inactive', 'archived', 'unpublished'].some(k => s.includes(k))) return 'neutral';
  return 'info';
}

export function formatPercent(n) {
  if (n == null) return '—';
  return `${n > 0 ? '+' : ''}${Number(n).toFixed(1)}%`;
}
