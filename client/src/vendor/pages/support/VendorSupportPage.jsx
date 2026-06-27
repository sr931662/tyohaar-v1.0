import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { vendorSupportApi } from '../../api';
import StatusBadge from '../../../admin/components/ui/StatusBadge';
import { SkeletonTable } from '../../../admin/components/ui/Skeleton';
import EmptyState from '../../../admin/components/ui/EmptyState';
import Pagination from '../../../admin/components/ui/Pagination';
import { usePagination } from '../../../admin/hooks/usePagination';
import { formatDateTime, timeAgo } from '../../../admin/utils/format';

const TICKET_TYPES = ['BOOKING', 'PAYMENT', 'VENDOR', 'ACCOUNT', 'GENERAL'];
const PRIORITIES = ['LOW', 'MEDIUM', 'HIGH', 'URGENT'];

const PRIORITY_COLOR = {
  LOW: 'var(--text-tertiary)',
  MEDIUM: '#f59e0b',
  HIGH: '#ef4444',
  URGENT: '#dc2626',
};

function NewTicketModal({ onClose, onCreate, saving }) {
  const [form, setForm] = useState({
    subject: '',
    description: '',
    ticket_type: 'GENERAL',
    priority: 'MEDIUM',
  });
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.subject.trim()) return toast.error('Subject is required.');
    if (!form.description.trim()) return toast.error('Description is required.');
    onCreate(form);
  };

  return (
    <div className="admin-modal-overlay" onClick={onClose}>
      <div className="admin-modal" style={{ maxWidth: 520 }} onClick={(e) => e.stopPropagation()}>
        <div className="admin-modal-header">
          <h2 className="admin-modal-title">New Support Ticket</h2>
          <button className="admin-modal-close" onClick={onClose}>×</button>
        </div>
        <form onSubmit={handleSubmit} style={{ padding: '0 24px 24px', display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div>
            <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 6 }}>Subject *</label>
            <input
              className="admin-input"
              value={form.subject}
              onChange={(e) => set('subject', e.target.value)}
              placeholder="Brief summary of your issue"
            />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 6 }}>Type</label>
              <select className="admin-input" value={form.ticket_type} onChange={(e) => set('ticket_type', e.target.value)}>
                {TICKET_TYPES.map((t) => <option key={t} value={t}>{t.charAt(0) + t.slice(1).toLowerCase()}</option>)}
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 6 }}>Priority</label>
              <select className="admin-input" value={form.priority} onChange={(e) => set('priority', e.target.value)}>
                {PRIORITIES.map((p) => <option key={p} value={p}>{p.charAt(0) + p.slice(1).toLowerCase()}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 6 }}>Description *</label>
            <textarea
              className="admin-input"
              rows={5}
              value={form.description}
              onChange={(e) => set('description', e.target.value)}
              placeholder="Please describe the issue in detail…"
            />
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 4 }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? 'Submitting…' : 'Submit Ticket'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function TicketDetailModal({ ticket, onClose }) {
  const qc = useQueryClient();
  const [message, setMessage] = useState('');

  const { data: messagesData, isLoading } = useQuery({
    queryKey: ['vendor-support-messages', ticket.id],
    queryFn: () => vendorSupportApi.listMessages(ticket.id, { per_page: 50 }),
    refetchInterval: 30_000,
  });

  const messages = messagesData?.items ?? [];

  const sendMutation = useMutation({
    mutationFn: (body) => vendorSupportApi.addMessage(ticket.id, body),
    onSuccess: () => {
      toast.success('Message sent');
      qc.invalidateQueries(['vendor-support-messages', ticket.id]);
      setMessage('');
    },
    onError: () => toast.error('Failed to send message'),
  });

  const handleSend = (e) => {
    e.preventDefault();
    if (!message.trim()) return;
    sendMutation.mutate({ message_text: message.trim() });
  };

  return (
    <div className="admin-modal-overlay" onClick={onClose}>
      <div className="admin-modal lg" style={{ maxWidth: 680, display: 'flex', flexDirection: 'column', maxHeight: '90vh' }} onClick={(e) => e.stopPropagation()}>
        <div className="admin-modal-header" style={{ flexShrink: 0 }}>
          <div>
            <h2 className="admin-modal-title" style={{ marginBottom: 4 }}>{ticket.subject}</h2>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <StatusBadge status={ticket.status?.toLowerCase()} />
              <span style={{ fontSize: 12, color: PRIORITY_COLOR[ticket.priority], fontWeight: 600 }}>
                {ticket.priority}
              </span>
              <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>#{ticket.ticket_number ?? ticket.id?.slice(0, 8)}</span>
            </div>
          </div>
          <button className="admin-modal-close" onClick={onClose}>×</button>
        </div>

        {/* Original description */}
        <div style={{ padding: '12px 24px', borderBottom: '1px solid var(--border-subtle)', flexShrink: 0 }}>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6, margin: 0 }}>{ticket.description}</p>
        </div>

        {/* Messages */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px 24px', display: 'flex', flexDirection: 'column', gap: 12 }}>
          {isLoading ? (
            <div style={{ padding: 24, textAlign: 'center' }}>
              <div className="spinner" style={{ width: 24, height: 24, margin: '0 auto' }} />
            </div>
          ) : !messages.length ? (
            <p style={{ color: 'var(--text-tertiary)', fontSize: 13, textAlign: 'center', padding: '24px 0' }}>
              No messages yet. Send a message below.
            </p>
          ) : (
            messages.map((msg) => (
              <div
                key={msg.id}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: msg.is_internal ? 'flex-start' : 'flex-end',
                }}
              >
                <div style={{
                  maxWidth: '80%', padding: '10px 14px', borderRadius: 12,
                  background: msg.is_internal ? 'var(--bg-raised)' : 'var(--brand-600, #4f46e5)',
                  color: msg.is_internal ? 'var(--text-primary)' : 'white',
                  fontSize: 13, lineHeight: 1.5,
                }}>
                  {msg.message_text}
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 3, padding: '0 4px' }}>
                  {msg.is_internal ? 'Support' : 'You'} · {msg.created_at ? timeAgo(msg.created_at) : ''}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Reply box */}
        {ticket.status !== 'CLOSED' && ticket.status !== 'RESOLVED' && (
          <form onSubmit={handleSend} style={{ padding: '12px 24px', borderTop: '1px solid var(--border-subtle)', display: 'flex', gap: 10, flexShrink: 0 }}>
            <input
              className="admin-input"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Type a message…"
              style={{ flex: 1 }}
            />
            <button type="submit" className="btn btn-primary btn-sm" disabled={sendMutation.isPending || !message.trim()}>
              Send
            </button>
          </form>
        )}
        {(ticket.status === 'CLOSED' || ticket.status === 'RESOLVED') && (
          <div style={{ padding: '12px 24px', borderTop: '1px solid var(--border-subtle)', fontSize: 13, color: 'var(--text-tertiary)', textAlign: 'center' }}>
            This ticket is {ticket.status?.toLowerCase()}. No further replies can be added.
          </div>
        )}
      </div>
    </div>
  );
}

