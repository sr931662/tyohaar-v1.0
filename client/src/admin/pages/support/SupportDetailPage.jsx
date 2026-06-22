import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { supportApi } from '../../api';
import { formatDateTime } from '../../utils/format';
import StatusBadge from '../../components/ui/StatusBadge';
import { SkeletonCard } from '../../components/ui/Skeleton';

export default function SupportDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [newMessage, setNewMessage] = useState('');

  const { data: ticket, isLoading } = useQuery({
    queryKey: ['support', id],
    queryFn: () => supportApi.get(id),
  });

  const { data: messagesData } = useQuery({
    queryKey: ['support', id, 'messages'],
    queryFn: () => supportApi.listMessages(id),
  });
  const messages = messagesData?.items ?? messagesData ?? [];

  const statusMutation = useMutation({
    mutationFn: (newStatus) => supportApi.updateStatus(id, newStatus),
    onSuccess: () => { toast.success('Status updated'); qc.invalidateQueries(['support', id]); },
    onError: () => toast.error('Failed'),
  });

  const sendMutation = useMutation({
    mutationFn: (content) => supportApi.addMessage(id, { content, sender_type: 'admin' }),
    onSuccess: () => {
      toast.success('Message sent');
      setNewMessage('');
      qc.invalidateQueries(['support', id, 'messages']);
    },
    onError: () => toast.error('Failed to send'),
  });

  if (isLoading) return <SkeletonCard />;
  if (!ticket) return <div className="admin-card" style={{ padding: 24 }}>Ticket not found.</div>;

  const STATUS_TRANSITIONS = {
    open: ['in_progress', 'closed'],
    in_progress: ['resolved', 'closed'],
    resolved: ['closed'],
    closed: [],
  };
  const nextStatuses = STATUS_TRANSITIONS[ticket.status] ?? [];

  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <button className="btn btn-secondary btn-sm" onClick={() => navigate('/admin/support')} style={{ marginRight: 8 }}>← Back</button>
          <h1>Ticket #{ticket.ticket_number ?? ticket.id?.slice(0, 8)}</h1>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {nextStatuses.map(s => (
            <button key={s} className="btn btn-secondary btn-sm" onClick={() => statusMutation.mutate(s)} disabled={statusMutation.isPending}>
              Mark {s.replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 24 }}>
        {/* Messages */}
        <div>
          <div className="admin-card" style={{ marginBottom: 16 }}>
            <div className="admin-card-header">
              <div className="admin-card-title">Conversation</div>
            </div>
            <div className="admin-card-body" style={{ display: 'flex', flexDirection: 'column', gap: 12, minHeight: 200 }}>
              {messages.map((m) => (
                <div key={m.id} style={{
                  padding: '10px 14px',
                  borderRadius: 8,
                  background: m.sender_type === 'admin' ? 'var(--primary-50)' : 'var(--bg-secondary)',
                  alignSelf: m.sender_type === 'admin' ? 'flex-end' : 'flex-start',
                  maxWidth: '80%',
                }}>
                  <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginBottom: 4 }}>
                    {m.sender_type === 'admin' ? 'Admin' : m.sender?.name ?? 'User'} · {formatDateTime(m.created_at)}
                  </div>
                  <div>{m.content}</div>
                </div>
              ))}
              {!messages.length && <div style={{ color: 'var(--text-tertiary)', textAlign: 'center', padding: 24 }}>No messages yet</div>}
            </div>
          </div>

          {ticket.status !== 'closed' && (
            <div className="admin-card">
              <div className="admin-card-body">
                <textarea className="form-control" rows={3} placeholder="Type a reply…" value={newMessage} onChange={e => setNewMessage(e.target.value)} />
                <div style={{ marginTop: 8, display: 'flex', justifyContent: 'flex-end' }}>
                  <button className="btn btn-primary" onClick={() => sendMutation.mutate(newMessage)} disabled={!newMessage.trim() || sendMutation.isPending}>
                    {sendMutation.isPending ? 'Sending…' : 'Send Reply'}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Info panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="admin-card">
            <div className="admin-card-header"><div className="admin-card-title">Ticket Info</div></div>
            <div className="admin-card-body">
              <div className="detail-row"><span className="detail-label">Status</span><StatusBadge status={ticket.status} /></div>
              <div className="detail-row"><span className="detail-label">Subject</span><span>{ticket.subject}</span></div>
              <div className="detail-row"><span className="detail-label">Category</span><span>{ticket.category ?? '—'}</span></div>
              <div className="detail-row"><span className="detail-label">Priority</span><StatusBadge status={ticket.priority ?? 'normal'} /></div>
              <div className="detail-row"><span className="detail-label">Created</span><span>{formatDateTime(ticket.created_at)}</span></div>
              {ticket.resolved_at && <div className="detail-row"><span className="detail-label">Resolved</span><span>{formatDateTime(ticket.resolved_at)}</span></div>}
            </div>
          </div>

          <div className="admin-card">
            <div className="admin-card-header"><div className="admin-card-title">Customer</div></div>
            <div className="admin-card-body">
              <div className="detail-row"><span className="detail-label">Name</span><span>{ticket.user?.name ?? '—'}</span></div>
              <div className="detail-row"><span className="detail-label">Email</span><span style={{ fontSize: 12 }}>{ticket.user?.email ?? '—'}</span></div>
            </div>
          </div>

          {ticket.description && (
            <div className="admin-card">
              <div className="admin-card-header"><div className="admin-card-title">Initial Description</div></div>
              <div className="admin-card-body" style={{ fontSize: 13, lineHeight: 1.6, color: 'var(--text-secondary)' }}>
                {ticket.description}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
