import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { notificationsApi } from '../../api';
import { formatDateTime } from '../../utils/format';
import StatusBadge from '../../components/ui/StatusBadge';
import { SkeletonTable } from '../../components/ui/Skeleton';
import Modal, { ConfirmDialog } from '../../components/ui/Modal';

function TemplatesTab() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [deleteId, setDeleteId] = useState(null);
  const [form, setForm] = useState({ template_key: '', title: '', body: '', notification_category: 'system' });

  const { data: templates = [] } = useQuery({
    queryKey: ['notifications', 'templates'],
    queryFn: () => notificationsApi.listTemplates(),
  });

  const saveMutation = useMutation({
    mutationFn: (body) => editItem ? notificationsApi.updateTemplate(editItem.id, body) : notificationsApi.createTemplate(body),
    onSuccess: () => {
      toast.success(editItem ? 'Template updated' : 'Template created');
      qc.invalidateQueries(['notifications', 'templates']);
      setOpen(false); setEditItem(null);
    },
    onError: () => toast.error('Save failed'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id) => notificationsApi.deleteTemplate(id),
    onSuccess: () => { toast.success('Deleted'); qc.invalidateQueries(['notifications', 'templates']); setDeleteId(null); },
    onError: () => toast.error('Delete failed'),
  });

  const openEdit = (t) => {
    setEditItem(t);
    setForm({ template_key: t.template_key, title: t.title, body: t.body, notification_category: t.notification_category });
    setOpen(true);
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
        <button className="btn btn-primary" onClick={() => { setEditItem(null); setForm({ template_key:'', title:'', body:'', notification_category:'system' }); setOpen(true); }}>
          + New Template
        </button>
      </div>
      <div className="admin-table-wrapper">
        <table className="admin-table">
          <thead>
            <tr><th>Key</th><th>Title</th><th>Category</th><th>Actions</th></tr>
          </thead>
          <tbody>
            {templates.map((t) => (
              <tr key={t.id}>
                <td><code style={{ fontSize: 11 }}>{t.template_key}</code></td>
                <td>{t.title}</td>
                <td>{t.notification_category}</td>
                <td>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <button className="btn btn-secondary btn-sm" onClick={() => openEdit(t)}>Edit</button>
                    <button className="btn btn-danger btn-sm" onClick={() => setDeleteId(t.id)}>Delete</button>
                  </div>
                </td>
              </tr>
            ))}
            {!templates.length && <tr><td colSpan={4} className="admin-table-empty">No templates</td></tr>}
          </tbody>
        </table>
      </div>

      <Modal open={open} onClose={() => setOpen(false)} title={editItem ? 'Edit Template' : 'New Template'} size="lg"
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setOpen(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={() => saveMutation.mutate(form)} disabled={!form.template_key || !form.title || saveMutation.isPending}>
              {saveMutation.isPending ? 'Saving…' : 'Save'}
            </button>
          </>
        }
      >
        <div className="form-row-2">
          <div className="form-group">
            <label className="form-label required">Template Key</label>
            <input className="form-control" value={form.template_key} onChange={e => setForm(f => ({ ...f, template_key: e.target.value }))} placeholder="booking_confirmed" disabled={!!editItem} />
          </div>
          <div className="form-group">
            <label className="form-label">Category</label>
            <select className="form-control" value={form.notification_category} onChange={e => setForm(f => ({ ...f, notification_category: e.target.value }))}>
              <option value="system">System</option>
              <option value="booking">Booking</option>
              <option value="payment">Payment</option>
              <option value="promotion">Promotion</option>
              <option value="alert">Alert</option>
            </select>
          </div>
        </div>
        <div className="form-group">
          <label className="form-label required">Title</label>
          <input className="form-control" value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} placeholder="Your booking is confirmed! 🎉" />
        </div>
        <div className="form-group">
          <label className="form-label required">Body</label>
          <textarea className="form-control" rows={4} value={form.body} onChange={e => setForm(f => ({ ...f, body: e.target.value }))} placeholder="Use {{variable}} for dynamic content…" />
          <div className="form-hint">Variables: {'{{user_name}}'}, {'{{booking_id}}'}, {'{{event_date}}'}, etc.</div>
        </div>
      </Modal>

      <ConfirmDialog open={!!deleteId} onClose={() => setDeleteId(null)} onConfirm={() => deleteMutation.mutate(deleteId)}
        title="Delete Template" message="This template will be permanently deleted." danger loading={deleteMutation.isPending} />
    </div>
  );
}

