import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { membershipsApi } from '../../api';
import { formatDate, formatCurrency } from '../../utils/format';
import StatusBadge from '../../components/ui/StatusBadge';
import Pagination from '../../components/ui/Pagination';
import { SkeletonTable } from '../../components/ui/Skeleton';
import Modal, { ConfirmDialog } from '../../components/ui/Modal';
import { usePagination } from '../../hooks/usePagination';

function PlansSection() {
  const qc = useQueryClient();
  const [newOpen, setNewOpen] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [form, setForm] = useState({ name: '', price: '', billing_period: 'monthly', features: '', description: '' });

  const { data: plans = [] } = useQuery({
    queryKey: ['memberships', 'plans'],
    queryFn: () => membershipsApi.listPlans(),
  });

  const saveMutation = useMutation({
    mutationFn: (body) => editItem ? membershipsApi.updatePlan(editItem.id, body) : membershipsApi.createPlan(body),
    onSuccess: () => {
      toast.success(editItem ? 'Plan updated' : 'Plan created');
      qc.invalidateQueries(['memberships', 'plans']);
      setNewOpen(false); setEditItem(null);
    },
    onError: () => toast.error('Save failed'),
  });

  const deactivateMutation = useMutation({
    mutationFn: (id) => membershipsApi.deactivatePlan(id),
    onSuccess: () => { toast.success('Plan deactivated'); qc.invalidateQueries(['memberships', 'plans']); },
    onError: () => toast.error('Failed'),
  });

  const openEdit = (plan) => {
    setEditItem(plan);
    setForm({ name: plan.name, price: plan.price, billing_period: plan.billing_period, features: plan.features?.join(', ') ?? '', description: plan.description ?? '' });
    setNewOpen(true);
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
        <button className="btn btn-primary" onClick={() => { setEditItem(null); setForm({ name:'', price:'', billing_period:'monthly', features:'', description:'' }); setNewOpen(true); }}>
          + New Plan
        </button>
      </div>
      <div className="admin-table-wrapper">
        <table className="admin-table">
          <thead>
            <tr><th>Name</th><th>Price</th><th>Billing</th><th>Active Subscribers</th><th>Actions</th></tr>
          </thead>
          <tbody>
            {plans.map((p) => (
              <tr key={p.id}>
                <td>
                  <div className="admin-user-name">{p.name}</div>
                  <div className="admin-user-email">{p.description ?? ''}</div>
                </td>
                <td>{formatCurrency(p.price)}</td>
                <td>{p.billing_period}</td>
                <td>{p.active_subscriber_count ?? 0}</td>
                <td>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <button className="btn btn-secondary btn-sm" onClick={() => openEdit(p)}>Edit</button>
                    <button className="btn btn-danger btn-sm" onClick={() => deactivateMutation.mutate(p.id)}>Deactivate</button>
                  </div>
                </td>
              </tr>
            ))}
            {!plans.length && <tr><td colSpan={5} className="admin-table-empty">No plans</td></tr>}
          </tbody>
        </table>
      </div>

      <Modal open={newOpen} onClose={() => setNewOpen(false)} title={editItem ? 'Edit Plan' : 'New Plan'}
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setNewOpen(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={() => saveMutation.mutate({ ...form, price: parseFloat(form.price), features: form.features.split(',').map(s => s.trim()).filter(Boolean) })} disabled={!form.name || !form.price || saveMutation.isPending}>
              {saveMutation.isPending ? 'Saving…' : 'Save'}
            </button>
          </>
        }
      >
        <div className="form-row-2">
          <div className="form-group">
            <label className="form-label required">Plan Name</label>
            <input className="form-control" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder="Gold" />
          </div>
          <div className="form-group">
            <label className="form-label required">Price (INR)</label>
            <input className="form-control" type="number" value={form.price} onChange={e => setForm(f => ({ ...f, price: e.target.value }))} />
          </div>
        </div>
        <div className="form-group">
          <label className="form-label">Billing Period</label>
          <select className="form-control" value={form.billing_period} onChange={e => setForm(f => ({ ...f, billing_period: e.target.value }))}>
            <option value="monthly">Monthly</option>
            <option value="quarterly">Quarterly</option>
            <option value="yearly">Yearly</option>
          </select>
        </div>
        <div className="form-group">
          <label className="form-label">Description</label>
          <input className="form-control" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
        </div>
        <div className="form-group">
          <label className="form-label">Features (comma-separated)</label>
          <textarea className="form-control" rows={3} value={form.features} onChange={e => setForm(f => ({ ...f, features: e.target.value }))} placeholder="Unlimited bookings, Priority support, …" />
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
    onSuccess: () => { toast.success('Membership expired'); qc.invalidateQueries(['memberships', 'all']); },
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
        isLoading ? <SkeletonTable rows={8} cols={5} /> : (
          <div className="admin-table-wrapper">
            <table className="admin-table">
              <thead>
                <tr><th>User</th><th>Plan</th><th>Status</th><th>Started</th><th>Expires</th><th>Actions</th></tr>
              </thead>
              <tbody>
                {items.map((m) => (
                  <tr key={m.id}>
                    <td>{m.user?.name ?? m.user_id?.slice(0, 8)}</td>
                    <td>{m.plan?.name ?? m.plan_name}</td>
                    <td><StatusBadge status={m.status} /></td>
                    <td>{formatDate(m.started_at ?? m.created_at)}</td>
                    <td>{m.expires_at ? formatDate(m.expires_at) : 'Never'}</td>
                    <td>
                      {m.status === 'active' && (
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
