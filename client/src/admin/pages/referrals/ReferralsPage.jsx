import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { referralsApi } from '../../api';
import Pagination from '../../components/ui/Pagination';
import { SkeletonCard, SkeletonLine } from '../../components/ui/Skeleton';
import EmptyState from '../../components/ui/EmptyState';
import StatusBadge from '../../components/ui/StatusBadge';
import Modal from '../../components/ui/Modal';

const EMPTY_RULE_FORM = {
  referrals_required: '10',
  discount_percentage: '5',
  applicable_plan_count: '5',
  min_plan_price: '5000',
  is_active: true,
};

function MilestoneRulesSection() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [form, setForm] = useState(EMPTY_RULE_FORM);

  const { data: rules = [], isLoading } = useQuery({
    queryKey: ['referrals', 'milestone-rules'],
    queryFn: () => referralsApi.listMilestoneRules(),
  });

  const saveMutation = useMutation({
    mutationFn: (body) => (editItem ? referralsApi.updateMilestoneRule(editItem.id, body) : referralsApi.createMilestoneRule(body)),
    onSuccess: () => {
      toast.success(editItem ? 'Rule updated' : 'Rule created');
      qc.invalidateQueries({ queryKey: ['referrals', 'milestone-rules'] });
      setOpen(false);
      setEditItem(null);
    },
    onError: (err) => toast.error(err?.response?.data?.message || 'Save failed'),
  });

  const openNew = () => { setEditItem(null); setForm(EMPTY_RULE_FORM); setOpen(true); };
  const openEdit = (rule) => {
    setEditItem(rule);
    setForm({
      referrals_required: String(rule.referrals_required),
      discount_percentage: String(rule.discount_percentage),
      applicable_plan_count: String(rule.applicable_plan_count),
      min_plan_price: String(rule.min_plan_price),
      is_active: rule.is_active,
    });
    setOpen(true);
  };

  const set = (key) => (e) => {
    const value = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
    setForm((f) => ({ ...f, [key]: value }));
  };

  const save = () => {
    saveMutation.mutate({
      referrals_required: parseInt(form.referrals_required, 10) || 1,
      discount_percentage: parseFloat(form.discount_percentage) || 0,
      applicable_plan_count: parseInt(form.applicable_plan_count, 10) || 1,
      min_plan_price: parseFloat(form.min_plan_price) || 0,
      is_active: form.is_active,
    });
  };

  return (
    <div className="admin-card" style={{ marginBottom: 24 }}>
      <div className="admin-card-header">
        <h2 className="admin-card-title">Referral Milestone Rewards</h2>
        <button className="btn btn-primary" onClick={openNew}>+ New Rule</button>
      </div>
      {isLoading ? (
        <div style={{ padding: 24 }}><SkeletonLine height={44} /></div>
      ) : rules.length === 0 ? (
        <EmptyState icon="🎯" title="No milestone rules yet" description="Create one to reward customers for referring friends." />
      ) : (
        <div className="admin-table-wrapper">
          <table className="admin-table">
            <thead>
              <tr><th>Every</th><th>Discount</th><th>Applies To</th><th>Min Plan Price</th><th>Active</th><th>Actions</th></tr>
            </thead>
            <tbody>
              {rules.map((r) => (
                <tr key={r.id}>
                  <td>{r.referrals_required} referrals</td>
                  <td>{r.discount_percentage}%</td>
                  <td>next {r.applicable_plan_count} plan(s)</td>
                  <td>₹{Number(r.min_plan_price).toLocaleString()}+</td>
                  <td>{r.is_active ? 'Yes' : 'No'}</td>
                  <td><button className="btn btn-secondary btn-sm" onClick={() => openEdit(r)}>Edit</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title={editItem ? 'Edit Milestone Rule' : 'New Milestone Rule'}
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setOpen(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={save} disabled={saveMutation.isPending}>
              {saveMutation.isPending ? 'Saving…' : 'Save'}
            </button>
          </>
        }
      >
        <div className="form-row-2">
          <div className="form-group">
            <label className="form-label required">For every N referrals</label>
            <input className="form-control" type="number" value={form.referrals_required} onChange={set('referrals_required')} />
          </div>
          <div className="form-group">
            <label className="form-label required">Discount %</label>
            <input className="form-control" type="number" value={form.discount_percentage} onChange={set('discount_percentage')} />
          </div>
        </div>
        <div className="form-row-2">
          <div className="form-group">
            <label className="form-label required">Applies to next N plans</label>
            <input className="form-control" type="number" value={form.applicable_plan_count} onChange={set('applicable_plan_count')} />
          </div>
          <div className="form-group">
            <label className="form-label required">Plan must be at least (₹)</label>
            <input className="form-control" type="number" value={form.min_plan_price} onChange={set('min_plan_price')} />
          </div>
        </div>
        <label><input type="checkbox" checked={form.is_active} onChange={set('is_active')} /> Active (making this active deactivates any other active rule)</label>
      </Modal>
    </div>
  );
}

export default function ReferralsPage() {
  const [page, setPage] = useState(1);
  const perPage = 20;

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['referrals', 'stats'],
    queryFn: () => referralsApi.stats(),
  });

  const { data, isLoading } = useQuery({
    queryKey: ['referrals', 'list', { page, perPage }],
    queryFn: () => referralsApi.list({ page, per_page: perPage }),
  });

  const referrals = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / perPage);

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Referrals</h1>
          <p className="admin-page-subtitle">Track referral codes, conversions, and reward payouts.</p>
        </div>
      </div>

      {/* Stats row */}
      <div className="admin-stats-grid" style={{ marginBottom: 24 }}>
        {statsLoading ? (
          Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} height={80} />)
        ) : (
          <>
            <div className="admin-stat-card">
              <div className="stat-value">{stats?.total_referrals ?? 0}</div>
              <div className="stat-label">Total Referrals</div>
            </div>
            <div className="admin-stat-card">
              <div className="stat-value">{stats?.successful_referrals ?? 0}</div>
              <div className="stat-label">Successful</div>
            </div>
            <div className="admin-stat-card">
              <div className="stat-value">{stats?.pending_rewards ?? 0}</div>
              <div className="stat-label">Pending Rewards</div>
            </div>
            <div className="admin-stat-card">
              <div className="stat-value">₹{(stats?.total_reward_value ?? 0).toLocaleString()}</div>
              <div className="stat-label">Total Rewards Issued</div>
            </div>
          </>
        )}
      </div>

      <MilestoneRulesSection />

      {/* Referrals table */}
      <div className="admin-card">
        <div className="admin-card-header">
          <h2 className="admin-card-title">All Referrals</h2>
          <span className="admin-badge">{total} total</span>
        </div>

        {isLoading ? (
          <div style={{ padding: 24 }}>
            {Array.from({ length: 8 }).map((_, i) => (
              <SkeletonLine key={i} height={44} />
            ))}
          </div>
        ) : referrals.length === 0 ? (
          <EmptyState
            icon="🎁"
            title="No referrals yet"
            description="Referral activity will appear here once customers start sharing their codes."
          />
        ) : (
          <>
            <div className="admin-table-wrapper">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Referrer</th>
                    <th>Referee</th>
                    <th>Code</th>
                    <th>Status</th>
                    <th>Reward</th>
                    <th>Date</th>
                  </tr>
                </thead>
                <tbody>
                  {referrals.map((r) => (
                    <tr key={r.id}>
                      <td>
                        <div style={{ fontWeight: 600 }}>{r.referrer?.full_name ?? '—'}</div>
                        <div style={{ fontSize: 12, color: 'var(--ink-3)' }}>{r.referrer?.phone ?? r.referrer?.email ?? ''}</div>
                      </td>
                      <td>
                        <div style={{ fontWeight: 600 }}>{r.referred?.full_name ?? '—'}</div>
                        <div style={{ fontSize: 12, color: 'var(--ink-3)' }}>{r.referred?.phone ?? r.referred?.email ?? ''}</div>
                      </td>
                      <td>
                        <code style={{ fontSize: 12, background: 'var(--surface-2)', padding: '2px 6px', borderRadius: 4 }}>
                          {r.referral_code ?? '—'}
                        </code>
                      </td>
                      <td>
                        <StatusBadge status={r.status} />
                      </td>
                      <td>
                        {r.reward_value ? (
                          <span style={{ fontWeight: 700, color: 'var(--leaf)' }}>
                            ₹{r.reward_value.toLocaleString()}
                          </span>
                        ) : '—'}
                      </td>
                      <td style={{ color: 'var(--ink-3)', fontSize: 13 }}>
                        {r.created_at ? new Date(r.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {totalPages > 1 && (
              <div style={{ padding: '16px 24px', borderTop: '1px solid var(--line)' }}>
                <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
