import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { vendorPackagesApi, vendorServiceIoApi } from '../../api';
import { ConfirmDialog } from '../../../admin/components/ui/Modal';
import ImageUploadField from '../../components/ImageUploadField';
import ItemImportExportBar from '../../components/ItemImportExportBar';
import { PACKAGE_UNIT_OPTIONS } from '../../../constants/packageUnits';

// ── Package Services Modal ──────────────────────────────────────────────────────
// Mirrors PackageItemsModal exactly, minus the returnable flag (doesn't apply
// to a labor service).

export default function PackageServicesModal({ pkg, onClose }) {
  const qc = useQueryClient();
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [newService, setNewService] = useState({ name: '', description: '', quantity: 1, max_quantity: '', unit: '', base_price: '', is_mandatory: true, cover_image_url: '' });
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [managingImagesFor, setManagingImagesFor] = useState(null);
  const [attachingId, setAttachingId] = useState('');

  const { data: services = [], isLoading } = useQuery({
    queryKey: ['pkg-services', pkg.id],
    queryFn: () => vendorPackagesApi.listServices(pkg.id),
  });

  const { data: commonServices = [] } = useQuery({
    queryKey: ['vendor-common-services'],
    queryFn: () => vendorPackagesApi.listCommonServices(),
  });

  const invalidate = () => qc.invalidateQueries(['pkg-services', pkg.id]);

  const addMutation = useMutation({
    mutationFn: (body) => vendorPackagesApi.addService(pkg.id, { ...body, package_id: pkg.id }),
    onSuccess: () => { toast.success('Service added.'); invalidate(); setNewService({ name: '', description: '', quantity: 1, max_quantity: '', unit: '', base_price: '', is_mandatory: true, cover_image_url: '' }); },
    onError: (err) => toast.error(err?.response?.data?.detail ?? 'Failed to add service.'),
  });

  const attachMutation = useMutation({
    mutationFn: (serviceId) => vendorPackagesApi.attachCommonService(pkg.id, serviceId),
    onSuccess: () => { toast.success('Common service attached.'); invalidate(); setAttachingId(''); },
    onError: (err) => toast.error(err?.response?.data?.detail ?? 'Failed to attach service.'),
  });

  const detachMutation = useMutation({
    mutationFn: (serviceId) => vendorPackagesApi.detachCommonService(pkg.id, serviceId),
    onSuccess: () => { toast.success('Common service detached.'); invalidate(); },
    onError: (err) => toast.error(err?.response?.data?.detail ?? 'Failed to detach service.'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ serviceId, body }) => vendorPackagesApi.updateService(pkg.id, serviceId, body),
    onSuccess: () => { toast.success('Service updated.'); invalidate(); setEditingId(null); },
    onError: (err) => toast.error(err?.response?.data?.detail ?? 'Failed to update service.'),
  });

  const deleteMutation = useMutation({
    mutationFn: (serviceId) => vendorPackagesApi.deleteService(pkg.id, serviceId),
    onSuccess: () => { toast.success('Service removed.'); invalidate(); setConfirmDelete(null); },
    onError: () => toast.error('Failed to remove service.'),
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

  const isLocked = pkg.status === 'pending_review';

  return (
    <div className="admin-modal-overlay" onClick={onClose}>
      <div className="admin-modal lg" onClick={(e) => e.stopPropagation()}>
        <div className="admin-modal-header">
          <div>
            <h2 className="admin-modal-title">Package Services</h2>
            <p style={{ margin: '2px 0 0', fontSize: 12, color: 'var(--text-tertiary)' }}>{pkg.name}</p>
          </div>
          <button className="admin-modal-close" onClick={onClose}>×</button>
        </div>
        <div style={{ padding: '20px 24px 24px' }}>
          {isLocked && (
            <div style={{ padding: '10px 14px', borderRadius: 8, background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.2)', fontSize: 13, color: '#f59e0b', marginBottom: 16 }}>
              This package is under review. Services cannot be edited.
            </div>
          )}

          <ItemImportExportBar scope="package" packageId={pkg.id} disabled={isLocked} invalidateKey={['pkg-services', pkg.id]} entityApi={vendorServiceIoApi} entityLabel="services" />

          {/* Existing services */}
          {isLoading ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 20 }}>
              {[0, 1].map((i) => <div key={i} className="skeleton skeleton-card" style={{ height: 56 }} />)}
            </div>
          ) : !services.length ? (
            <p style={{ color: 'var(--text-tertiary)', fontSize: 13, textAlign: 'center', padding: '16px 0', marginBottom: 4 }}>No services yet. Add one below.</p>
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
                  <div>
                    <input className="admin-input" type="number" min={editForm.quantity || 1} value={editForm.max_quantity} onChange={(e) => setEF('max_quantity', e.target.value)} placeholder="Max customer can pick (optional)" />
                    <p style={{ margin: '4px 0 0', fontSize: 11, color: 'var(--text-tertiary)' }}>Leave blank for no cap — e.g. cap photographers at 3.</p>
                  </div>
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
                  {(service.cover_image_url || service.images?.[0]?.image_url) && (
                    <img
                      src={service.cover_image_url || service.images[0].image_url}
                      alt=""
                      style={{ width: 42, height: 42, borderRadius: 8, objectFit: 'cover', border: '1px solid var(--border-subtle)', flexShrink: 0 }}
                      onError={(e) => { e.target.style.display = 'none'; }}
                    />
                  )}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--text-primary)' }}>
                      {service.name}
                      {service.is_common && <span style={{ marginLeft: 6, fontSize: 11, color: 'var(--color-primary,#6366f1)', fontWeight: 400 }}>common</span>}
                      {!service.is_mandatory && <span style={{ marginLeft: 6, fontSize: 11, color: 'var(--text-tertiary)', fontWeight: 400 }}>optional</span>}
                    </div>
                    {service.description && <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginTop: 1 }}>{service.description}</div>}
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
                    {service.quantity > 1 && `${service.quantity}${service.unit ? ' ' + service.unit : 'x'} · `}
                    ₹{Number(service.base_price).toLocaleString('en-IN')}
                  </div>
                  {!isLocked && (
                    <div style={{ display: 'flex', gap: 6 }}>
                      {service.is_common ? (
                        <button
                          className="btn btn-sm"
                          style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', color: '#ef4444' }}
                          onClick={() => detachMutation.mutate(service.id)}
                          disabled={detachMutation.isPending}
                        >
                          Detach
                        </button>
                      ) : (
                        <>
                          <button className="btn btn-secondary btn-sm" onClick={() => setManagingImagesFor(service)}>
                            Photos{service.images?.length ? ` (${service.images.length})` : ''}
                          </button>
                          <button className="btn btn-secondary btn-sm" onClick={() => startEdit(service)}>Edit</button>
                          <button className="btn btn-sm" style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', color: '#ef4444' }} onClick={() => setConfirmDelete(service)}>✕</button>
                        </>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {!isLocked && commonServices.length > 0 && (
            <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 20 }}>
              <select
                className="admin-input"
                value={attachingId}
                onChange={(e) => setAttachingId(e.target.value)}
                style={{ flex: 1 }}
              >
                <option value="">Attach a common service…</option>
                {commonServices
                  .filter((cs) => !services.some((s) => s.id === cs.id))
                  .map((cs) => (
                    <option key={cs.id} value={cs.id}>
                      {cs.name} · ₹{Number(cs.base_price).toLocaleString('en-IN')}
                    </option>
                  ))}
              </select>
              <button
                className="btn btn-secondary"
                disabled={!attachingId || attachMutation.isPending}
                onClick={() => attachMutation.mutate(attachingId)}
              >
                {attachMutation.isPending ? 'Attaching…' : 'Attach'}
              </button>
            </div>
          )}

          {/* Add new service */}
          {!isLocked && (
            <div>
              <h4 style={{ margin: '0 0 12px', fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>Add New Service</h4>
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
                <div>
                  <input className="admin-input" type="number" min={newService.quantity || 1} value={newService.max_quantity} onChange={(e) => setNF('max_quantity', e.target.value)} placeholder="Max customer can pick (optional)" />
                  <p style={{ margin: '4px 0 0', fontSize: 11, color: 'var(--text-tertiary)' }}>Leave blank for no cap. More gallery photos can be added after creating the service.</p>
                </div>
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
                    {addMutation.isPending ? 'Adding…' : '+ Add Service'}
                  </button>
                </div>
              </form>
            </div>
          )}
        </div>
      </div>

      <ConfirmDialog
        open={!!confirmDelete}
        onClose={() => setConfirmDelete(null)}
        onConfirm={() => deleteMutation.mutate(confirmDelete.id)}
        title="Remove Service"
        message={`Remove "${confirmDelete?.name}" from this package?`}
        loading={deleteMutation.isPending}
      />

      {managingImagesFor && (
        <PackageServiceImagesModal
          pkgId={pkg.id}
          service={managingImagesFor}
          onClose={() => setManagingImagesFor(null)}
          onChanged={invalidate}
        />
      )}
    </div>
  );
}

// ── Package Service Photos Modal ────────────────────────────────────────────────
// Same idea as PackageItemImagesModal, scoped to one service.

function PackageServiceImagesModal({ pkgId, service, onClose, onChanged }) {
  const qc = useQueryClient();
  const [uploadUrl, setUploadUrl] = useState('');
  const [confirmDelete, setConfirmDelete] = useState(null);

  const { data: liveService, isLoading } = useQuery({
    queryKey: ['pkg-service-images', pkgId, service.id],
    queryFn: () => vendorPackagesApi.listServices(pkgId).then((services) => services.find((s) => s.id === service.id) ?? service),
    initialData: service,
  });
  const images = liveService?.images ?? [];
  const coverUrl = liveService?.cover_image_url ?? null;

  const invalidate = () => {
    qc.invalidateQueries(['pkg-service-images', pkgId, service.id]);
    qc.invalidateQueries(['pkg-services', pkgId]);
    onChanged?.();
  };

  const addMutation = useMutation({
    mutationFn: (imageUrl) => vendorPackagesApi.addServiceImage(pkgId, service.id, { image_url: imageUrl }),
    onSuccess: () => { toast.success('Image added.'); invalidate(); setUploadUrl(''); },
    onError: (err) => toast.error(err?.response?.data?.detail ?? 'Failed to add image.'),
  });

  const deleteMutation = useMutation({
    mutationFn: (imageId) => vendorPackagesApi.deleteServiceImage(pkgId, service.id, imageId),
    onSuccess: () => { toast.success('Image removed.'); invalidate(); setConfirmDelete(null); },
    onError: () => toast.error('Failed to remove image.'),
  });

  const coverMutation = useMutation({
    mutationFn: (imageUrl) => vendorPackagesApi.updateService(pkgId, service.id, { cover_image_url: imageUrl }),
    onSuccess: () => { toast.success('Cover updated.'); invalidate(); },
    onError: () => toast.error('Failed to set cover.'),
  });

  return (
    <div className="admin-modal-overlay" onClick={onClose}>
      <div className="admin-modal" onClick={(e) => e.stopPropagation()}>
        <div className="admin-modal-header">
          <div>
            <h2 className="admin-modal-title">Service Photos</h2>
            <p style={{ margin: '2px 0 0', fontSize: 12, color: 'var(--text-tertiary)' }}>{service.name}</p>
          </div>
          <button className="admin-modal-close" onClick={onClose}>×</button>
        </div>
        <div style={{ padding: '20px 24px 24px' }}>
          {isLoading ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(110px, 1fr))', gap: 10, marginBottom: 20 }}>
              {[0, 1].map((i) => <div key={i} className="skeleton" style={{ height: 90, borderRadius: 10 }} />)}
            </div>
          ) : images.length > 0 ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(110px, 1fr))', gap: 10, marginBottom: 20 }}>
              {images.map((img) => {
                const isCover = coverUrl === img.image_url;
                return (
                  <div key={img.id} style={{ position: 'relative', borderRadius: 10, overflow: 'hidden', border: isCover ? '2px solid var(--color-primary,#6366f1)' : '1px solid var(--border-subtle)', aspectRatio: '1/1', background: 'var(--bg-base)' }}>
                    <img src={img.image_url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} onError={(e) => { e.target.style.display = 'none'; }} />
                    <button
                      onClick={() => setConfirmDelete(img)}
                      style={{ position: 'absolute', top: 4, right: 4, width: 20, height: 20, borderRadius: '50%', border: 'none', background: 'rgba(239,68,68,0.85)', color: '#fff', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11 }}
                    >×</button>
                    {isCover ? (
                      <span style={{ position: 'absolute', bottom: 4, left: 4, padding: '2px 7px', borderRadius: 6, background: 'var(--color-primary,#6366f1)', color: '#fff', fontSize: 10, fontWeight: 600 }}>Cover</span>
                    ) : (
                      <button
                        onClick={() => coverMutation.mutate(img.image_url)}
                        disabled={coverMutation.isPending}
                        style={{ position: 'absolute', bottom: 4, left: 4, padding: '2px 7px', borderRadius: 6, border: 'none', background: 'rgba(0,0,0,0.55)', color: '#fff', fontSize: 10, cursor: 'pointer' }}
                      >Set as cover</button>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <p style={{ color: 'var(--text-tertiary)', fontSize: 13, marginBottom: 16 }}>No photos yet for this service.</p>
          )}

          <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
            <div style={{ flex: 1 }}>
              <ImageUploadField value={uploadUrl} onChange={setUploadUrl} usage="package_image" placeholder="Image URL (https://...)" />
            </div>
            <button
              className="btn btn-primary"
              disabled={!uploadUrl || addMutation.isPending}
              onClick={() => addMutation.mutate(uploadUrl)}
            >
              {addMutation.isPending ? 'Adding…' : '+ Add'}
            </button>
          </div>
        </div>
      </div>

      <ConfirmDialog
        open={!!confirmDelete}
        onClose={() => setConfirmDelete(null)}
        onConfirm={() => deleteMutation.mutate(confirmDelete.id)}
        title="Remove Photo"
        message="Remove this photo from the service?"
        loading={deleteMutation.isPending}
      />
    </div>
  );
}
