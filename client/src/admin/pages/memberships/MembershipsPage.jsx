import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { membershipsApi } from '../../api';
import { formatDate, formatCurrency } from '../../utils/format';
import StatusBadge from '../../components/ui/StatusBadge';
import Pagination from '../../components/ui/Pagination';
import { SkeletonTable } from '../../components/ui/Skeleton';
import Modal from '../../components/ui/Modal';
import { usePagination } from '../../hooks/usePagination';

const TIERS = ['free', 'silver', 'gold', 'platinum'];

const EMPTY_FORM = {
  tier: 'silver',
  name: '',
  slug: '',
  tagline: '',
  description: '',
  monthly_price: '',
  yearly_price: '',
  validity_days: '',
  cashback_percentage: '0',
  discount_percentage: '0',
  reward_multiplier: '1',
  wallet_bonus: '0',
  free_invitations_count: '0',
  priority_booking: false,
  has_exclusive_packages: false,
  cancellation_protection: false,
  customer_support_priority: '1',
  can_upgrade_to_tier: '',
  can_downgrade_to_tier: '',
  is_active: true,
  display_order: '0',
};

function slugify(name) {
  return name.toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
}

function planToForm(plan) {
  return {
    ...EMPTY_FORM,
    tier: plan.tier,
    name: plan.name,
    slug: plan.slug,
    tagline: plan.tagline ?? '',
    description: plan.description ?? '',
    monthly_price: String(plan.monthly_price ?? ''),
    yearly_price: String(plan.yearly_price ?? ''),
    validity_days: plan.validity_days != null ? String(plan.validity_days) : '',
    cashback_percentage: String(plan.cashback_percentage ?? '0'),
    discount_percentage: String(plan.discount_percentage ?? '0'),
    reward_multiplier: String(plan.reward_multiplier ?? '1'),
    wallet_bonus: String(plan.wallet_bonus ?? '0'),
    free_invitations_count: String(plan.free_invitations_count ?? '0'),
    priority_booking: !!plan.priority_booking,
    has_exclusive_packages: !!plan.has_exclusive_packages,
    cancellation_protection: !!plan.cancellation_protection,
    customer_support_priority: String(plan.customer_support_priority ?? '1'),
    can_upgrade_to_tier: plan.can_upgrade_to_tier ?? '',
    can_downgrade_to_tier: plan.can_downgrade_to_tier ?? '',
    is_active: plan.is_active,
    display_order: String(plan.display_order ?? '0'),
  };
}

function formToPayload(form) {
  return {
    tier: form.tier,
    name: form.name.trim(),
    slug: form.slug.trim() || slugify(form.name),
    tagline: form.tagline.trim() || null,
    description: form.description.trim() || null,
    monthly_price: parseFloat(form.monthly_price) || 0,
    yearly_price: parseFloat(form.yearly_price) || 0,
    validity_days: form.validity_days.trim() ? parseInt(form.validity_days, 10) : null,
    cashback_percentage: parseFloat(form.cashback_percentage) || 0,
    discount_percentage: parseFloat(form.discount_percentage) || 0,
    reward_multiplier: parseFloat(form.reward_multiplier) || 1,
    wallet_bonus: parseFloat(form.wallet_bonus) || 0,
    free_invitations_count: parseInt(form.free_invitations_count, 10) || 0,
    priority_booking: form.priority_booking,
    has_exclusive_packages: form.has_exclusive_packages,
    cancellation_protection: form.cancellation_protection,
    customer_support_priority: parseInt(form.customer_support_priority, 10) || 1,
    can_upgrade_to_tier: form.can_upgrade_to_tier || null,
    can_downgrade_to_tier: form.can_downgrade_to_tier || null,
    is_active: form.is_active,
    display_order: parseInt(form.display_order, 10) || 0,
  };
}

