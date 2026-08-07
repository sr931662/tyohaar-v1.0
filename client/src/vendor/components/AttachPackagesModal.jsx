import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { vendorPackagesApi } from '../api';
import Modal from '../../admin/components/ui/Modal';

// ── Attach Packages Modal ────────────────────────────────────────────────────
// Lets a vendor pick specific packages to attach a common item/service to,
// as an alternative to the all-or-nothing "Attach to all" button. Reuses the
// same attach-all endpoint underneath — it already accepts an explicit
// package_ids list (server/app/schemas/packages/create.py AttachAllRequest).
export default function AttachPackagesModal({ open, onClose, onAttach, isAttaching }) {
  const [selected, setSelected] = useState([]);

  useEffect(() => {
    if (open) setSelected([]);
  }, [open]);

  const { data, isLoading } = useQuery({
    queryKey: ['vendor-packages'],
    queryFn: () => vendorPackagesApi.list({ per_page: 100 }),
    enabled: open,
  });
  const packages = data?.items ?? [];

  const toggle = (id) =>
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));

  const allSelected = packages.length > 0 && selected.length === packages.length;
  const toggleAll = () => setSelected(allSelected ? [] : packages.map((p) => p.id));

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Attach to specific packages"
      footer={
        <>
          <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button
            className="btn btn-primary"
            onClick={() => onAttach(selected)}
            disabled={!selected.length || isAttaching}
          >
            {isAttaching ? 'Attaching…' : `Attach to ${selected.length || 0} package${selected.length === 1 ? '' : 's'}`}
          </button>
        </>
      }
    >
      {isLoading ? (
        <p style={{ color: 'var(--text-tertiary)', fontSize: 13 }}>Loading packages…</p>
      ) : !packages.length ? (
        <p style={{ color: 'var(--text-tertiary)', fontSize: 13 }}>You don't have any packages yet.</p>
      ) : (
        <>
          <label
            style={{
              display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, fontWeight: 600,
              cursor: 'pointer', marginBottom: 10, paddingBottom: 10, borderBottom: '1px solid var(--border-subtle)',
            }}
          >
            <input type="checkbox" checked={allSelected} onChange={toggleAll} />
            Select all ({packages.length})
          </label>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 320, overflowY: 'auto' }}>
            {packages.map((pkg) => (
              <label key={pkg.id} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, cursor: 'pointer' }}>
                <input type="checkbox" checked={selected.includes(pkg.id)} onChange={() => toggle(pkg.id)} />
                {pkg.name}
              </label>
            ))}
          </div>
        </>
      )}
    </Modal>
  );
}
