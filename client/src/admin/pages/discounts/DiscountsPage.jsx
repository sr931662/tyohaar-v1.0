import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { discountsApi, bulkApi, vendorsApi, packagesApi, occasionsApi, membershipsApi } from '../../api';
import { formatCurrency, formatNumber } from '../../utils/format';
import StatusBadge from '../../components/ui/StatusBadge';
import Pagination from '../../components/ui/Pagination';
import { SkeletonTable, SkeletonMetrics } from '../../components/ui/Skeleton';
import EmptyState from '../../components/ui/EmptyState';
import Modal, { ConfirmDialog } from '../../components/ui/Modal';
import ImageUploadField from '../../components/ui/ImageUploadField';
import MultiSelect from '../../components/ui/MultiSelect';
import { useDebounce } from '../../hooks/useDebounce';
import { usePagination } from '../../hooks/usePagination';

const COUPON_TYPES = [
  { value: 'percentage', label: 'Percentage Discount' },
  { value: 'fixed_amount', label: 'Flat Amount Discount' },
  { value: 'fixed_price', label: 'Fixed Price Offer' },
  { value: 'free_service', label: 'Free Service' },
  { value: 'cashback', label: 'Cashback' },
  { value: 'buy_x_get_y', label: 'Buy X Get Y (coming soon)', disabled: true },
  { value: 'free_addon', label: 'Free Add-on (coming soon)', disabled: true },
];

const APPLICABILITY_OPTIONS = [
  { value: 'all', label: 'Entire Platform' },
  { value: 'first_booking', label: 'First Booking Only' },
  { value: 'specific_category', label: 'Specific Occasion Category' },
  { value: 'specific_vendor', label: 'Specific Vendor(s)' },
  { value: 'specific_package', label: 'Specific Package(s)' },
  { value: 'membership_only', label: 'Membership Tier' },
];

const OCCASION_CATEGORY_OPTIONS = [
  { value: 'life_event', label: 'Life Event' },
  { value: 'major_festival', label: 'Major Festival' },
  { value: 'minor_festival', label: 'Minor Festival' },
  { value: 'personal', label: 'Personal' },
  { value: 'corporate', label: 'Corporate' },
  { value: 'religious', label: 'Religious' },
  { value: 'seasonal', label: 'Seasonal' },
];

const VERB_LABELS = {
  enable: { past: 'enabled', ing: 'enable' },
  disable: { past: 'disabled', ing: 'disable' },
  archive: { past: 'archived', ing: 'archive' },
};

const EMPTY_FORM = {
  mode: 'automatic', // 'automatic' | 'code'
  code: '',
  title: '',
  public_offer_title: '',
  description: '',
  terms_and_conditions: '',
  coupon_type: 'percentage',
  applicability: 'all',
  discount_value: '',
  max_discount_amount: '',
  priority: '100',
  is_stackable: false,
  banner_image_url: '',
  theme_color_hex: '',
  min_order_value: '',
  min_package_value: '',
  first_booking_only: false,
  repeat_customers_only: false,
  referral_users_only: false,
  eligible_membership_tiers: [],
  applicable_vendor_ids: [],
  applicable_package_ids: [],
  applicable_occasion_ids: [],
  applicable_occasion_categories: [],
  total_usage_limit: '',
  per_user_limit: '',
  max_uses_per_day: '',
  valid_from: '',
  valid_until: '',
  admin_status: 'draft',
};