export default function VendorSupportPage() {
  const qc = useQueryClient();
  const { page, perPage, setPage, reset } = usePagination();
  const [statusFilter, setStatusFilter] = useState('');
  const [showNew, setShowNew] = useState(false);
  const [viewTicket, setViewTicket] = useState(null);

  const { data, isLoading } = useQuery({
    queryKey: ['vendor-support', { page, perPage, statusFilter }],
    queryFn: () => vendorSupportApi.list({
      page, per_page: perPage,
      status: statusFilter || undefined,
    }),
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const pages = data?.pages ?? 1;

  const createMutation = useMutation({
    mutationFn: (body) => vendorSupportApi.create(body),
    onSuccess: () => {
      toast.success('Support ticket created');
      qc.invalidateQueries(['vendor-support']);
      setShowNew(false);
    },
    onError: (err) => toast.error(err?.response?.data?.error?.message ?? 'Failed to create ticket'),
  });

  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <h1>Support</h1>
          <p style={{ color: 'var(--text-secondary)' }}>Submit and track your support requests</p>
        </div>
        <div className="admin-page-header-actions">
          <button className="btn btn-primary" onClick={() => setShowNew(true)}>+ New Ticket</button>
        </div>
      </div>

      <div className="admin-filters">
        <select
          className="admin-filters-select"
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); reset(); }}
        >
          <option value="">All Statuses</option>
          <option value="OPEN">Open</option>
          <option value="IN_PROGRESS">In Progress</option>
          <option value="WAITING_ON_CUSTOMER">Waiting on You</option>
          <option value="RESOLVED">Resolved</option>
          <option value="CLOSED">Closed</option>
        </select>
      </div>

      {isLoading ? (
        <SkeletonTable rows={5} cols={5} />
      ) : !items.length ? (
        <EmptyState
          title="No support tickets"
          description="Create a ticket if you need help with bookings, payments, or your account."
          icon="🎫"
          action={<button className="btn btn-primary" onClick={() => setShowNew(true)}>Create Ticket</button>}
        />
      ) : (
        <>
          <div className="admin-table-wrapper">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Ticket</th>
                  <th>Type</th>
                  <th>Priority</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((ticket) => (
                  <tr key={ticket.id} style={{ cursor: 'pointer' }} onClick={() => setViewTicket(ticket)}>
                    <td>
                      <div className="admin-user-name">{ticket.subject}</div>
                      <div className="admin-user-email">#{ticket.ticket_number ?? ticket.id?.slice(0, 8)}</div>
                    </td>
                    <td style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                      {ticket.ticket_type?.charAt(0) + ticket.ticket_type?.slice(1)?.toLowerCase() ?? '—'}
                    </td>
                    <td>
                      <span style={{ fontSize: 12, fontWeight: 600, color: PRIORITY_COLOR[ticket.priority] }}>
                        {ticket.priority}
                      </span>
                    </td>
                    <td><StatusBadge status={ticket.status?.toLowerCase()} /></td>
                    <td style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>
                      {ticket.created_at ? timeAgo(ticket.created_at) : '—'}
                    </td>
                    <td onClick={(e) => e.stopPropagation()}>
                      <button className="btn btn-secondary btn-sm" onClick={() => setViewTicket(ticket)}>Open</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination page={page} pages={pages} total={total} perPage={perPage} onPageChange={setPage} />
        </>
      )}

      {showNew && (
        <NewTicketModal
          onClose={() => setShowNew(false)}
          onCreate={(body) => createMutation.mutate(body)}
          saving={createMutation.isPending}
        />
      )}
      {viewTicket && (
        <TicketDetailModal
          ticket={viewTicket}
          onClose={() => setViewTicket(null)}
        />
      )}
    </div>
  );
}
