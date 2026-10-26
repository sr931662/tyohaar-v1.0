import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { colorsApi } from '../../api';
import Modal, { ConfirmDialog } from '../../components/ui/Modal';
import EmptyState from '../../components/ui/EmptyState';
import { SkeletonTable } from '../../components/ui/Skeleton';

const HEX = /^#[0-9a-fA-F]{6}$/;
const muted = { color: 'var(--text-tertiary)' };

function Swatch({ hex, size = 28 }) {
  return (
    <span
      aria-hidden="true"
      style={{
        display: 'inline-block', width: size, height: size, borderRadius: '50%', background: hex,
        border: '1px solid var(--border, rgba(0,0,0,0.15))', flex: 'none',
      }}
    />
  );
}

/** Name + colour picker + hex box, kept in sync. Used for both add and edit. */
function ColorFields({ value, onChange }) {
  const valid = HEX.test(value.hex_code);
  return (
    <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
      <input
        className="admin-input"
        placeholder="Colour name, e.g. Rose Gold"
        value={value.name}
        maxLength={60}
        onChange={(e) => onChange({ ...value, name: e.target.value })}
        style={{ flex: '1 1 200px' }}
      />
      <input
        type="color"
        aria-label="Pick a colour"
        value={valid ? value.hex_code : '#000000'}
        onChange={(e) => onChange({ ...value, hex_code: e.target.value.toUpperCase() })}
        style={{ width: 44, height: 38, padding: 0, border: 'none', background: 'none', cursor: 'pointer' }}
      />
      <input
        className="admin-input"
        placeholder="#D4AF37"
        value={value.hex_code}
        maxLength={7}
        onChange={(e) => onChange({ ...value, hex_code: e.target.value.toUpperCase() })}
        style={{ width: 110, fontFamily: 'monospace', borderColor: value.hex_code && !valid ? 'var(--danger, #c0392b)' : undefined }}
        aria-invalid={value.hex_code ? !valid : undefined}
      />
    </div>
  );
}