function PlansSection() {
  const qc = useQueryClient();
  const [newOpen, setNewOpen] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);

  const { data: plans = [] } = useQuery({
    queryKey: ['memberships', 'plans'],
    queryFn: () => membershipsApi.listPlans(),
  });

  const saveMutation = useMutation({
    mutationFn: (body) => (editItem ? membershipsApi.updatePlan(editItem.id, body) : membershipsApi.createPlan(body)),
    onSuccess: () => {
      toast.success(editItem ? 'Plan updated' : 'Plan created');
      qc.invalidateQueries({ queryKey: ['memberships', 'plans'] });
      setNewOpen(false);
      setEditItem(null);
    },
    onError: (err) => toast.error(err?.response?.data?.message || 'Save failed'),
  });

  const deactivateMutation = useMutation({
    mutationFn: (id) => membershipsApi.deactivatePlan(id),
    onSuccess: () => {
      toast.success('Plan deactivated');
      qc.invalidateQueries({ queryKey: ['memberships', 'plans'] });
    },
    onError: () => toast.error('Failed'),
  });

  const openNew = () => {
    setEditItem(null);
    setForm(EMPTY_FORM);
    setNewOpen(true);
  };

  const openEdit = (plan) => {
    setEditItem(plan);
    setForm(planToForm(plan));
    setNewOpen(true);
  };

  const set = (key) => (e) => {
    const value = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
    setForm((f) => ({ ...f, [key]: value }));
  };

  const canSave = form.name.trim() && form.monthly_price !== '' && form.yearly_price !== '';

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
        <button className="btn btn-primary" onClick={openNew}>+ New Plan</button>
      </div>
      <div className="admin-table-wrapper">
        <table className="admin-table">
          <thead>
            <tr><th>Name</th><th>Tier</th><th>Monthly</th><th>Yearly</th><th>Active</th><th>Actions</th></tr>
          </thead>
          <tbody>
            {plans.map((p) => (
              <tr key={p.id}>
                <td>
                  <div className="admin-user-name">{p.name}</div>
                  <div className="admin-user-email">{p.tagline ?? p.slug}</div>
                </td>
                <td style={{ textTransform: 'capitalize' }}>{p.tier}</td>
                <td>{formatCurrency(p.monthly_price)}</td>
                <td>{formatCurrency(p.yearly_price)}</td>
                <td>{p.is_active ? 'Yes' : 'No'}</td>
                <td>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <button className="btn btn-secondary btn-sm" onClick={() => openEdit(p)}>Edit</button>
                    {p.is_active && (
                      <button className="btn btn-danger btn-sm" onClick={() => deactivateMutation.mutate(p.id)}>Deactivate</button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
            {!plans.length && <tr><td colSpan={6} className="admin-table-empty">No plans</td></tr>}
          </tbody>
        </table>
      </div>

      <Modal
        open={newOpen}
        onClose={() => setNewOpen(false)}
        title={editItem ? 'Edit Plan' : 'New Plan'}
        size="lg"
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setNewOpen(false)}>Cancel</button>
            <button
              className="btn btn-primary"
              onClick={() => saveMutation.mutate(formToPayload(form))}
              disabled={!canSave || saveMutation.isPending}
            >
              {saveMutation.isPending ? 'Saving…' : 'Save'}
            </button>
          </>
        }
      >
        <div className="form-row-2">
          <div className="form-group">
            <label className="form-label required">Tier</label>
            <select className="form-control" value={form.tier} onChange={set('tier')}>
              {TIERS.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label required">Plan Name</label>
            <input className="form-control" value={form.name} onChange={set('name')} placeholder="Gold" />
          </div>
        </div>
        <div className="form-row-2">
          <div className="form-group">
            <label className="form-label">Slug</label>
            <input className="form-control" value={form.slug} onChange={set('slug')} placeholder={slugify(form.name) || 'gold-annual'} />
          </div>
          <div className="form-group">
            <label className="form-label">Tagline</label>
            <input className="form-control" value={form.tagline} onChange={set('tagline')} />
          </div>
        </div>
        <div className="form-group">
          <label className="form-label">Description</label>
          <textarea className="form-control" rows={2} value={form.description} onChange={set('description')} />
        </div>
        <div className="form-row-2">
          <div className="form-group">
            <label className="form-label required">Monthly Price (INR)</label>
            <input className="form-control" type="number" value={form.monthly_price} onChange={set('monthly_price')} />
          </div>
          <div className="form-group">
            <label className="form-label required">Yearly Price (INR)</label>
            <input className="form-control" type="number" value={form.yearly_price} onChange={set('yearly_price')} />
          </div>
        </div>
        <div className="form-row-2">
          <div className="form-group">
            <label className="form-label">Validity (days, blank = perpetual)</label>
            <input className="form-control" type="number" value={form.validity_days} onChange={set('validity_days')} />
          </div>
          <div className="form-group">
            <label className="form-label">Display Order</label>
            <input className="form-control" type="number" value={form.display_order} onChange={set('display_order')} />
          </div>
        </div>
        <div className="form-row-2">
          <div className="form-group">
            <label className="form-label">Cashback %</label>
            <input className="form-control" type="number" value={form.cashback_percentage} onChange={set('cashback_percentage')} />
          </div>
          <div className="form-group">
            <label className="form-label">Discount %</label>
            <input className="form-control" type="number" value={form.discount_percentage} onChange={set('discount_percentage')} />
          </div>
        </div>
        <div className="form-row-2">
          <div className="form-group">
            <label className="form-label">Reward Multiplier</label>
            <input className="form-control" type="number" step="0.1" value={form.reward_multiplier} onChange={set('reward_multiplier')} />
          </div>
          <div className="form-group">
            <label className="form-label">Wallet Bonus (INR, one-time on activation)</label>
            <input className="form-control" type="number" value={form.wallet_bonus} onChange={set('wallet_bonus')} />
          </div>
        </div>
        <div className="form-row-2">
          <div className="form-group">
            <label className="form-label">Free Invitations</label>
            <input className="form-control" type="number" value={form.free_invitations_count} onChange={set('free_invitations_count')} />
          </div>
          <div className="form-group">
            <label className="form-label">Support Priority (1=standard, 3=dedicated)</label>
            <select className="form-control" value={form.customer_support_priority} onChange={set('customer_support_priority')}>
              <option value="1">1 — Standard</option>
              <option value="2">2 — Priority</option>
              <option value="3">3 — Dedicated</option>
            </select>
          </div>
        </div>
        <div className="form-row-2">
          <div className="form-group">
            <label className="form-label">Can Upgrade To</label>
            <select className="form-control" value={form.can_upgrade_to_tier} onChange={set('can_upgrade_to_tier')}>
              <option value="">None</option>
              {TIERS.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Can Downgrade To</label>
            <select className="form-control" value={form.can_downgrade_to_tier} onChange={set('can_downgrade_to_tier')}>
              <option value="">None</option>
              {TIERS.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
        </div>
        <div className="form-group" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <label><input type="checkbox" checked={form.priority_booking} onChange={set('priority_booking')} /> Priority booking</label>
          <label><input type="checkbox" checked={form.has_exclusive_packages} onChange={set('has_exclusive_packages')} /> Exclusive packages</label>
          <label><input type="checkbox" checked={form.cancellation_protection} onChange={set('cancellation_protection')} /> Cancellation fee waiver</label>
          <label><input type="checkbox" checked={form.is_active} onChange={set('is_active')} /> Active (visible to customers)</label>
        </div>
      </Modal>
    </div>
  );
}

export default function MembershipsPage() {
  const { page, perPage, setPage } = usePagination();
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState('active');

  const { data, isLoading } = useQuery({
    queryKey: ['memberships', 'all', { page, perPage }],
    queryFn: () => membershipsApi.listAll({ page, per_page: perPage }),
    enabled: activeTab === 'active',
  });

  const expireMutation = useMutation({
    mutationFn: (id) => membershipsApi.forceExpire(id),
    onSuccess: () => { toast.success('Membership expired'); qc.invalidateQueries({ queryKey: ['memberships', 'all'] }); },
    onError: () => toast.error('Failed'),
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const pages = data?.pages ?? 1;

  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <h1>Membership Management</h1>
          <p>Manage plans and user subscriptions</p>
        </div>
      </div>

      <div className="admin-tabs">
        {['active', 'plans'].map(t => (
          <button key={t} className={`admin-tab${activeTab === t ? ' active' : ''}`} onClick={() => setActiveTab(t)}>
            {t === 'active' ? 'All Memberships' : 'Plans'}
          </button>
        ))}
      </div>

      {activeTab === 'active' && (
        isLoading ? <SkeletonTable rows={8} cols={6} /> : (
          <div className="admin-table-wrapper">
            <table className="admin-table">
              <thead>
                <tr><th>User</th><th>Tier</th><th>Status</th><th>Activated</th><th>Expires</th><th>Actions</th></tr>
              </thead>
              <tbody>
                {items.map((m) => (
                  <tr key={m.id}>
                    <td><code style={{ fontSize: 11 }}>{m.user_id?.slice(0, 8)}</code></td>
                    <td style={{ textTransform: 'capitalize' }}>{m.tier ?? '—'}</td>
                    <td><StatusBadge status={m.membership_status} /></td>
                    <td>{m.activated_at ? formatDate(m.activated_at) : '—'}</td>
                    <td>{m.expires_at ? formatDate(m.expires_at) : 'Never'}</td>
                    <td>
                      {(m.membership_status === 'active' || m.membership_status === 'grace_period') && (
                        <button className="btn btn-danger btn-sm" onClick={() => expireMutation.mutate(m.id)}>Force Expire</button>
                      )}
                    </td>
                  </tr>
                ))}
                {!items.length && <tr><td colSpan={6} className="admin-table-empty">No memberships</td></tr>}
              </tbody>
            </table>
            <Pagination page={page} pages={pages} total={total} perPage={perPage} onChange={setPage} />
          </div>
        )
      )}

      {activeTab === 'plans' && <PlansSection />}
    </div>
  );
}
