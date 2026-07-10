import { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { notificationsApi } from '../../api';
import { formatDateTime } from '../../utils/format';
import StatusBadge from '../../components/ui/StatusBadge';
import { SkeletonTable } from '../../components/ui/Skeleton';
import Modal, { ConfirmDialog } from '../../components/ui/Modal';

const NOTIFICATION_TYPE_OPTIONS = [
  { value: 'booking_confirmed', label: 'Booking Confirmed' },
  { value: 'booking_cancelled', label: 'Booking Cancelled' },
  { value: 'booking_updated', label: 'Booking Updated' },
  { value: 'payment_received', label: 'Payment Received' },
  { value: 'payment_failed', label: 'Payment Failed' },
  { value: 'refund_initiated', label: 'Refund Initiated' },
  { value: 'refund_completed', label: 'Refund Completed' },
  { value: 'otp', label: 'OTP' },
  { value: 'reminder', label: 'Reminder' },
  { value: 'promotional', label: 'Promotional' },
  { value: 'system', label: 'System' },
  { value: 'review_request', label: 'Review Request' },
  { value: 'vendor_assigned', label: 'Vendor Assigned' },
  { value: 'rsvp_update', label: 'RSVP Update' },
  { value: 'celebration_upcoming', label: 'Celebration Upcoming' },
  { value: 'wallet_credit', label: 'Wallet Credit' },
  { value: 'membership_expiring', label: 'Membership Expiring' },
  { value: 'support_update', label: 'Support Update' },
];

const TEMPLATE_CHANNEL_OPTIONS = [
  { value: 'in_app', label: 'In-App' },
  { value: 'push', label: 'Push' },
  { value: 'sms', label: 'SMS' },
  { value: 'email', label: 'Email' },
  { value: 'whatsapp', label: 'WhatsApp' },
];

// Curated list of dynamic content the notification service actually renders
// into templates via Jinja2 — click to insert instead of typing {{...}} by hand.
const DYNAMIC_CONTENT_OPTIONS = [
  { key: 'user_name', label: 'Customer Name' },
  { key: 'booking_number', label: 'Booking Number' },
  { key: 'booking_id', label: 'Booking ID' },
  { key: 'package_name', label: 'Package Name' },
  { key: 'vendor_name', label: 'Vendor Name' },
  { key: 'event_date', label: 'Event Date' },
  { key: 'event_time', label: 'Event Time' },
  { key: 'venue_address', label: 'Venue Address' },
  { key: 'celebration_title', label: 'Celebration Title' },
  { key: 'amount', label: 'Amount' },
  { key: 'payment_status', label: 'Payment Status' },
  { key: 'wallet_balance', label: 'Wallet Balance' },
  { key: 'membership_tier', label: 'Membership Tier' },
  { key: 'ticket_number', label: 'Support Ticket #' },
];

function DynamicContentPicker({ onInsert }) {
  return (
    <div style={{ marginTop: 6 }}>
      <div className="form-hint" style={{ marginBottom: 6 }}>Click to insert dynamic content:</div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
        {DYNAMIC_CONTENT_OPTIONS.map((opt) => (
          <button
            key={opt.key}
            type="button"
            className="btn btn-secondary btn-sm"
            style={{ fontSize: 12 }}
            onMouseDown={(e) => e.preventDefault()} // keep focus/selection in the text field
            onClick={() => onInsert(`{{${opt.key}}}`)}
          >
            + {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}

const EMPTY_TEMPLATE_FORM = {
  notification_type: 'booking_confirmed',
  channel: 'in_app',
  title_template: '',
  body_template: '',
};

function TemplatesTab() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [deleteId, setDeleteId] = useState(null);
  const [form, setForm] = useState(EMPTY_TEMPLATE_FORM);
  const titleRef = useRef(null);
  const bodyRef = useRef(null);

  const { data: templates = [] } = useQuery({
    queryKey: ['notifications', 'templates'],
    queryFn: () => notificationsApi.listTemplates(),
  });

  const saveMutation = useMutation({
    mutationFn: (body) => editItem
      ? notificationsApi.updateTemplate(editItem.id, { title_template: body.title_template, body_template: body.body_template })
      : notificationsApi.createTemplate(body),
    onSuccess: () => {
      toast.success(editItem ? 'Template updated' : 'Template created');
      qc.invalidateQueries(['notifications', 'templates']);
      setOpen(false); setEditItem(null);
    },
    onError: (err) => toast.error(err?.response?.data?.message || err?.response?.data?.detail || 'Save failed'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id) => notificationsApi.deleteTemplate(id),
    onSuccess: () => { toast.success('Deleted'); qc.invalidateQueries(['notifications', 'templates']); setDeleteId(null); },
    onError: () => toast.error('Delete failed'),
  });

  const openEdit = (t) => {
    setEditItem(t);
    setForm({
      notification_type: t.notification_type,
      channel: t.channel,
      title_template: t.title_template,
      body_template: t.body_template,
    });
    setOpen(true);
  };

  // Inserts text at the current cursor position of whichever field was last
  // focused, so admins never have to hand-type {{variable}} syntax.
  const insertIntoField = (fieldKey, ref, text) => {
    const el = ref.current;
    const current = form[fieldKey] ?? '';
    if (!el) {
      setForm((f) => ({ ...f, [fieldKey]: current + text }));
      return;
    }
    const start = el.selectionStart ?? current.length;
    const end = el.selectionEnd ?? current.length;
    const next = current.slice(0, start) + text + current.slice(end);
    setForm((f) => ({ ...f, [fieldKey]: next }));
    requestAnimationFrame(() => {
      el.focus();
      const pos = start + text.length;
      el.setSelectionRange(pos, pos);
    });
  };

  const typeLabel = (value) => NOTIFICATION_TYPE_OPTIONS.find((o) => o.value === value)?.label ?? value;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
        <button className="btn btn-primary" onClick={() => { setEditItem(null); setForm(EMPTY_TEMPLATE_FORM); setOpen(true); }}>
          + New Template
        </button>
      </div>
      <div className="admin-table-wrapper">
        <table className="admin-table">
          <thead>
            <tr><th>Key</th><th>Title</th><th>Type</th><th>Channel</th><th>Actions</th></tr>
          </thead>
          <tbody>
            {templates.map((t) => (
              <tr key={t.id}>
                <td><code style={{ fontSize: 11 }}>{t.template_key}</code></td>
                <td>{t.title_template}</td>
                <td>{typeLabel(t.notification_type)}</td>
                <td>{TEMPLATE_CHANNEL_OPTIONS.find((c) => c.value === t.channel)?.label ?? t.channel}</td>
                <td>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <button className="btn btn-secondary btn-sm" onClick={() => openEdit(t)}>Edit</button>
                    <button className="btn btn-danger btn-sm" onClick={() => setDeleteId(t.id)}>Delete</button>
                  </div>
                </td>
              </tr>
            ))}
            {!templates.length && <tr><td colSpan={5} className="admin-table-empty">No templates</td></tr>}
          </tbody>
        </table>
      </div>

      <Modal open={open} onClose={() => setOpen(false)} title={editItem ? 'Edit Template' : 'New Template'} size="lg"
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setOpen(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={() => saveMutation.mutate(form)} disabled={!form.title_template || !form.body_template || saveMutation.isPending}>
              {saveMutation.isPending ? 'Saving…' : 'Save'}
            </button>
          </>
        }
      >
        <div className="form-row-2">
          <div className="form-group">
            <label className="form-label required">Notification Type</label>
            <select className="form-control" value={form.notification_type} disabled={!!editItem}
              onChange={e => setForm(f => ({ ...f, notification_type: e.target.value }))}>
              {NOTIFICATION_TYPE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
            {!editItem && <div className="form-hint">The template's unique key is generated from this — can't be changed later.</div>}
          </div>
          <div className="form-group">
            <label className="form-label required">Channel</label>
            <select className="form-control" value={form.channel} disabled={!!editItem}
              onChange={e => setForm(f => ({ ...f, channel: e.target.value }))}>
              {TEMPLATE_CHANNEL_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
        </div>
        <div className="form-group">
          <label className="form-label required">Title</label>
          <input
            ref={titleRef}
            className="form-control"
            value={form.title_template}
            onChange={e => setForm(f => ({ ...f, title_template: e.target.value }))}
            placeholder="Your booking is confirmed! 🎉"
          />
        </div>
        <div className="form-group">
          <label className="form-label required">Body</label>
          <textarea
            ref={bodyRef}
            className="form-control"
            rows={4}
            value={form.body_template}
            onChange={e => setForm(f => ({ ...f, body_template: e.target.value }))}
            placeholder="Hi there, your booking is confirmed for..."
          />
        </div>
        <DynamicContentPicker
          onInsert={(text) => {
            // Insert into whichever field (title/body) the admin last used;
            // default to body since that's the common case.
            const active = document.activeElement;
            if (active === titleRef.current) insertIntoField('title_template', titleRef, text);
            else insertIntoField('body_template', bodyRef, text);
          }}
        />
      </Modal>

      <ConfirmDialog open={!!deleteId} onClose={() => setDeleteId(null)} onConfirm={() => deleteMutation.mutate(deleteId)}
        title="Delete Template" message="This template will be permanently deleted." danger loading={deleteMutation.isPending} />
    </div>
  );
}

const CHANNEL_OPTIONS = [
  { value: 'in_app', label: 'In-App' },
  { value: 'push', label: 'Push' },
  { value: 'sms', label: 'SMS' },
  { value: 'email', label: 'Email' },
  { value: 'whatsapp', label: 'WhatsApp' },
];

function SendTab() {
  const [form, setForm] = useState({ user_id: '', title: '', body: '', channel: 'in_app', notification_type: 'system' });
  const [broadcastForm, setBroadcastForm] = useState({ title: '', body: '', channel: 'in_app', notification_type: 'promotional', target_segment: 'all' });
  const [mode, setMode] = useState('single');

  const sendMutation = useMutation({
    mutationFn: (body) => mode === 'single'
      ? notificationsApi.send(body)
      : notificationsApi.broadcast(body),
    onSuccess: () => { toast.success(mode === 'single' ? 'Notification sent' : 'Broadcast queued'); },
    onError: (err) => toast.error(err?.response?.data?.message || err?.response?.data?.detail || 'Send failed'),
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
              <textarea className="form-control" rows={3} value={form.body} onChange={e => setForm(f => ({ ...f, body: e.target.value }))} />
            </div>
            <div className="form-group">
              <label className="form-label">Channel</label>
              <select className="form-control" value={form.channel} onChange={e => setForm(f => ({ ...f, channel: e.target.value }))}>
                {CHANNEL_OPTIONS.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
              </select>
              {form.channel !== 'in_app' && (
                <div className="form-hint">Only In-App is delivered today. Other channels are recorded as pending until a dispatcher is wired.</div>
              )}
            </div>
            <button className="btn btn-primary" onClick={() => sendMutation.mutate(form)} disabled={!form.user_id || !form.title || !form.body || sendMutation.isPending}>
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
              <select className="form-control" value={broadcastForm.target_segment} onChange={e => setBroadcastForm(f => ({ ...f, target_segment: e.target.value }))}>
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
              <textarea className="form-control" rows={3} value={broadcastForm.body} onChange={e => setBroadcastForm(f => ({ ...f, body: e.target.value }))} />
            </div>
            <div className="form-group">
              <label className="form-label">Channel</label>
              <select className="form-control" value={broadcastForm.channel} onChange={e => setBroadcastForm(f => ({ ...f, channel: e.target.value }))}>
                {CHANNEL_OPTIONS.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
              </select>
              {broadcastForm.channel !== 'in_app' && (
                <div className="form-hint">Only In-App is delivered today. Other channels are recorded as pending until a dispatcher is wired.</div>
              )}
            </div>
            <button className="btn btn-primary" onClick={() => sendMutation.mutate(broadcastForm)} disabled={!broadcastForm.title || !broadcastForm.body || sendMutation.isPending}>
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
