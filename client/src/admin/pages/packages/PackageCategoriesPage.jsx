import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { packagesApi } from '../../api';
import { formatDate } from '../../utils/format';
import EmptyState from '../../components/ui/EmptyState';
import Modal, { ConfirmDialog } from '../../components/ui/Modal';
import ImageUploadField from '../../components/ui/ImageUploadField';

export default function PackageCategoriesPage() {
  const qc = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [deleteId, setDeleteId] = useState(null);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [iconUrl, setIconUrl] = useState('');

  const { data: categories = [], isLoading } = useQuery({
    queryKey: ['packages', 'categories'],
    queryFn: () => packagesApi.listCategories(),
  });

  const saveMutation = useMutation({
    mutationFn: (body) => editItem
      ? packagesApi.updateCategory(editItem.id, body)
      : packagesApi.createCategory(body),
    onSuccess: () => {
      toast.success(editItem ? 'Category updated' : 'Category created');
      qc.invalidateQueries(['packages', 'categories']);
      setModalOpen(false);
      setEditItem(null); setName(''); setDescription(''); setIconUrl('');
    },
    onError: () => toast.error('Save failed'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id) => packagesApi.deleteCategory(id),
    onSuccess: () => { toast.success('Deleted'); qc.invalidateQueries(['packages', 'categories']); setDeleteId(null); },
    onError: () => toast.error('Delete failed'),
  });

  const openEdit = (cat) => {
    setEditItem(cat); setName(cat.name); setDescription(cat.description ?? ''); setIconUrl(cat.icon_url ?? '');
    setModalOpen(true);
  };

  const openNew = () => {
    setEditItem(null); setName(''); setDescription(''); setIconUrl('');
    setModalOpen(true);
  };

  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <h1>Package Categories</h1>
          <p>Manage categories used for grouping packages</p>
        </div>
        <div className="admin-page-header-actions">
          <button className="btn btn-primary" onClick={openNew}>+ New Category</button>
        </div>
      </div>

      {!categories.length && !isLoading ? (
        <EmptyState title="No categories yet" action={<button className="btn btn-primary" onClick={openNew}>Create first category</button>} />
      ) : (
        <div className="admin-table-wrapper">
          <table className="admin-table">
            <thead>
              <tr><th>Name</th><th>Description</th><th>Packages</th><th>Created</th><th>Actions</th></tr>
            </thead>
            <tbody>
              {categories.map((cat) => (
                <tr key={cat.id}>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      {cat.icon_url && (
                        <img src={cat.icon_url} alt="" style={{ width: 24, height: 24, borderRadius: 4, objectFit: 'cover' }} />
                      )}
                      <div className="admin-user-name">{cat.name}</div>
                    </div>
                  </td>
                  <td><span className="text-secondary">{cat.description ?? '—'}</span></td>
                  <td>{cat.package_count ?? 0}</td>
                  <td>{formatDate(cat.created_at)}</td>
                  <td>
                    <div style={{ display: 'flex', gap: 6 }}>
                      <button className="btn btn-secondary btn-sm" onClick={() => openEdit(cat)}>Edit</button>
                      <button className="btn btn-danger btn-sm" onClick={() => setDeleteId(cat.id)}>Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editItem ? 'Edit Category' : 'New Category'}
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setModalOpen(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={() => saveMutation.mutate({ name, description, icon_url: iconUrl || undefined })} disabled={!name || saveMutation.isPending}>
              {saveMutation.isPending ? 'Saving…' : 'Save'}
            </button>
          </>
        }
      >
        <div className="form-group">
          <label className="form-label required">Name</label>
          <input className="form-control" value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Photography" />
        </div>
        <div className="form-group">
          <label className="form-label">Description</label>
          <textarea className="form-control" value={description} onChange={e => setDescription(e.target.value)} rows={3} />
        </div>
        <div className="form-group">
          <label className="form-label">Icon</label>
          <ImageUploadField value={iconUrl} onChange={setIconUrl} usage="product_image" />
        </div>
      </Modal>

      <ConfirmDialog
        open={!!deleteId}
        onClose={() => setDeleteId(null)}
        onConfirm={() => deleteMutation.mutate(deleteId)}
        title="Delete Category"
        message="Are you sure? Packages in this category will lose their category assignment."
        danger
        loading={deleteMutation.isPending}
      />
    </div>
  );
}
