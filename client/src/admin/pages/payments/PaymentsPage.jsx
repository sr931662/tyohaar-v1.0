import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { paymentsApi } from '../../api';
import { formatCurrency, formatDateTime } from '../../utils/format';
import StatusBadge from '../../components/ui/StatusBadge';
import Pagination from '../../components/ui/Pagination';
import { SkeletonTable } from '../../components/ui/Skeleton';
import EmptyState from '../../components/ui/EmptyState';
import Modal from '../../components/ui/Modal';
import { useDebounce } from '../../hooks/useDebounce';
import { usePagination } from '../../hooks/usePagination';

function CouponSection() {
  const qc = useQueryClient();
  const [newOpen, setNewOpen] = useState(false);
  const [form, setForm] = useState({ code: '', discount_type: 'percentage', discount_value: '', max_uses: '', valid_until: '' });

  const { data: coupons = [], isLoading } = useQuery({
    queryKey: ['payments', 'coupons'],
    queryFn: () => paymentsApi.listCoupons(),
  });

  const createMutation = useMutation({
    mutationFn: () => paymentsApi.createCoupon(form),
    onSuccess: () => { toast.success('Coupon created'); qc.invalidateQueries(['payments', 'coupons']); setNewOpen(false); },
    onError: () => toast.error('Failed to create coupon'),
  });

  const deactivateMutation = useMutation({
    mutationFn: (id) => paymentsApi.deactivateCoupon(id),
    onSuccess: () => { toast.success('Coupon deactivated'); qc.invalidateQueries(['payments', 'coupons']); },
    onError: () => toast.error('Failed'),
  });

  return (
    <div>
      <div className="admin-page-header" style={{ marginBottom: 12 }}>
        <div className="admin-page-header-left">
          <h2 style={{ fontSize: 16 }}>Coupons</h2>
        </div>
        <button className="btn btn-primary btn-sm" onClick={() => setNewOpen(true)}>+ New Coupon</button>
      </div>
      <div className="admin-table-wrapper">
        <table className="admin-table">
          <thead>
            <tr><th>Code</th><th>Type</th><th>Value</th><th>Uses</th><th>Expires</th><th>Actions</th></tr>
          </thead>
          <tbody>
            {coupons.map((c) => (
              <tr key={c.id}>
                <td><code style={{ fontSize: 12 }}>{c.code}</code></td>
                <td>{c.discount_type}</td>
                <td>{c.discount_type === 'percentage' ? `${c.discount_value}%` : formatCurrency(c.discount_value)}</td>
                <td>{c.used_count ?? 0} / {c.max_uses ?? '∞'}</td>
                <td>{c.valid_until ? formatDateTime(c.valid_until) : 'No expiry'}</td>
                <td>
                  <button className="btn btn-danger btn-sm" onClick={() => deactivateMutation.mutate(c.id)}>Deactivate</button>
                </td>
              </tr>
            ))}
            {!coupons.length && <tr><td colSpan={6} className="admin-table-empty">No coupons</td></tr>}
          </tbody>
        </table>
      </div>

      <Modal open={newOpen} onClose={() => setNewOpen(false)} title="Create Coupon"
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setNewOpen(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={() => createMutation.mutate()} disabled={createMutation.isPending}>
              {createMutation.isPending ? 'Creating…' : 'Create'}
            </button>
          </>
        }
      >
        <div className="form-row-2">
          <div className="form-group">
            <label className="form-label required">Coupon Code</label>
            <input className="form-control" value={form.code} onChange={e => setForm(f => ({ ...f, code: e.target.value.toUpperCase() }))} placeholder="SAVE20" />
          </div>
          <div className="form-group">
            <label className="form-label required">Discount Type</label>
            <select className="form-control" value={form.discount_type} onChange={e => setForm(f => ({ ...f, discount_type: e.target.value }))}>
              <option value="percentage">Percentage</option>
              <option value="fixed">Fixed Amount</option>
            </select>
          </div>
        </div>
        <div className="form-row-2">
          <div className="form-group">
            <label className="form-label required">Discount Value</label>
            <input className="form-control" type="number" value={form.discount_value} onChange={e => setForm(f => ({ ...f, discount_value: e.target.value }))} />
          </div>
          <div className="form-group">
            <label className="form-label">Max Uses</label>
            <input className="form-control" type="number" value={form.max_uses} onChange={e => setForm(f => ({ ...f, max_uses: e.target.value }))} placeholder="Unlimited" />
          </div>
        </div>
        <div className="form-group">
          <label className="form-label">Valid Until</label>
          <input className="form-control" type="datetime-local" value={form.valid_until} onChange={e => setForm(f => ({ ...f, valid_until: e.target.value }))} />
        </div>
      </Modal>
    </div>
  );
}

export default function PaymentsPage() {
  const navigate = useNavigate();
  const { page, perPage, setPage, reset } = usePagination();
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [activeTab, setActiveTab] = useState('payments');
  const debouncedSearch = useDebounce(search);

  const { data, isLoading } = useQuery({
    queryKey: ['payments', { page, perPage, search: debouncedSearch, status }],
    queryFn: () => paymentsApi.list({ page, per_page: perPage, search: debouncedSearch || undefined, status: status || undefined }),
    enabled: activeTab === 'payments',
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const pages = data?.pages ?? 1;

  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <h1>Payments</h1>
          <p>Track all payments, refunds, and coupons</p>
        </div>
      </div>

      <div className="admin-tabs">
        {['payments', 'coupons'].map(t => (
          <button key={t} className={`admin-tab${activeTab === t ? ' active' : ''}`} onClick={() => setActiveTab(t)}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {activeTab === 'payments' && (
        <>
          <div className="admin-filters">
            <div className="admin-filters-search">
              <span style={{ color: 'var(--text-tertiary)' }}>⌕</span>
              <input placeholder="Search payments…" value={search} onChange={(e) => { setSearch(e.target.value); reset(); }} />
            </div>
            <select className="admin-filters-select" value={status} onChange={(e) => { setStatus(e.target.value); reset(); }}>
              <option value="">All Statuses</option>
              <option value="pending">Pending</option>
              <option value="success">Success</option>
              <option value="failed">Failed</option>
              <option value="refunded">Refunded</option>
            </select>
          </div>

          {isLoading ? <SkeletonTable rows={10} cols={6} /> : !items.length ? (
            <EmptyState title="No payments found" />
          ) : (
            <div className="admin-table-wrapper">
              <table className="admin-table">
                <thead>
                  <tr><th>Payment ID</th><th>Customer</th><th>Amount</th><th>Gateway</th><th>Status</th><th>Date</th><th>Actions</th></tr>
                </thead>
                <tbody>
                  {items.map((p) => (
                    <tr key={p.id}>
                      <td><code style={{ fontSize: 11 }}>{p.id?.slice(0, 8)}</code></td>
                      <td>{p.user?.name ?? p.customer_name ?? '—'}</td>
                      <td><strong>{formatCurrency(p.amount)}</strong></td>
                      <td>{p.gateway ?? '—'}</td>
                      <td><StatusBadge status={p.status} /></td>
                      <td>{formatDateTime(p.created_at)}</td>
                      <td>
                        <button className="btn btn-secondary btn-sm" onClick={() => navigate(`/admin/payments/${p.id}`)}>View</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <Pagination page={page} pages={pages} total={total} perPage={perPage} onChange={setPage} />
            </div>
          )}
        </>
      )}

      {activeTab === 'coupons' && <CouponSection />}
    </div>
  );
}
