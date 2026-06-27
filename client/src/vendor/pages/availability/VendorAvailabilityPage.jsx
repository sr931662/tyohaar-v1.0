import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { vendorProfileApi } from '../../api';
import { ConfirmDialog } from '../../../admin/components/ui/Modal';
import { SkeletonCard } from '../../../admin/components/ui/Skeleton';

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
const DAY_ABBR = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

const EMPTY_SLOT = {
  available_from_date: '',
  available_until_date: '',
  max_bookings_per_day: 1,
  is_active: true,
};

function SlotFormModal({ initial, onClose, onSave, saving }) {
  const isEdit = !!initial;
  const [form, setForm] = useState({
    available_from_date: initial?.available_from_date ?? '',
    available_until_date: initial?.available_until_date ?? '',
    max_bookings_per_day: initial?.max_bookings_per_day ?? 1,
    is_active: initial?.is_active ?? true,
  });

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.available_from_date) return toast.error('Start date is required.');
    if (!form.available_until_date) return toast.error('End date is required.');
    if (form.available_from_date > form.available_until_date) return toast.error('Start date must be before end date.');
    onSave(form);
  };

  return (
    <div className="admin-modal-overlay" onClick={onClose}>
      <div className="admin-modal" style={{ maxWidth: 460 }} onClick={(e) => e.stopPropagation()}>
        <div className="admin-modal-header">
          <h2 className="admin-modal-title">{isEdit ? 'Edit Availability Slot' : 'Add Availability Slot'}</h2>
          <button className="admin-modal-close" onClick={onClose}>×</button>
        </div>
        <form onSubmit={handleSubmit} style={{ padding: '0 24px 24px', display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 6 }}>From Date *</label>
              <input
                className="admin-input"
                type="date"
                value={form.available_from_date}
                onChange={(e) => set('available_from_date', e.target.value)}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 6 }}>Until Date *</label>
              <input
                className="admin-input"
                type="date"
                value={form.available_until_date}
                onChange={(e) => set('available_until_date', e.target.value)}
              />
            </div>
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 6 }}>Max Bookings Per Day</label>
            <input
              className="admin-input"
              type="number"
              min="1"
              max="20"
              value={form.max_bookings_per_day}
              onChange={(e) => set('max_bookings_per_day', Number(e.target.value))}
            />
          </div>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, cursor: 'pointer', userSelect: 'none' }}>
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(e) => set('is_active', e.target.checked)}
            />
            Active (accepting bookings)
          </label>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 4 }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? 'Saving…' : (isEdit ? 'Save Changes' : 'Add Slot')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function VendorAvailabilityPage() {
  const qc = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);
  const [editingSlot, setEditingSlot] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(null);

  const { data: vendor } = useQuery({
    queryKey: ['vendor', 'me'],
    queryFn: () => vendorProfileApi.getMe(),
  });

  const vendorId = vendor?.id;

  const { data: slots = [], isLoading } = useQuery({
    queryKey: ['vendor-availability', vendorId],
    queryFn: () => vendorProfileApi.listAvailability(vendorId),
    enabled: !!vendorId,
  });

  const invalidate = () => qc.invalidateQueries(['vendor-availability', vendorId]);

  const createMutation = useMutation({
    mutationFn: (body) => vendorProfileApi.createAvailability(vendorId, body),
    onSuccess: () => { toast.success('Availability slot added.'); invalidate(); setShowAdd(false); },
    onError: (err) => toast.error(err?.response?.data?.error?.message ?? 'Failed to add slot.'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ slotId, body }) => vendorProfileApi.updateAvailability(vendorId, slotId, body),
    onSuccess: () => { toast.success('Slot updated.'); invalidate(); setEditingSlot(null); },
    onError: (err) => toast.error(err?.response?.data?.error?.message ?? 'Failed to update slot.'),
  });

  const deleteMutation = useMutation({
    mutationFn: (slotId) => vendorProfileApi.deleteAvailability(vendorId, slotId),
    onSuccess: () => { toast.success('Slot removed.'); invalidate(); setConfirmDelete(null); },
    onError: () => toast.error('Failed to remove slot.'),
  });

  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <h1>Availability</h1>
          <p style={{ color: 'var(--text-secondary)' }}>Define date ranges when you accept bookings</p>
        </div>
        <div className="admin-page-header-actions">
          <button className="btn btn-primary" onClick={() => setShowAdd(true)} disabled={!vendorId}>
            + Add Slot
          </button>
        </div>
      </div>

      {/* Info banner */}
      <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start', background: 'rgba(59,130,246,0.07)', border: '1px solid rgba(59,130,246,0.18)', borderRadius: 10, padding: '11px 16px', marginBottom: 20, fontSize: 13, color: 'var(--color-info, #3b82f6)' }}>
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginTop: 1, flexShrink: 0 }}><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
        <span>Add date ranges when you are available to accept bookings. Customers will only be able to book services during active availability windows.</span>
      </div>

      {!vendorId ? (
        <div style={{ padding: 48, textAlign: 'center' }}>
          <p style={{ color: 'var(--text-secondary)' }}>Please create your vendor profile first.</p>
        </div>
      ) : isLoading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {[0, 1, 2].map((i) => <SkeletonCard key={i} height={72} />)}
        </div>
      ) : !slots.length ? (
        <div style={{ textAlign: 'center', padding: 48 }}>
          <div style={{ fontSize: 40, marginBottom: 12 }}>📅</div>
          <p style={{ color: 'var(--text-secondary)', marginBottom: 16 }}>No availability slots configured.</p>
          <button className="btn btn-primary" onClick={() => setShowAdd(true)}>+ Add First Slot</button>
        </div>
      ) : (
        <div className="admin-table-wrapper">
          <table className="admin-table">
            <thead>
              <tr>
                <th>From Date</th>
                <th>Until Date</th>
                <th>Max Bookings / Day</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {slots.map((slot) => (
                <tr key={slot.id}>
                  <td style={{ fontSize: 13, fontWeight: 500 }}>
                    {slot.available_from_date
                      ? new Date(slot.available_from_date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
                      : '—'}
                  </td>
                  <td style={{ fontSize: 13 }}>
                    {slot.available_until_date
                      ? new Date(slot.available_until_date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
                      : '—'}
                  </td>
                  <td style={{ fontSize: 13 }}>
                    {slot.max_bookings_per_day ?? 1} booking{slot.max_bookings_per_day !== 1 ? 's' : ''} / day
                  </td>
                  <td>
                    <span style={{
                      display: 'inline-flex', alignItems: 'center', gap: 5,
                      padding: '3px 8px', borderRadius: 99,
                      background: slot.is_active ? 'rgba(34,197,94,0.1)' : 'rgba(107,114,128,0.1)',
                      border: `1px solid ${slot.is_active ? 'rgba(34,197,94,0.3)' : 'rgba(107,114,128,0.3)'}`,
                      fontSize: 12, fontWeight: 600,
                      color: slot.is_active ? '#22c55e' : 'var(--text-tertiary)',
                    }}>
                      <span style={{ width: 5, height: 5, borderRadius: '50%', background: 'currentColor' }} />
                      {slot.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: 6 }}>
                      <button className="btn btn-secondary btn-sm" onClick={() => setEditingSlot(slot)}>Edit</button>
                      <button
                        className="btn btn-sm"
                        style={{ background: 'transparent', border: '1px solid var(--border-subtle)', color: '#ef4444' }}
                        onClick={() => setConfirmDelete(slot)}
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showAdd && (
        <SlotFormModal
          onClose={() => setShowAdd(false)}
          onSave={(body) => createMutation.mutate(body)}
          saving={createMutation.isPending}
        />
      )}
      {editingSlot && (
        <SlotFormModal
          initial={editingSlot}
          onClose={() => setEditingSlot(null)}
          onSave={(body) => updateMutation.mutate({ slotId: editingSlot.id, body })}
          saving={updateMutation.isPending}
        />
      )}

      <ConfirmDialog
        open={!!confirmDelete}
        onClose={() => setConfirmDelete(null)}
        onConfirm={() => deleteMutation.mutate(confirmDelete.id)}
        title="Remove Availability Slot"
        message={`Remove this availability slot? Customers will no longer be able to book during this period.`}
        loading={deleteMutation.isPending}
      />
    </div>
  );
}
