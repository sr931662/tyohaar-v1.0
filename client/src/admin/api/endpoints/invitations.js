import { apiClient, extractData, extractPaginated } from '../client';

const BASE = '/admin/invitations';

export const invitationsApi = {
  list: (params) => apiClient.get(BASE, { params }).then(extractPaginated),

  get: (guestId) => apiClient.get(`${BASE}/${guestId}`).then(extractData),

  revoke: (guestId, reason) =>
    apiClient.post(`${BASE}/${guestId}/revoke`, { reason: reason || null }).then(extractData),

  entryLogs: (params) => apiClient.get(`${BASE}/entry-logs`, { params }).then(extractPaginated),

  celebrationSummary: (celebrationId) =>
    apiClient.get(`${BASE}/celebrations/${celebrationId}/summary`).then(extractData),

  getPolicy: () => apiClient.get(`${BASE}/policy`).then(extractData),

  updatePolicy: (body) => apiClient.put(`${BASE}/policy`, body).then(extractData),

  exportCsv: (params) =>
    apiClient.get(`${BASE}/export.csv`, { params, responseType: 'blob' }).then((res) => res.data),
};