function SendTab() {
  const [form, setForm] = useState({ user_id: '', title: '', message: '', notification_type: 'push' });
  const [broadcastForm, setBroadcastForm] = useState({ title: '', message: '', notification_type: 'push', target: 'all' });
  const [mode, setMode] = useState('single');

  const sendMutation = useMutation({
    mutationFn: (body) => mode === 'single' ? notificationsApi.send(body) : notificationsApi.broadcast(body),
    onSuccess: () => { toast.success(mode === 'single' ? 'Notification sent' : 'Broadcast queued'); },
    onError: () => toast.error('Send failed'),
  });

  return (
    <div style={{ maxWidth: 560 }}>
      <div className="admin-tabs" style={{ marginBottom: 16 }}>
        <button className={`admin-tab${mode === 'single' ? ' active' : ''}`} onClick={() => setMode('single')}>Single User</button>
        <button className={`admin-tab${mode === 'broadcast' ? ' active' : ''}`} onClick={() => setMode('broadcast')}>Broadcast</button>
      </div>

      {mode === 'single' && (
        <div className="admin-card">
          <div className="admin-card-body">
            <div className="form-group">
              <label className="form-label required">User ID</label>
              <input className="form-control" value={form.user_id} onChange={e => setForm(f => ({ ...f, user_id: e.target.value }))} placeholder="User UUID…" />
            </div>
            <div className="form-group">
              <label className="form-label required">Title</label>
              <input className="form-control" value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} />
            </div>
            <div className="form-group">
              <label className="form-label required">Message</label>
              <textarea className="form-control" rows={3} value={form.message} onChange={e => setForm(f => ({ ...f, message: e.target.value }))} />
            </div>
            <button className="btn btn-primary" onClick={() => sendMutation.mutate(form)} disabled={!form.user_id || !form.title || sendMutation.isPending}>
              {sendMutation.isPending ? 'Sending…' : 'Send Notification'}
            </button>
          </div>
        </div>
      )}

      {mode === 'broadcast' && (
        <div className="admin-card">
          <div className="admin-card-body">
            <div className="admin-alert admin-alert-warning">
              ⚠️ This will send to ALL users or the selected segment. Use carefully.
            </div>
            <div className="form-group">
              <label className="form-label">Target Audience</label>
              <select className="form-control" value={broadcastForm.target} onChange={e => setBroadcastForm(f => ({ ...f, target: e.target.value }))}>
                <option value="all">All Users</option>
                <option value="customers">Customers Only</option>
                <option value="vendors">Vendors Only</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label required">Title</label>
              <input className="form-control" value={broadcastForm.title} onChange={e => setBroadcastForm(f => ({ ...f, title: e.target.value }))} />
            </div>
            <div className="form-group">
              <label className="form-label required">Message</label>
              <textarea className="form-control" rows={3} value={broadcastForm.message} onChange={e => setBroadcastForm(f => ({ ...f, message: e.target.value }))} />
            </div>
            <button className="btn btn-primary" onClick={() => sendMutation.mutate(broadcastForm)} disabled={!broadcastForm.title || sendMutation.isPending}>
              {sendMutation.isPending ? 'Queuing…' : 'Broadcast'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function NotificationsPage() {
  const [activeTab, setActiveTab] = useState('templates');

  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <h1>Notification Center</h1>
          <p>Manage templates, send notifications, and broadcast messages</p>
        </div>
      </div>

      <div className="admin-tabs">
        {['templates', 'send'].map(t => (
          <button key={t} className={`admin-tab${activeTab === t ? ' active' : ''}`} onClick={() => setActiveTab(t)}>
            {t === 'templates' ? 'Templates' : 'Send / Broadcast'}
          </button>
        ))}
      </div>

      {activeTab === 'templates' && <TemplatesTab />}
      {activeTab === 'send' && <SendTab />}
    </div>
  );
}
