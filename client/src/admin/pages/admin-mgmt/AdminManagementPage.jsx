import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { adminMgmtApi } from '../../api';
import { formatDateTime } from '../../utils/format';
import StatusBadge from '../../components/ui/StatusBadge';
import Pagination from '../../components/ui/Pagination';
import { SkeletonTable } from '../../components/ui/Skeleton';
import Modal, { ConfirmDialog } from '../../components/ui/Modal';
import { usePagination } from '../../hooks/usePagination';

function AdminsTab() {
  const qc = useQueryClient();
  const { page, perPage, setPage } = usePagination();
  const [open, setOpen] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [form, setForm] = useState({ email: '', name: '', password: '', role: 'admin' });

  const { data, isLoading } = useQuery({
    queryKey: ['admins', { page, perPage }],
    queryFn: () => adminMgmtApi.listAdmins({ page, per_page: perPage }),
  });

  const saveMutation = useMutation({
    mutationFn: (body) => editItem ? adminMgmtApi.updateAdmin(editItem.id, body) : adminMgmtApi.createAdmin(body),
    onSuccess: () => { toast.success(editItem ? 'Admin updated' : 'Admin created'); qc.invalidateQueries(['admins']); setOpen(false); setEditItem(null); },
    onError: () => toast.error('Save failed'),
  });

  const deactivateMutation = useMutation({
    mutationFn: (id) => adminMgmtApi.deactivateAdmin(id),
    onSuccess: () => { toast.success('Admin deactivated'); qc.invalidateQueries(['admins']); },
    onError: () => toast.error('Failed'),
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const pages = data?.pages ?? 1;

  const openEdit = (a) => {
    setEditItem(a);
    setForm({ email: a.email, name: a.name ?? '', password: '', role: a.role ?? 'admin' });
    setOpen(true);
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
        <button className="btn btn-primary" onClick={() => { setEditItem(null); setForm({ email:'', name:'', password:'', role:'admin' }); setOpen(true); }}>
          + New Admin
        </button>
      </div>
      {isLoading ? <SkeletonTable rows={6} cols={5} /> : (
        <div className="admin-table-wrapper">
          <table className="admin-table">
            <thead>
              <tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th><th>Last Login</th><th>Actions</th></tr>
            </thead>
            <tbody>
              {items.map((a) => (
                <tr key={a.id}>
                  <td><div className="admin-user-name">{a.name ?? '—'}</div></td>
                  <td>{a.email}</td>
                  <td><span className="badge badge-blue">{a.role}</span></td>
                  <td><StatusBadge status={a.is_active ? 'active' : 'inactive'} /></td>
                  <td>{a.last_login ? formatDateTime(a.last_login) : 'Never'}</td>
                  <td>
                    <div style={{ display: 'flex', gap: 6 }}>
                      <button className="btn btn-secondary btn-sm" onClick={() => openEdit(a)}>Edit</button>
                      {a.is_active && <button className="btn btn-danger btn-sm" onClick={() => deactivateMutation.mutate(a.id)}>Deactivate</button>}
                    </div>
                  </td>
                </tr>
              ))}
              {!items.length && <tr><td colSpan={6} className="admin-table-empty">No admins</td></tr>}
            </tbody>
          </table>
          <Pagination page={page} pages={pages} total={total} perPage={perPage} onChange={setPage} />
        </div>
      )}

      <Modal open={open} onClose={() => setOpen(false)} title={editItem ? 'Edit Admin' : 'New Admin'}
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setOpen(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={() => saveMutation.mutate(form)} disabled={!form.email || saveMutation.isPending}>
              {saveMutation.isPending ? 'Saving…' : 'Save'}
            </button>
          </>
        }
      >
        <div className="form-row-2">
          <div className="form-group">
            <label className="form-label required">Email</label>
            <input className="form-control" type="email" value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} />
          </div>
          <div className="form-group">
            <label className="form-label">Name</label>
            <input className="form-control" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
          </div>
        </div>
        <div className="form-row-2">
          <div className="form-group">
            <label className="form-label">Role</label>
            <select className="form-control" value={form.role} onChange={e => setForm(f => ({ ...f, role: e.target.value }))}>
              <option value="admin">Admin</option>
              <option value="super_admin">Super Admin</option>
              <option value="support">Support</option>
              <option value="viewer">Viewer</option>
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">{editItem ? 'New Password (leave blank to keep)' : 'Password'}</label>
            <input className="form-control" type="password" value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))} />
          </div>
        </div>
      </Modal>
    </div>
  );
}

