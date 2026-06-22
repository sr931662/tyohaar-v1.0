import { apiClient, extractData, extractList, extractPaginated } from '../client';

export const adminMgmtApi = {
  // Admins
  listAdmins: (params) =>
    apiClient.get('/admin/admins', { params }).then(extractPaginated),

  getAdmin: (adminId) =>
    apiClient.get(`/admin/admins/${adminId}`).then(extractData),

  createAdmin: (body) =>
    apiClient.post('/admin/admins', body).then(extractData),

  updateAdmin: (adminId, body) =>
    apiClient.put(`/admin/admins/${adminId}`, body).then(extractData),

  deactivateAdmin: (adminId) =>
    apiClient.post(`/admin/admins/${adminId}/deactivate`).then(extractData),

  unlockAdmin: (adminId) =>
    apiClient.post(`/admin/admins/${adminId}/unlock`).then(extractData),

  changePassword: (adminId, body) =>
    apiClient.post(`/admin/admins/${adminId}/change-password`, body).then(extractData),

  getAdminPermissions: (adminId) =>
    apiClient.get(`/admin/admins/${adminId}/permissions`).then(extractList),

  // Roles
  listRoles: () =>
    apiClient.get('/admin/roles').then(extractList),

  getRole: (roleId) =>
    apiClient.get(`/admin/roles/${roleId}`).then(extractData),

  createRole: (body) =>
    apiClient.post('/admin/roles', body).then(extractData),

  updateRole: (roleId, body) =>
    apiClient.put(`/admin/roles/${roleId}`, body).then(extractData),

  deleteRole: (roleId) =>
    apiClient.delete(`/admin/roles/${roleId}`).then(extractData),

  assignRole: (body) =>
    apiClient.post('/admin/roles/assign', body).then(extractData),

  // Permissions
  listPermissions: () =>
    apiClient.get('/admin/permissions').then(extractList),

  createPermission: (body) =>
    apiClient.post('/admin/permissions', body).then(extractData),

  assignPermissionToRole: (body) =>
    apiClient.post('/admin/permissions/assign-to-role', body).then(extractData),

  revokePermissionFromRole: (roleId, permissionId) =>
    apiClient.delete(`/admin/roles/${roleId}/permissions/${permissionId}`).then(extractData),

  // Audit logs
  listAuditLogs: (params) =>
    apiClient.get('/admin/audit-logs', { params }).then(extractPaginated),

  getEntityAuditLogs: (entityId, params) =>
    apiClient.get(`/admin/audit-logs/entity/${entityId}`, { params }).then(extractPaginated),
};