function ColoursPanel() {
  const queryClient = useQueryClient();
  const { data: colors, isLoading, isError } = useQuery({ queryKey: ['balloon-colors'], queryFn: colorsApi.listAll });
  const [draft, setDraft] = useState({ name: '', hex_code: '#D4AF37' });
  const [editing, setEditing] = useState(null);
  const [deleting, setDeleting] = useState(null);

  const refresh = () => queryClient.invalidateQueries({ queryKey: ['balloon-colors'] });
  const fail = (fallback) => (e) => toast.error(e?.response?.data?.error?.message ?? fallback);

  const create = useMutation({
    mutationFn: () => colorsApi.create({ name: draft.name.trim(), hex_code: draft.hex_code }),
    onSuccess: () => { toast.success('Colour added.'); setDraft({ name: '', hex_code: '#D4AF37' }); refresh(); },
    onError: fail('Could not add the colour.'),
  });
  const update = useMutation({
    mutationFn: ({ id, body }) => colorsApi.update(id, body),
    onSuccess: () => { setEditing(null); refresh(); },
    onError: fail('Could not update the colour.'),
  });
  const remove = useMutation({
    mutationFn: (id) => colorsApi.remove(id),
    onSuccess: () => { toast.success('Colour removed.'); setDeleting(null); refresh(); },
    onError: (e) => { setDeleting(null); fail('Could not remove the colour.')(e); },
  });
  const reorder = useMutation({
    mutationFn: (ids) => colorsApi.reorder(ids),
    onSuccess: refresh,
    onError: fail('Could not save the order.'),
  });

  const list = colors ?? [];
  const active = list.filter((c) => c.is_active);
  const move = (index, delta) => {
    const ids = list.map((c) => c.id);
    const target = index + delta;
    if (target < 0 || target >= ids.length) return;
    [ids[index], ids[target]] = [ids[target], ids[index]];
    reorder.mutate(ids);
  };

  const canAdd = draft.name.trim().length >= 2 && HEX.test(draft.hex_code) && !create.isPending;

  return (
    <div>
      <div className="admin-card" style={{ padding: 16, marginBottom: 16 }}>
        <h3 style={{ fontSize: 14, margin: '0 0 10px' }}>Add a colour</h3>
        <form onSubmit={(e) => { e.preventDefault(); if (canAdd) create.mutate(); }} style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ flex: '1 1 380px' }}><ColorFields value={draft} onChange={setDraft} /></div>
          <button className="btn btn-primary" type="submit" disabled={!canAdd}>{create.isPending ? 'Adding…' : 'Add colour'}</button>
        </form>
      </div>

      <div className="admin-card" style={{ padding: 16, marginBottom: 16 }}>
        <h3 style={{ fontSize: 14, margin: '0 0 4px' }}>What customers see ({active.length})</h3>
        <p style={{ ...muted, margin: '0 0 10px', fontSize: 12.5 }}>This is the order of the swatches in the app&apos;s &ldquo;Choose your balloon colours&rdquo; step. Use the arrows below to change it.</p>
        {active.length ? (
          <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap' }}>
            {active.map((c, idx) => (
              <div key={c.id} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4, width: 64 }}>
                <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-tertiary)' }}>{idx + 1}</span>
                <Swatch hex={c.hex_code} size={36} />
                <span style={{ fontSize: 11, textAlign: 'center' }}>{c.name}</span>
              </div>
            ))}
          </div>
        ) : <p style={muted}>No active colours — customers can&apos;t pick a balloon colour until you enable some.</p>}
        {active.length === 1 && <p style={{ ...muted, marginTop: 8 }}>Add at least two active colours so customers can choose a combination.</p>}
      </div>

      {isLoading ? <SkeletonTable rows={8} cols={5} /> : isError ? (
        <EmptyState title="Couldn't load colours" message="Please try again." />
      ) : !list.length ? (
        <EmptyState title="No colours yet" message="Add your first colour above." />
      ) : (
        <div className="admin-table-wrapper">
          <table className="admin-table">
            <thead><tr><th style={{ width: 130 }}>Sequence</th><th>Colour</th><th>Hex</th><th>Offered to customers</th><th /></tr></thead>
            <tbody>
              {list.map((c, i) => (
                <tr key={c.id} style={c.is_active ? undefined : { opacity: 0.6 }}>
                  <td>
                    <b style={{ display: 'inline-block', width: 22, ...muted }}>{i + 1}</b>
                    <button className="btn btn-ghost btn-sm" aria-label={`Move ${c.name} up`} disabled={i === 0 || reorder.isPending} onClick={() => move(i, -1)}>↑</button>
                    <button className="btn btn-ghost btn-sm" aria-label={`Move ${c.name} down`} disabled={i === list.length - 1 || reorder.isPending} onClick={() => move(i, 1)}>↓</button>
                  </td>
                  <td><span style={{ display: 'inline-flex', alignItems: 'center', gap: 10 }}><Swatch hex={c.hex_code} /><b>{c.name}</b></span></td>
                  <td><code>{c.hex_code}</code></td>
                  <td>
                    <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
                      <input type="checkbox" checked={c.is_active} disabled={update.isPending}
                        onChange={(e) => update.mutate({ id: c.id, body: { is_active: e.target.checked } })} />
                      {c.is_active ? 'On' : 'Off'}
                    </label>
                  </td>
                  <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
                    <button className="btn btn-secondary btn-sm" onClick={() => setEditing({ id: c.id, name: c.name, hex_code: c.hex_code })}>Edit</button>{' '}
                    <button className="btn btn-danger btn-sm" onClick={() => setDeleting(c)}>Remove</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p style={{ ...muted, marginTop: 12, fontSize: 13 }}>
        Existing bookings keep the exact colours the customer chose, so editing, turning off or removing a colour never changes an order already placed.
      </p>

      <Modal
        open={!!editing}
        onClose={() => setEditing(null)}
        title="Edit colour"
        footer={(
          <>
            <button className="btn btn-secondary" onClick={() => setEditing(null)}>Cancel</button>
            <button
              className="btn btn-primary"
              disabled={update.isPending || !editing || editing.name.trim().length < 2 || !HEX.test(editing.hex_code)}
              onClick={() => update.mutate({ id: editing.id, body: { name: editing.name.trim(), hex_code: editing.hex_code } })}
            >
              {update.isPending ? 'Saving…' : 'Save'}
            </button>
          </>
        )}
      >
        {editing && <ColorFields value={editing} onChange={setEditing} />}
      </Modal>

      <ConfirmDialog
        open={!!deleting}
        onClose={() => setDeleting(null)}
        onConfirm={() => remove.mutate(deleting.id)}
        title="Remove colour?"
        message={deleting ? `"${deleting.name}" will no longer be offered. Existing bookings are not affected.` : ''}
        danger
        loading={remove.isPending}
      />
    </div>
  );
}

function FinishesPanel() {
  const queryClient = useQueryClient();
  const { data, isLoading, isError } = useQuery({ queryKey: ['balloon-finishes'], queryFn: colorsApi.listFinishes });
  const [name, setName] = useState('');
  const [editing, setEditing] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['balloon-finishes'] });
  const fail = (fallback) => (e) => toast.error(e?.response?.data?.error?.message ?? fallback);

  const create = useMutation({
    mutationFn: () => colorsApi.createFinish({ name: name.trim() }),
    onSuccess: () => { toast.success('Finish added.'); setName(''); refresh(); },
    onError: fail('Could not add the finish.'),
  });
  const update = useMutation({
    mutationFn: ({ id, body }) => colorsApi.updateFinish(id, body),
    onSuccess: () => { setEditing(null); refresh(); },
    onError: fail('Could not update the finish.'),
  });
  const remove = useMutation({
    mutationFn: (id) => colorsApi.removeFinish(id),
    onSuccess: () => { toast.success('Finish removed.'); setDeleting(null); refresh(); },
    onError: (e) => { setDeleting(null); fail('Could not remove the finish.')(e); },
  });
  const reorder = useMutation({ mutationFn: (ids) => colorsApi.reorderFinishes(ids), onSuccess: refresh, onError: fail('Could not save the order.') });

  const list = data ?? [];
  const move = (index, delta) => {
    const ids = list.map((f) => f.id);
    const target = index + delta;
    if (target < 0 || target >= ids.length) return;
    [ids[index], ids[target]] = [ids[target], ids[index]];
    reorder.mutate(ids);
  };

  return (
    <div>
      <div className="admin-card" style={{ padding: 16, marginBottom: 16 }}>
        <h3 style={{ fontSize: 14, margin: '0 0 10px' }}>Add a finish</h3>
        <form onSubmit={(e) => { e.preventDefault(); if (name.trim().length >= 2) create.mutate(); }} style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <input className="admin-input" placeholder="e.g. Pastel" maxLength={60} value={name} onChange={(e) => setName(e.target.value)} style={{ flex: '1 1 240px' }} />
          <button className="btn btn-primary" type="submit" disabled={name.trim().length < 2 || create.isPending}>{create.isPending ? 'Adding…' : 'Add finish'}</button>
        </form>
        <p style={{ ...muted, margin: '10px 0 0', fontSize: 12.5 }}>
          Shown under the colours in the app as a single choice. The first active finish is pre-selected, so put the most common one first.
        </p>
      </div>

      {isLoading ? <SkeletonTable rows={4} cols={3} /> : isError ? (
        <EmptyState title="Couldn't load finishes" message="Please try again." />
      ) : !list.length ? (
        <EmptyState title="No finishes yet" message="Without any, customers just choose colours." />
      ) : (
        <div className="admin-table-wrapper">
          <table className="admin-table">
            <thead><tr><th style={{ width: 130 }}>Sequence</th><th>Finish</th><th>Offered to customers</th><th /></tr></thead>
            <tbody>
              {list.map((f, i) => (
                <tr key={f.id} style={f.is_active ? undefined : { opacity: 0.6 }}>
                  <td>
                    <b style={{ display: 'inline-block', width: 22, ...muted }}>{i + 1}</b>
                    <button className="btn btn-ghost btn-sm" aria-label={`Move ${f.name} up`} disabled={i === 0 || reorder.isPending} onClick={() => move(i, -1)}>↑</button>
                    <button className="btn btn-ghost btn-sm" aria-label={`Move ${f.name} down`} disabled={i === list.length - 1 || reorder.isPending} onClick={() => move(i, 1)}>↓</button>
                  </td>
                  <td><b>{f.name}</b></td>
                  <td>
                    <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
                      <input type="checkbox" checked={f.is_active} disabled={update.isPending} onChange={(e) => update.mutate({ id: f.id, body: { is_active: e.target.checked } })} />
                      {f.is_active ? 'On' : 'Off'}
                    </label>
                  </td>
                  <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
                    <button className="btn btn-secondary btn-sm" onClick={() => setEditing({ id: f.id, name: f.name })}>Edit</button>{' '}
                    <button className="btn btn-danger btn-sm" onClick={() => setDeleting(f)}>Remove</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal
        open={!!editing}
        onClose={() => setEditing(null)}
        title="Edit finish"
        footer={(
          <>
            <button className="btn btn-secondary" onClick={() => setEditing(null)}>Cancel</button>
            <button className="btn btn-primary" disabled={update.isPending || !editing || editing.name.trim().length < 2}
              onClick={() => update.mutate({ id: editing.id, body: { name: editing.name.trim() } })}>{update.isPending ? 'Saving…' : 'Save'}</button>
          </>
        )}
      >
        {editing && <input className="admin-input" maxLength={60} value={editing.name} onChange={(e) => setEditing({ ...editing, name: e.target.value })} style={{ width: '100%' }} />}
      </Modal>
      <ConfirmDialog open={!!deleting} onClose={() => setDeleting(null)} onConfirm={() => remove.mutate(deleting.id)} title="Remove finish?"
        message={deleting ? `"${deleting.name}" will no longer be offered. Existing bookings keep what they chose.` : ''} danger loading={remove.isPending} />
    </div>
  );
}

export default function ColorsPage() {
  const [tab, setTab] = useState('colours');
  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <h1>Balloon Colours &amp; Finishes</h1>
          <p>What customers choose in the app&apos;s &ldquo;Choose your balloon colours&rdquo; step, in this order</p>
        </div>
      </div>
      <div className="admin-tabs">
        {[['colours', 'Colours'], ['finishes', 'Finishes']].map(([key, label]) => (
          <button key={key} className={`admin-tab${tab === key ? ' active' : ''}`} onClick={() => setTab(key)}>{label}</button>
        ))}
      </div>
      {tab === 'colours' ? <ColoursPanel /> : <FinishesPanel />}
    </div>
  );
}