function toDatetimeLocal(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function MetricCard({ label, value, icon }) {
  return (
    <div className="admin-metric-card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div className="admin-metric-label">{label}</div>
          <div className="admin-metric-value">{value ?? '—'}</div>
        </div>
        {icon && (
          <div className="admin-metric-icon" style={{ background: 'var(--brand-100)', color: 'var(--brand-600)' }}>
            <span style={{ fontSize: 18 }}>{icon}</span>
          </div>
        )}
      </div>
    </div>
  );
}

function AnalyticsTab() {
  const { data, isLoading } = useQuery({
    queryKey: ['discounts', 'analytics'],
    queryFn: () => discountsApi.analytics(),
  });

  if (isLoading) return <SkeletonMetrics count={8} />;
  if (!data) return <EmptyState title="No analytics available" />;

  const statusChartData = [
    { name: 'Draft', count: data.draft_count },
    { name: 'Scheduled', count: data.scheduled_count },
    { name: 'Active', count: data.active_count },
    { name: 'Paused', count: data.paused_count },
    { name: 'Expired', count: data.expired_count },
    { name: 'Archived', count: data.archived_count },
  ];

  return (
    <div>
      <div className="admin-metric-grid" style={{ marginBottom: 24 }}>
        <MetricCard label="Total Discounts" value={formatNumber(data.total_discounts)} icon="🏷️" />
        <MetricCard label="Active Now" value={formatNumber(data.active_count)} icon="✅" />
        <MetricCard label="Times Used" value={formatNumber(data.total_times_used)} icon="🔁" />
        <MetricCard label="Conversion Rate" value={`${data.conversion_rate}%`} icon="📈" />
        <MetricCard label="Revenue Generated" value={formatCurrency(data.total_revenue_generated)} icon="💰" />
        <MetricCard label="Revenue Given (Discounts)" value={formatCurrency(data.total_revenue_lost)} icon="🎁" />
      </div>

      <div className="admin-card" style={{ marginBottom: 24 }}>
        <div className="admin-card-header">
          <div className="admin-card-title">Discounts by Status</div>
        </div>
        <div className="admin-card-body" style={{ height: 260 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={statusChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
              <XAxis dataKey="name" tick={{ fontSize: 12 }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="count" fill="var(--brand-500)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="admin-card">
        <div className="admin-card-header">
          <div className="admin-card-title">Top Performing Discounts</div>
        </div>
        <div className="admin-table-wrapper">
          <table className="admin-table">
            <thead>
              <tr><th>Discount</th><th>Code</th><th>Times Used</th><th>Revenue Generated</th></tr>
            </thead>
            <tbody>
              {(data.top_coupons ?? []).map((c) => (
                <tr key={c.coupon_id}>
                  <td>{c.title}</td>
                  <td>{c.code ? <code style={{ fontSize: 12 }}>{c.code}</code> : <span style={{ color: 'var(--text-tertiary)' }}>Automatic</span>}</td>
                  <td>{formatNumber(c.times_used)}</td>
                  <td>{formatCurrency(c.revenue_generated)}</td>
                </tr>
              ))}
              {!data.top_coupons?.length && <tr><td colSpan={4} className="admin-table-empty">No usage yet</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default function DiscountsPage() {
  const qc = useQueryClient();
  const { page, perPage, setPage, reset } = usePagination();
  const [activeTab, setActiveTab] = useState('list');
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [selected, setSelected] = useState([]);
  const [confirmBulk, setConfirmBulk] = useState('');
  const debouncedSearch = useDebounce(search);

  const [formOpen, setFormOpen] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [confirmAction, setConfirmAction] = useState(null); // { type: 'archive'|'duplicate', id, name }

  const { data, isLoading } = useQuery({
    queryKey: ['discounts', { page, perPage, search: debouncedSearch, status }],
    queryFn: () => discountsApi.list({
      page, per_page: perPage,
      search: debouncedSearch || undefined,
      admin_status: status || undefined,
    }),
    enabled: activeTab === 'list',
  });

  // Scope-picker option sources — only fetched while the form is open.
  const { data: vendorOptions = [] } = useQuery({
    queryKey: ['discounts', 'vendor-options'],
    queryFn: async () => {
      const res = await vendorsApi.list({ per_page: 100 });
      return (res.items ?? []).map((v) => ({ value: v.id, label: v.business_name ?? v.name ?? v.id }));
    },
    enabled: formOpen,
    staleTime: 60_000,
  });
  const { data: packageOptions = [] } = useQuery({
    queryKey: ['discounts', 'package-options'],
    queryFn: async () => {
      const res = await packagesApi.list({ per_page: 100 });
      return (res.items ?? []).map((p) => ({ value: p.id, label: p.name ?? p.id }));
    },
    enabled: formOpen,
    staleTime: 60_000,
  });
  const { data: occasionOptions = [] } = useQuery({
    queryKey: ['discounts', 'occasion-options'],
    queryFn: async () => {
      const res = await occasionsApi.list({ per_page: 100 });
      return (res.items ?? []).map((o) => ({ value: o.id, label: o.name ?? o.id }));
    },
    enabled: formOpen,
    staleTime: 60_000,
  });
  const { data: membershipTierOptions = [] } = useQuery({
    queryKey: ['discounts', 'membership-tier-options'],
    queryFn: async () => {
      const plans = await membershipsApi.listPlans();
      const seen = new Set();
      return (plans ?? []).filter((p) => {
        if (seen.has(p.tier)) return false;
        seen.add(p.tier);
        return true;
      }).map((p) => ({ value: p.tier, label: p.tier }));
    },
    enabled: formOpen,
    staleTime: 60_000,
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const pages = data?.pages ?? 1;

  const buildPayload = (f) => ({
    is_automatic: f.mode === 'automatic',
    code: f.mode === 'code' ? f.code.trim() : undefined,
    title: f.title,
    public_offer_title: f.public_offer_title || undefined,
    description: f.description || undefined,
    terms_and_conditions: f.terms_and_conditions || undefined,
    coupon_type: f.coupon_type,
    applicability: f.applicability,
    discount_value: f.discount_value === '' ? 0 : Number(f.discount_value),
    max_discount_amount: f.max_discount_amount === '' ? undefined : Number(f.max_discount_amount),
    priority: parseInt(f.priority, 10) || 100,
    is_stackable: f.is_stackable,
    banner_image_url: f.banner_image_url || undefined,
    theme_color_hex: f.theme_color_hex || undefined,
    min_order_value: f.min_order_value === '' ? undefined : Number(f.min_order_value),
    min_package_value: f.min_package_value === '' ? undefined : Number(f.min_package_value),
    first_booking_only: f.first_booking_only,
    repeat_customers_only: f.repeat_customers_only,
    referral_users_only: f.referral_users_only,
    eligible_membership_tiers: f.eligible_membership_tiers.length ? f.eligible_membership_tiers : undefined,
    applicable_vendor_ids: f.applicable_vendor_ids.length ? f.applicable_vendor_ids : undefined,
    applicable_package_ids: f.applicable_package_ids.length ? f.applicable_package_ids : undefined,
    applicable_occasion_ids: f.applicable_occasion_ids.length ? f.applicable_occasion_ids : undefined,
    applicable_occasion_categories: f.applicable_occasion_categories.length ? f.applicable_occasion_categories : undefined,
    total_usage_limit: f.total_usage_limit === '' ? undefined : parseInt(f.total_usage_limit, 10),
    per_user_limit: f.per_user_limit === '' ? undefined : parseInt(f.per_user_limit, 10),
    max_uses_per_day: f.max_uses_per_day === '' ? undefined : parseInt(f.max_uses_per_day, 10),
    valid_from: f.valid_from ? new Date(f.valid_from).toISOString() : new Date().toISOString(),
    valid_until: f.valid_until ? new Date(f.valid_until).toISOString() : undefined,
    admin_status: f.admin_status,
  });

  const saveMutation = useMutation({
    mutationFn: () => {
      const payload = buildPayload(form);
      return editItem ? discountsApi.update(editItem.id, payload) : discountsApi.create(payload);
    },
    onSuccess: () => {
      toast.success(editItem ? 'Discount updated' : 'Discount created');
      qc.invalidateQueries(['discounts']);
      setFormOpen(false); setEditItem(null); setForm(EMPTY_FORM);
    },
    onError: (err) => toast.error(err?.response?.data?.error?.message ?? err?.response?.data?.detail ?? 'Save failed'),
  });

  const duplicateMutation = useMutation({
    mutationFn: (id) => discountsApi.duplicate(id),
    onSuccess: () => { toast.success('Discount duplicated as a new draft'); qc.invalidateQueries(['discounts']); },
    onError: () => toast.error('Failed to duplicate'),
  });

  const archiveMutation = useMutation({
    mutationFn: (id) => discountsApi.archive(id),
    onSuccess: () => { toast.success('Discount archived'); qc.invalidateQueries(['discounts']); },
    onError: () => toast.error('Failed to archive'),
  });

  const toggleActiveMutation = useMutation({
    mutationFn: ({ id, is_active }) => discountsApi.update(id, { is_active }),
    onSuccess: () => { toast.success('Status updated'); qc.invalidateQueries(['discounts']); },
    onError: () => toast.error('Failed to update status'),
  });

  const reportBulkResult = (result, verb) => {
    const { past, ing } = VERB_LABELS[verb];
    const noun = result.total_requested === 1 ? 'discount' : 'discounts';
    if (result.failed > 0 && result.succeeded === 0) {
      toast.error(`Failed to ${ing} ${result.failed === 1 ? 'the discount' : `${result.failed} discounts`}.`);
    } else if (result.failed > 0) {
      toast.warning(`${result.succeeded} ${noun} ${past}, ${result.failed} failed.`);
    } else {
      toast.success(`${result.total_requested === 1 ? 'Discount' : 'Discounts'} ${past}.`);
    }
    qc.invalidateQueries(['discounts']);
    setSelected([]);
  };

  const bulkEnableMutation = useMutation({
    mutationFn: (ids) => bulkApi.enableDiscounts(ids),
    onSuccess: (result) => reportBulkResult(result, 'enable'),
    onError: () => toast.error('Failed to enable.'),
  });
  const bulkDisableMutation = useMutation({
    mutationFn: (ids) => bulkApi.disableDiscounts(ids),
    onSuccess: (result) => reportBulkResult(result, 'disable'),
    onError: () => toast.error('Failed to disable.'),
  });
  const bulkArchiveMutation = useMutation({
    mutationFn: (ids) => bulkApi.archiveDiscounts(ids),
    onSuccess: (result) => reportBulkResult(result, 'archive'),
    onError: () => toast.error('Failed to archive.'),
  });

  const toggleAll = () => setSelected((s) => (s.length === items.length ? [] : items.map((i) => i.id)));
  const toggleItem = (id) => setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));

  const handleBulk = () => {
    if (confirmBulk === 'enable') bulkEnableMutation.mutate(selected);
    else if (confirmBulk === 'disable') bulkDisableMutation.mutate(selected);
    else if (confirmBulk === 'archive') bulkArchiveMutation.mutate(selected);
    setConfirmBulk('');
  };

  const openCreate = () => { setEditItem(null); setForm(EMPTY_FORM); setFormOpen(true); };

  const openEdit = (item) => {
    setEditItem(item);
    setForm({
      mode: item.is_automatic ? 'automatic' : 'code',
      code: item.code ?? '',
      title: item.title ?? '',
      public_offer_title: item.public_offer_title ?? '',
      description: item.description ?? '',
      terms_and_conditions: item.terms_and_conditions ?? '',
      coupon_type: item.coupon_type,
      applicability: item.applicability,
      discount_value: String(item.discount_value ?? ''),
      max_discount_amount: item.max_discount_amount != null ? String(item.max_discount_amount) : '',
      priority: String(item.priority ?? 100),
      is_stackable: !!item.is_stackable,
      banner_image_url: item.banner_image_url ?? '',
      theme_color_hex: item.theme_color_hex ?? '',
      min_order_value: item.min_order_value != null ? String(item.min_order_value) : '',
      min_package_value: item.min_package_value != null ? String(item.min_package_value) : '',
      first_booking_only: !!item.first_booking_only,
      repeat_customers_only: !!item.repeat_customers_only,
      referral_users_only: !!item.referral_users_only,
      eligible_membership_tiers: item.eligible_membership_tiers ?? [],
      applicable_vendor_ids: item.applicable_vendor_ids ?? [],
      applicable_package_ids: item.applicable_package_ids ?? [],
      applicable_occasion_ids: item.applicable_occasion_ids ?? [],
      applicable_occasion_categories: item.applicable_occasion_categories ?? [],
      total_usage_limit: item.total_usage_limit != null ? String(item.total_usage_limit) : '',
      per_user_limit: item.per_user_limit != null ? String(item.per_user_limit) : '',
      max_uses_per_day: item.max_uses_per_day != null ? String(item.max_uses_per_day) : '',
      valid_from: toDatetimeLocal(item.valid_from),
      valid_until: toDatetimeLocal(item.valid_until),
      admin_status: item.admin_status ?? 'draft',
    });
    setFormOpen(true);
  };

  const handleConfirmAction = () => {
    if (!confirmAction) return;
    if (confirmAction.type === 'archive') archiveMutation.mutate(confirmAction.id);
    else if (confirmAction.type === 'duplicate') duplicateMutation.mutate(confirmAction.id);
    setConfirmAction(null);
  };

  const set = (key) => (e) => {
    const value = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
    setForm((f) => ({ ...f, [key]: value }));
  };
  const setList = (key) => (arr) => setForm((f) => ({ ...f, [key]: arr }));

  const isBulkPending = bulkEnableMutation.isPending || bulkDisableMutation.isPending || bulkArchiveMutation.isPending;

  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <h1>Discounts &amp; Promotions</h1>
          <p>Create and manage coupon-based and automatic discounts</p>
        </div>
        {activeTab === 'list' && (
          <div className="admin-page-header-actions">
            <button className="btn btn-primary" onClick={openCreate}>+ New Discount</button>
          </div>
        )}
      </div>

      <div className="admin-tabs" style={{ marginBottom: 16 }}>
        <button className={`admin-tab${activeTab === 'list' ? ' active' : ''}`} onClick={() => setActiveTab('list')}>Discounts</button>
        <button className={`admin-tab${activeTab === 'analytics' ? ' active' : ''}`} onClick={() => setActiveTab('analytics')}>Analytics</button>
      </div>

      {activeTab === 'analytics' ? <AnalyticsTab /> : (
        <>
          <div className="admin-filters">
            <div className="admin-filters-search">
              <span style={{ color: 'var(--text-tertiary)' }}>⌕</span>
              <input placeholder="Search by name or code…" value={search} onChange={(e) => { setSearch(e.target.value); reset(); }} />
            </div>
            <select className="admin-filters-select" value={status} onChange={(e) => { setStatus(e.target.value); reset(); }}>
              <option value="">All Statuses</option>
              <option value="draft">Draft</option>
              <option value="published">Published</option>
              <option value="paused">Paused</option>
              <option value="archived">Archived</option>
            </select>
            {selected.length > 0 && (
              <>
                <button className="btn btn-success btn-sm" onClick={() => setConfirmBulk('enable')}>Enable {selected.length}</button>
                <button className="btn btn-secondary btn-sm" onClick={() => setConfirmBulk('disable')}>Disable {selected.length}</button>
                <button className="btn btn-danger btn-sm" onClick={() => setConfirmBulk('archive')}>Archive {selected.length}</button>
                <button className="btn btn-ghost btn-sm" onClick={() => setSelected([])}>Clear</button>
              </>
            )}
          </div>

          {isLoading ? <SkeletonTable rows={8} cols={8} /> : !items.length ? (
            <EmptyState title="No discounts found" message="Create your first discount or promotion to get started." />
          ) : (
            <div className="admin-table-wrapper">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th><input type="checkbox" checked={selected.length === items.length && items.length > 0} onChange={toggleAll} /></th>
                    <th>Discount</th>
                    <th>Code</th>
                    <th>Type</th>
                    <th>Value</th>
                    <th>Usage</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((d) => (
                    <tr key={d.id}>
                      <td><input type="checkbox" checked={selected.includes(d.id)} onChange={() => toggleItem(d.id)} /></td>
                      <td>
                        <div className="admin-user-name">{d.title}</div>
                        {d.public_offer_title && <div className="admin-user-email">{d.public_offer_title}</div>}
                      </td>
                      <td>{d.code ? <code style={{ fontSize: 12 }}>{d.code}</code> : <span style={{ color: 'var(--text-tertiary)' }}>Automatic</span>}</td>
                      <td>{COUPON_TYPES.find((t) => t.value === d.coupon_type)?.label ?? d.coupon_type}</td>
                      <td>
                        {d.coupon_type === 'percentage' ? `${d.discount_value}%` :
                          d.coupon_type === 'fixed_price' ? `→ ${formatCurrency(d.discount_value)}` :
                          formatCurrency(d.discount_value)}
                      </td>
                      <td>{d.times_used}{d.total_usage_limit ? ` / ${d.total_usage_limit}` : ''}</td>
                      <td><StatusBadge status={d.effective_status ?? d.admin_status} /></td>
                      <td>
                        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                          <button className="btn btn-secondary btn-sm" onClick={() => openEdit(d)}>Edit</button>
                          <button className="btn btn-secondary btn-sm" onClick={() => setConfirmAction({ type: 'duplicate', id: d.id, name: d.title })}>Duplicate</button>
                          {d.admin_status !== 'archived' && (
                            <button
                              className="btn btn-secondary btn-sm"
                              onClick={() => toggleActiveMutation.mutate({ id: d.id, is_active: !d.is_active })}
                            >
                              {d.is_active ? 'Disable' : 'Enable'}
                            </button>
                          )}
                          {d.admin_status !== 'archived' && (
                            <button className="btn btn-danger btn-sm" onClick={() => setConfirmAction({ type: 'archive', id: d.id, name: d.title })}>Archive</button>
                          )}
                        </div>
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

      <Modal
        open={formOpen}
        onClose={() => setFormOpen(false)}
        title={editItem ? 'Edit Discount' : 'New Discount'}
        size="lg"
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setFormOpen(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={() => saveMutation.mutate()} disabled={!form.title || saveMutation.isPending}>
              {saveMutation.isPending ? 'Saving…' : 'Save'}
            </button>
          </>
        }
      >
        <div className="form-group">
          <label className="form-label required">Discount Name</label>
          <input className="form-control" value={form.title} onChange={set('title')} placeholder="Diwali 2026 15% Off" />
        </div>
        <div className="form-group">
          <label className="form-label">Public Offer Title</label>
          <input className="form-control" value={form.public_offer_title} onChange={set('public_offer_title')} placeholder="Diwali Dhamaka — 15% OFF!" />
        </div>
        <div className="form-group">
          <label className="form-label">Internal Description</label>
          <textarea className="form-control" rows={2} value={form.description} onChange={set('description')} />
        </div>

        <div className="form-row-2">
          <div className="form-group">
            <label className="form-label required">Mode</label>
            <select className="form-control" value={form.mode} onChange={set('mode')}>
              <option value="automatic">Automatic (no code required)</option>
              <option value="code">Coupon Code</option>
            </select>
          </div>
          {form.mode === 'code' && (
            <div className="form-group">
              <label className="form-label required">Coupon Code</label>
              <input className="form-control" value={form.code} onChange={set('code')} placeholder="DIWALI15" />
            </div>
          )}
        </div>

        <div className="form-row-2">
          <div className="form-group">
            <label className="form-label required">Discount Type</label>
            <select className="form-control" value={form.coupon_type} onChange={set('coupon_type')}>
              {COUPON_TYPES.map((t) => <option key={t.value} value={t.value} disabled={t.disabled}>{t.label}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label required">
              {form.coupon_type === 'fixed_price' ? 'Target Price (₹)' : form.coupon_type === 'percentage' ? 'Discount Value (%)' : 'Discount Value (₹)'}
            </label>
            <input className="form-control" type="number" value={form.discount_value} onChange={set('discount_value')} />
          </div>
        </div>

        <div className="form-row-2">
          <div className="form-group">
            <label className="form-label">Maximum Discount Amount (₹)</label>
            <input className="form-control" type="number" value={form.max_discount_amount} onChange={set('max_discount_amount')} placeholder="Uncapped if blank" />
          </div>
          <div className="form-group">
            <label className="form-label">Priority</label>
            <input className="form-control" type="number" value={form.priority} onChange={set('priority')} />
            <div className="form-hint">Lower number = preferred first among non-stackable discounts.</div>
          </div>
        </div>

        <div className="form-check">
          <input type="checkbox" id="is_stackable" checked={form.is_stackable} onChange={set('is_stackable')} />
          <label htmlFor="is_stackable">Allow stacking with other discounts</label>
        </div>

        <div className="form-group">
          <label className="form-label required">Applicable Scope</label>
          <select className="form-control" value={form.applicability} onChange={set('applicability')}>
            {APPLICABILITY_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>

        <div className="form-row-2">
          <div className="form-group">
            <label className="form-label">Vendor(s)</label>
            <MultiSelect options={vendorOptions} value={form.applicable_vendor_ids} onChange={setList('applicable_vendor_ids')} placeholder="Search vendors…" />
          </div>
          <div className="form-group">
            <label className="form-label">Package(s)</label>
            <MultiSelect options={packageOptions} value={form.applicable_package_ids} onChange={setList('applicable_package_ids')} placeholder="Search packages…" />
          </div>
        </div>
        <div className="form-row-2">
          <div className="form-group">
            <label className="form-label">Occasion(s)</label>
            <MultiSelect options={occasionOptions} value={form.applicable_occasion_ids} onChange={setList('applicable_occasion_ids')} placeholder="Search occasions…" />
          </div>
          <div className="form-group">
            <label className="form-label">Occasion Categories</label>
            <MultiSelect options={OCCASION_CATEGORY_OPTIONS} value={form.applicable_occasion_categories} onChange={setList('applicable_occasion_categories')} placeholder="Select categories…" />
          </div>
        </div>
        <div className="form-group">
          <label className="form-label">Membership Tier(s)</label>
          <MultiSelect options={membershipTierOptions} value={form.eligible_membership_tiers} onChange={setList('eligible_membership_tiers')} placeholder="Select tiers…" />
        </div>

        <div className="form-check">
          <input type="checkbox" id="first_booking_only" checked={form.first_booking_only} onChange={set('first_booking_only')} />
          <label htmlFor="first_booking_only">First booking only</label>
        </div>
        <div className="form-check">
          <input type="checkbox" id="repeat_customers_only" checked={form.repeat_customers_only} onChange={set('repeat_customers_only')} />
          <label htmlFor="repeat_customers_only">Repeat customers only</label>
        </div>
        <div className="form-check">
          <input type="checkbox" id="referral_users_only" checked={form.referral_users_only} onChange={set('referral_users_only')} />
          <label htmlFor="referral_users_only">Referral users only</label>
        </div>

        <div className="form-row-2" style={{ marginTop: 16 }}>
          <div className="form-group">
            <label className="form-label">Minimum Booking Amount (₹)</label>
            <input className="form-control" type="number" value={form.min_order_value} onChange={set('min_order_value')} />
          </div>
          <div className="form-group">
            <label className="form-label">Minimum Package Value (₹)</label>
            <input className="form-control" type="number" value={form.min_package_value} onChange={set('min_package_value')} />
          </div>
        </div>

        <div className="form-row-2">
          <div className="form-group">
            <label className="form-label">Total Usage Limit</label>
            <input className="form-control" type="number" value={form.total_usage_limit} onChange={set('total_usage_limit')} placeholder="Unlimited if blank" />
          </div>
          <div className="form-group">
            <label className="form-label">Per-User Limit</label>
            <input className="form-control" type="number" value={form.per_user_limit} onChange={set('per_user_limit')} placeholder="Unlimited if blank" />
          </div>
        </div>
        <div className="form-group">
          <label className="form-label">Max Uses Per Day</label>
          <input className="form-control" type="number" value={form.max_uses_per_day} onChange={set('max_uses_per_day')} placeholder="Unlimited if blank" />
        </div>

        <div className="form-row-2">
          <div className="form-group">
            <label className="form-label required">Start Date &amp; Time</label>
            <input className="form-control" type="datetime-local" value={form.valid_from} onChange={set('valid_from')} />
          </div>
          <div className="form-group">
            <label className="form-label">End Date &amp; Time</label>
            <input className="form-control" type="datetime-local" value={form.valid_until} onChange={set('valid_until')} placeholder="Never expires if blank" />
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">Banner Image</label>
          <ImageUploadField value={form.banner_image_url} onChange={(url) => setForm((f) => ({ ...f, banner_image_url: url }))} usage="discount_banner" label="Upload" />
        </div>
        <div className="form-group">
          <label className="form-label">Theme Color</label>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <input type="color" value={form.theme_color_hex || '#C8A96E'} onChange={(e) => setForm((f) => ({ ...f, theme_color_hex: e.target.value }))} style={{ width: 44, height: 36, padding: 2 }} />
            <input className="form-control" value={form.theme_color_hex} onChange={set('theme_color_hex')} placeholder="Optional, e.g. #C8A96E" />
          </div>
        </div>
        <div className="form-group">
          <label className="form-label">Terms &amp; Conditions</label>
          <textarea className="form-control" rows={2} value={form.terms_and_conditions} onChange={set('terms_and_conditions')} />
        </div>

        <div className="form-group">
          <label className="form-label required">Status</label>
          <select className="form-control" value={form.admin_status} onChange={set('admin_status')}>
            <option value="draft">Draft</option>
            <option value="published">Published</option>
            <option value="paused">Paused</option>
            <option value="archived">Archived</option>
          </select>
          <div className="form-hint">
            When Published, the discount automatically becomes Scheduled/Active/Expired based on the date range above — no manual step needed.
          </div>
        </div>
      </Modal>

      <ConfirmDialog
        open={!!confirmAction}
        onClose={() => setConfirmAction(null)}
        onConfirm={handleConfirmAction}
        title={confirmAction?.type === 'archive' ? 'Archive Discount' : 'Duplicate Discount'}
        message={
          confirmAction?.type === 'archive'
            ? `Archive "${confirmAction?.name}"? It will be permanently excluded from evaluation.`
            : `Duplicate "${confirmAction?.name}" as a new draft?`
        }
        danger={confirmAction?.type === 'archive'}
        loading={archiveMutation.isPending || duplicateMutation.isPending}
      />

      <ConfirmDialog
        open={!!confirmBulk}
        onClose={() => setConfirmBulk('')}
        onConfirm={handleBulk}
        title={confirmBulk ? `Bulk ${confirmBulk.charAt(0).toUpperCase()}${confirmBulk.slice(1)}` : ''}
        message={`${confirmBulk} ${selected.length} discount(s)?`}
        danger={confirmBulk === 'archive'}
        loading={isBulkPending}
      />
    </div>
  );
}
