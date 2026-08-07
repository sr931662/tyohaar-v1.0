import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { vendorPackagesApi, vendorServiceIoApi } from '../../api';
import { ConfirmDialog } from '../../../admin/components/ui/Modal';
import ImageUploadField from '../../components/ImageUploadField';
import ItemImportExportBar from '../../components/ItemImportExportBar';
import AttachPackagesModal from '../../components/AttachPackagesModal';
import { PACKAGE_UNIT_OPTIONS } from '../../../constants/packageUnits';

// ── Common Services Modal (vendor-wide service templates) ──────────────────────
// Reusable services (Photography, DJ, Makeup, etc.) owned by the vendor, not
// tied to any one package. Attached to individual packages from the Package
// Services modal. Mirrors CommonItemsModal exactly, minus the returnable flag
// (doesn't apply to a labor service).

export default function CommonServicesModal({ onClose }) {
  const qc = useQueryClient();
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [newService, setNewService] = useState({ name: '', description: '', quantity: 1, max_quantity: '', unit: '', base_price: '', is_mandatory: true, cover_image_url: '' });
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [attachTarget, setAttachTarget] = useState(null);

  const { data: services = [], isLoading } = useQuery({
    queryKey: ['vendor-common-services'],
    queryFn: () => vendorPackagesApi.listCommonServices(),
  });

  const invalidate = () => qc.invalidateQueries(['vendor-common-services']);

  const addMutation = useMutation({
    mutationFn: (body) => vendorPackagesApi.createCommonService(body),
    onSuccess: () => {
      toast.success('Service added.');
      toast.message('Remember to attach it to a package — customers won\'t see it until you do.');
      invalidate();
      setNewService({ name: '', description: '', quantity: 1, max_quantity: '', unit: '', base_price: '', is_mandatory: true, cover_image_url: '' });
    },
    onError: (err) => toast.error(err?.response?.data?.detail ?? 'Failed to add service.'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ serviceId, body }) => vendorPackagesApi.updateCommonService(serviceId, body),
    onSuccess: () => { toast.success('Service updated.'); invalidate(); setEditingId(null); },
    onError: (err) => toast.error(err?.response?.data?.detail ?? 'Failed to update service.'),
  });

  const deleteMutation = useMutation({
    mutationFn: (serviceId) => vendorPackagesApi.deleteCommonService(serviceId),
    onSuccess: () => { toast.success('Service deleted.'); invalidate(); setConfirmDelete(null); },
    onError: () => toast.error('Failed to delete service.'),
  });

  const attachMutation = useMutation({
    mutationFn: ({ serviceId, packageIds }) => vendorPackagesApi.attachAllCommonService(serviceId, packageIds),
    onSuccess: (result) => { toast.success(`Attached to ${result.attached_count} package(s).`); invalidate(); },
    onError: (err) => toast.error(err?.response?.data?.detail ?? 'Failed to attach to packages.'),
  });

  const startEdit = (service) => {
    setEditingId(service.id);
    setEditForm({ name: service.name, description: service.description ?? '', quantity: service.quantity, max_quantity: service.max_quantity ?? '', unit: service.unit ?? '', base_price: service.base_price, is_mandatory: service.is_mandatory, cover_image_url: service.cover_image_url ?? '' });
  };

  const setNF = (k, v) => setNewService((f) => ({ ...f, [k]: v }));
  const setEF = (k, v) => setEditForm((f) => ({ ...f, [k]: v }));

  const handleAdd = (e) => {
    e.preventDefault();
    if (!newService.name.trim()) return toast.error('Service name is required.');
    if (!newService.base_price || isNaN(Number(newService.base_price))) return toast.error('Enter a valid price.');
    addMutation.mutate({
      ...newService,
      quantity: Number(newService.quantity),
      max_quantity: newService.max_quantity !== '' ? Number(newService.max_quantity) : undefined,
      base_price: Number(newService.base_price),
      unit: newService.unit || undefined,
      description: newService.description || undefined,
      cover_image_url: newService.cover_image_url || undefined,
    });
  };

  const handleUpdate = (serviceId) => {
    if (!editForm.name.trim()) return toast.error('Service name is required.');
    updateMutation.mutate({
      serviceId,
      body: {
        ...editForm,
        quantity: Number(editForm.quantity),
        max_quantity: editForm.max_quantity !== '' ? Number(editForm.max_quantity) : null,
        base_price: Number(editForm.base_price),
        unit: editForm.unit || undefined,
        description: editForm.description || undefined,
        cover_image_url: editForm.cover_image_url || null,
      },
    });
  };

  return (
    <div className="admin-modal-overlay" onClick={onClose}>
      <div className="admin-modal lg" onClick={(e) => e.stopPropagation()}>
        <div className="admin-modal-header">
          <div>
            <h2 className="admin-modal-title">Common Services</h2>
            <p style={{ margin: '2px 0 0', fontSize: 12, color: 'var(--text-tertiary)' }}>
              Reusable services (Photography, DJ, Makeup…) you can attach to any of your packages instead of recreating them each time.
            </p>
          </div>
          <button className="admin-modal-close" onClick={onClose}>×</button>
        </div>
        <div style={{ padding: '20px 24px 24px' }}>
          <ItemImportExportBar scope="common" invalidateKey={['vendor-common-services']} entityApi={vendorServiceIoApi} entityLabel="services" />
          {isLoading ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 20 }}>
              {[0, 1].map((i) => <div key={i} className="skeleton skeleton-card" style={{ height: 56 }} />)}
            </div>
          ) : !services.length ? (
            <p style={{ color: 'var(--text-tertiary)', fontSize: 13, textAlign: 'center', padding: '16px 0', marginBottom: 4 }}>No common services yet. Add one below.</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 20 }}>
              {services.map((service) => editingId === service.id ? (
                <div key={service.id} className="admin-card" style={{ padding: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
                  <div className="form-row-2-1" style={{ gap: 10 }}>
                    <input className="admin-input" value={editForm.name} onChange={(e) => setEF('name', e.target.value)} placeholder="Service name" />
                    <input className="admin-input" type="number" min="0" value={editForm.base_price} onChange={(e) => setEF('base_price', e.target.value)} placeholder="Price (₹)" />
                  </div>
                  <div className="form-row-3" style={{ gap: 10 }}>
                    <input className="admin-input" type="number" min="1" value={editForm.quantity} onChange={(e) => setEF('quantity', e.target.value)} placeholder="Qty" />
                    <select className="admin-input" value={editForm.unit} onChange={(e) => setEF('unit', e.target.value)}>
                      <option value="">Unit (optional)</option>
                      {PACKAGE_UNIT_OPTIONS.map((u) => <option key={u.value} value={u.value}>{u.label}</option>)}
                    </select>
                    <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, cursor: 'pointer' }}>
                      <input type="checkbox" checked={editForm.is_mandatory} onChange={(e) => setEF('is_mandatory', e.target.checked)} />
                      Mandatory
                    </label>
                  </div>
                  <input className="admin-input" type="number" min={editForm.quantity || 1} value={editForm.max_quantity} onChange={(e) => setEF('max_quantity', e.target.value)} placeholder="Max qty (optional)" />
                  <input className="admin-input" value={editForm.description} onChange={(e) => setEF('description', e.target.value)} placeholder="Description (optional)" />
                  <ImageUploadField
                    label="Cover image"
                    value={editForm.cover_image_url}
                    onChange={(url) => setEF('cover_image_url', url)}
                    usage="package_image"
                    placeholder="Cover image URL (https://...)"
                  />
                  <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                    <button className="btn btn-secondary btn-sm" onClick={() => setEditingId(null)}>Cancel</button>
                    <button className="btn btn-primary btn-sm" onClick={() => handleUpdate(service.id)} disabled={updateMutation.isPending}>Save</button>
                  </div>
                </div>
              ) : (
                <div key={service.id} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 14px', borderRadius: 10, background: 'var(--bg-base)', border: '1px solid var(--border-subtle)' }}>
                  {service.cover_image_url && (
                    <img
                      src={service.cover_image_url}
                      alt=""
                      style={{ width: 42, height: 42, borderRadius: 8, objectFit: 'cover', border: '1px solid var(--border-subtle)', flexShrink: 0 }}
                      onError={(e) => { e.target.style.display = 'none'; }}
                    />
                  )}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--text-primary)' }}>
                      {service.name}
                      {!service.is_mandatory && <span style={{ marginLeft: 6, fontSize: 11, color: 'var(--text-tertiary)', fontWeight: 400 }}>optional</span>}
                    </div>
                    {service.description && <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginTop: 1 }}>{service.description}</div>}
                    <div style={{ fontSize: 11, marginTop: 2, color: service.attached_package_count > 0 ? 'var(--text-tertiary)' : '#f59e0b', fontWeight: service.attached_package_count > 0 ? 400 : 600 }}>
                      {service.attached_package_count > 0
                        ? `Attached to ${service.attached_package_count} package${service.attached_package_count === 1 ? '' : 's'}`
                        : 'Not attached to any package yet'}
                    </div>
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
                    {service.quantity > 1 && `${service.quantity}${service.unit ? ' ' + service.unit : 'x'} · `}
                    ₹{Number(service.base_price).toLocaleString('en-IN')}
                  </div>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <button className="btn btn-secondary btn-sm" onClick={() => attachMutation.mutate({ serviceId: service.id, packageIds: null })} disabled={attachMutation.isPending}>Attach to all</button>
                    <button className="btn btn-secondary btn-sm" onClick={() => setAttachTarget(service)}>Custom Attach</button>
                    <button className="btn btn-secondary btn-sm" onClick={() => startEdit(service)}>Edit</button>
                    <button className="btn btn-sm" style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', color: '#ef4444' }} onClick={() => setConfirmDelete(service)}>✕</button>
                  </div>
                </div>
              ))}
            </div>
          )}

          <h4 style={{ margin: '0 0 12px', fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>Add Common Service</h4>
          <form onSubmit={handleAdd} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div className="form-row-2-1" style={{ gap: 10 }}>
              <input className="admin-input" value={newService.name} onChange={(e) => setNF('name', e.target.value)} placeholder="Service name *" />
              <input className="admin-input" type="number" min="0" value={newService.base_price} onChange={(e) => setNF('base_price', e.target.value)} placeholder="Price (₹) *" />
            </div>
            <div className="form-row-3" style={{ gap: 10 }}>
              <input className="admin-input" type="number" min="1" value={newService.quantity} onChange={(e) => setNF('quantity', e.target.value)} placeholder="Qty" />
              <select className="admin-input" value={newService.unit} onChange={(e) => setNF('unit', e.target.value)}>
                <option value="">Unit (optional)</option>
                {PACKAGE_UNIT_OPTIONS.map((u) => <option key={u.value} value={u.value}>{u.label}</option>)}
              </select>
              <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, cursor: 'pointer' }}>
                <input type="checkbox" checked={newService.is_mandatory} onChange={(e) => setNF('is_mandatory', e.target.checked)} />
                Mandatory
              </label>
            </div>
            <input className="admin-input" type="number" min={newService.quantity || 1} value={newService.max_quantity} onChange={(e) => setNF('max_quantity', e.target.value)} placeholder="Max qty (optional)" />
            <input className="admin-input" value={newService.description} onChange={(e) => setNF('description', e.target.value)} placeholder="Description (optional)" />
            <ImageUploadField
              label="Cover image (optional)"
              value={newService.cover_image_url}
              onChange={(url) => setNF('cover_image_url', url)}
              usage="package_image"
              placeholder="Cover image URL (https://...)"
            />
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button type="submit" className="btn btn-primary" disabled={addMutation.isPending}>
                {addMutation.isPending ? 'Adding…' : '+ Add Common Service'}
              </button>
            </div>
          </form>
        </div>
      </div>

      <ConfirmDialog
        open={!!confirmDelete}
        onClose={() => setConfirmDelete(null)}
        onConfirm={() => deleteMutation.mutate(confirmDelete.id)}
        title="Delete Common Service"
        message={`Delete "${confirmDelete?.name}"? It will be removed from every package it's attached to.`}
        loading={deleteMutation.isPending}
      />

      <AttachPackagesModal
        open={!!attachTarget}
        onClose={() => setAttachTarget(null)}
        isAttaching={attachMutation.isPending}
        onAttach={(packageIds) =>
          attachMutation.mutate(
            { serviceId: attachTarget.id, packageIds },
            { onSuccess: () => setAttachTarget(null) },
          )
        }
      />
    </div>
  );
}
