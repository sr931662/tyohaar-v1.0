import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { automationApi } from '../../api';
import { formatDateTime } from '../../utils/format';
import StatusBadge from '../../components/ui/StatusBadge';
import { SkeletonTable } from '../../components/ui/Skeleton';
import Modal, { ConfirmDialog } from '../../components/ui/Modal';

const TRIGGER_TYPES = ['booking_created', 'booking_confirmed', 'booking_completed', 'booking_cancelled', 'payment_received', 'user_registered', 'vendor_approved', 'membership_expired'];
const ACTION_TYPES = ['send_notification', 'send_email', 'assign_membership', 'update_status'];

export default function AutomationPage() {
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState('rules');
  const [open, setOpen] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [deleteId, setDeleteId] = useState(null);
  const [form, setForm] = useState({ name: '', trigger_type: 'booking_created', action_type: 'send_notification', config: '{}', is_active: true });

  const { data: rules = [], isLoading } = useQuery({
    queryKey: ['automation', 'rules'],
    queryFn: () => automationApi.listRules(),
  });

  const { data: logs = [], isLoading: logsLoading } = useQuery({
    queryKey: ['automation', 'logs'],
    queryFn: () => automationApi.listLogs(),
    enabled: activeTab === 'logs',
  });

  const saveMutation = useMutation({
    mutationFn: (body) => {
      const payload = { ...body, config: JSON.parse(body.config || '{}') };
      return editItem ? automationApi.updateRule(editItem.id, payload) : automationApi.createRule(payload);
    },
    onSuccess: () => { toast.success(editItem ? 'Rule updated' : 'Rule created'); qc.invalidateQueries(['automation']); setOpen(false); setEditItem(null); },
    onError: () => toast.error('Save failed — check JSON config'),
  });

  const toggleMutation = useMutation({
    mutationFn: (id) => automationApi.toggleRule(id),
    onSuccess: () => { toast.success('Rule toggled'); qc.invalidateQueries(['automation', 'rules']); },
    onError: () => toast.error('Failed'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id) => automationApi.deleteRule(id),
    onSuccess: () => { toast.success('Deleted'); qc.invalidateQueries(['automation', 'rules']); setDeleteId(null); },
    onError: () => toast.error('Failed'),
  });

  const triggerMutation = useMutation({
    mutationFn: (id) => automationApi.manualTrigger(id),
    onSuccess: () => toast.success('Rule triggered manually'),
    onError: () => toast.error('Trigger failed'),
  });

  const openEdit = (r) => {
    setEditItem(r);
    setForm({ name: r.name, trigger_type: r.trigger_type, action_type: r.action_type, config: JSON.stringify(r.config ?? {}, null, 2), is_active: r.is_active ?? true });
    setOpen(true);
  };

  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <h1>Automation Engine</h1>
          <p>Create trigger-action rules and view execution logs</p>
        </div>
        {activeTab === 'rules' && (
          <button className="btn btn-primary" onClick={() => { setEditItem(null); setForm({ name:'', trigger_type:'booking_created', action_type:'send_notification', config:'{}', is_active:true }); setOpen(true); }}>
            + New Rule
          </button>
        )}
      </div>

      <div className="admin-tabs">
        <button className={`admin-tab${activeTab === 'rules' ? ' active' : ''}`} onClick={() => setActiveTab('rules')}>Rules</button>
        <button className={`admin-tab${activeTab === 'logs' ? ' active' : ''}`} onClick={() => setActiveTab('logs')}>Execution Logs</button>
      </div>

      {activeTab === 'rules' && (
        isLoading ? <SkeletonTable rows={6} cols={5} /> : (
          <div className="admin-table-wrapper">
            <table className="admin-table">
              <thead>
                <tr><th>Name</th><th>Trigger</th><th>Action</th><th>Status</th><th>Actions</th></tr>
              </thead>
              <tbody>
                {rules.map((r) => (
                  <tr key={r.id}>
                    <td><div className="admin-user-name">{r.name}</div></td>
                    <td><code style={{ fontSize: 11 }}>{r.trigger_type}</code></td>
                    <td><code style={{ fontSize: 11 }}>{r.action_type}</code></td>
                    <td><StatusBadge status={r.is_active ? 'active' : 'inactive'} /></td>
                    <td>
                      <div style={{ display: 'flex', gap: 6 }}>
                        <button className="btn btn-secondary btn-sm" onClick={() => openEdit(r)}>Edit</button>
                        <button className="btn btn-secondary btn-sm" onClick={() => toggleMutation.mutate(r.id)}>
                          {r.is_active ? 'Disable' : 'Enable'}
                        </button>
                        <button className="btn btn-secondary btn-sm" onClick={() => triggerMutation.mutate(r.id)} title="Manual trigger">▶</button>
                        <button className="btn btn-danger btn-sm" onClick={() => setDeleteId(r.id)}>Delete</button>
                      </div>
                    </td>
                  </tr>
                ))}
                {!rules.length && <tr><td colSpan={5} className="admin-table-empty">No automation rules</td></tr>}
              </tbody>
            </table>
          </div>
        )
      )}

      {activeTab === 'logs' && (
        logsLoading ? <SkeletonTable rows={10} cols={5} /> : (
          <div className="admin-table-wrapper">
            <table className="admin-table">
              <thead>
                <tr><th>Rule</th><th>Status</th><th>Triggered By</th><th>Duration</th><th>Timestamp</th></tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log.id}>
                    <td>{log.rule?.name ?? log.rule_id?.slice(0, 8)}</td>
                    <td><StatusBadge status={log.status} /></td>
                    <td style={{ fontSize: 12 }}>{log.triggered_by ?? 'System'}</td>
                    <td style={{ fontSize: 12 }}>{log.duration_ms != null ? `${log.duration_ms}ms` : '—'}</td>
                    <td style={{ fontSize: 12 }}>{formatDateTime(log.created_at)}</td>
                  </tr>
                ))}
                {!logs.length && <tr><td colSpan={5} className="admin-table-empty">No execution logs</td></tr>}
              </tbody>
            </table>
          </div>
        )
      )}

      <Modal open={open} onClose={() => setOpen(false)} title={editItem ? 'Edit Rule' : 'New Automation Rule'} size="lg"
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setOpen(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={() => saveMutation.mutate(form)} disabled={!form.name || saveMutation.isPending}>
              {saveMutation.isPending ? 'Saving…' : 'Save Rule'}
            </button>
          </>
        }
      >
        <div className="form-group"><label className="form-label required">Rule Name</label><input className="form-control" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder="Notify on booking confirmed" /></div>
        <div className="form-row-2">
          <div className="form-group">
            <label className="form-label">Trigger</label>
            <select className="form-control" value={form.trigger_type} onChange={e => setForm(f => ({ ...f, trigger_type: e.target.value }))}>
              {TRIGGER_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Action</label>
            <select className="form-control" value={form.action_type} onChange={e => setForm(f => ({ ...f, action_type: e.target.value }))}>
              {ACTION_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
        </div>
        <div className="form-group">
          <label className="form-label">Config (JSON)</label>
          <textarea className="form-control" rows={5} value={form.config} onChange={e => setForm(f => ({ ...f, config: e.target.value }))} style={{ fontFamily: 'monospace', fontSize: 12 }} />
          <div className="form-hint">Example: {`{"template_key": "booking_confirmed", "delay_seconds": 0}`}</div>
        </div>
        <div className="form-check">
          <input type="checkbox" id="rule_active" checked={form.is_active} onChange={e => setForm(f => ({ ...f, is_active: e.target.checked }))} />
          <label htmlFor="rule_active">Active</label>
        </div>
      </Modal>

      <ConfirmDialog open={!!deleteId} onClose={() => setDeleteId(null)} onConfirm={() => deleteMutation.mutate(deleteId)}
        title="Delete Rule" message="This automation rule will be permanently deleted." danger loading={deleteMutation.isPending} />
    </div>
  );
}