function RolesTab() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [form, setForm] = useState({ name: '', description: '' });

  const { data: roles = [] } = useQuery({
    queryKey: ['roles'],
    queryFn: () => adminMgmtApi.listRoles(),
  });

  const saveMutation = useMutation({
    mutationFn: (body) => editItem ? adminMgmtApi.updateRole(editItem.id, body) : adminMgmtApi.createRole(body),
    onSuccess: () => { toast.success('Saved'); qc.invalidateQueries(['roles']); setOpen(false); setEditItem(null); },
    onError: () => toast.error('Failed'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id) => adminMgmtApi.deleteRole(id),
    onSuccess: () => { toast.success('Deleted'); qc.invalidateQueries(['roles']); },
    onError: () => toast.error('Failed'),
  });

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
        <button className="btn btn-primary" onClick={() => { setEditItem(null); setForm({ name:'', description:'' }); setOpen(true); }}>+ New Role</button>
      </div>
      <div className="admin-table-wrapper">
        <table className="admin-table">
          <thead>
            <tr><th>Name</th><th>Description</th><th>Created</th><th>Actions</th></tr>
          </thead>
          <tbody>
            {roles.map((r) => (
              <tr key={r.id}>
                <td><span className="badge badge-blue">{r.name}</span></td>
                <td>{r.description ?? '—'}</td>
                <td>{formatDateTime(r.created_at)}</td>
                <td>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <button className="btn btn-secondary btn-sm" onClick={() => { setEditItem(r); setForm({ name: r.name, description: r.description ?? '' }); setOpen(true); }}>Edit</button>
                    <button className="btn btn-danger btn-sm" onClick={() => deleteMutation.mutate(r.id)}>Delete</button>
                  </div>
                </td>
              </tr>
            ))}
            {!roles.length && <tr><td colSpan={4} className="admin-table-empty">No roles</td></tr>}
          </tbody>
        </table>
      </div>
      <Modal open={open} onClose={() => setOpen(false)} title={editItem ? 'Edit Role' : 'New Role'}
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setOpen(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={() => saveMutation.mutate(form)} disabled={!form.name || saveMutation.isPending}>
              {saveMutation.isPending ? 'Saving…' : 'Save'}
            </button>
          </>
        }
      >
        <div className="form-group"><label className="form-label required">Role Name</label><input className="form-control" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} /></div>
        <div className="form-group"><label className="form-label">Description</label><input className="form-control" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} /></div>
      </Modal>
    </div>
  );
}

function AuditLogsTab() {
  const { page, perPage, setPage } = usePagination();

  const { data, isLoading } = useQuery({
    queryKey: ['audit-logs', { page, perPage }],
    queryFn: () => adminMgmtApi.listAuditLogs({ page, per_page: perPage }),
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const pages = data?.pages ?? 1;

  return (
    isLoading ? <SkeletonTable rows={10} cols={5} /> : (
      <div className="admin-table-wrapper">
        <table className="admin-table">
          <thead>
            <tr><th>Admin</th><th>Action</th><th>Resource</th><th>IP</th><th>Timestamp</th></tr>
          </thead>
          <tbody>
            {items.map((log) => (
              <tr key={log.id}>
                <td>{log.admin?.email ?? log.admin_email ?? '—'}</td>
                <td><code style={{ fontSize: 11 }}>{log.action}</code></td>
                <td style={{ fontSize: 12 }}>{log.resource_type}{log.resource_id ? ` #${log.resource_id.slice(0, 8)}` : ''}</td>
                <td style={{ fontSize: 12 }}>{log.ip_address ?? '—'}</td>
                <td>{formatDateTime(log.created_at)}</td>
              </tr>
            ))}
            {!items.length && <tr><td colSpan={5} className="admin-table-empty">No audit logs</td></tr>}
          </tbody>
        </table>
        <Pagination page={page} pages={pages} total={total} perPage={perPage} onChange={setPage} />
      </div>
    )
  );
}

export default function AdminManagementPage() {
  const [activeTab, setActiveTab] = useState('admins');

  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <h1>Admin Management</h1>
          <p>Manage admins, roles, permissions, and audit logs</p>
        </div>
      </div>

      <div className="admin-tabs">
        {[['admins', 'Admins'], ['roles', 'Roles'], ['audit', 'Audit Logs']].map(([key, label]) => (
          <button key={key} className={`admin-tab${activeTab === key ? ' active' : ''}`} onClick={() => setActiveTab(key)}>
            {label}
          </button>
        ))}
      </div>

      {activeTab === 'admins' && <AdminsTab />}
      {activeTab === 'roles' && <RolesTab />}
      {activeTab === 'audit' && <AuditLogsTab />}
    </div>
  );
}
