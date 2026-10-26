import { apiClient, extractData, extractList } from '../client';

export const colorsApi = {
  listAll: () => apiClient.get('/admin/balloon-colors').then(extractList),

  create: (body) => apiClient.post('/admin/balloon-colors', body).then(extractData),

  update: (id, body) => apiClient.patch(`/admin/balloon-colors/${id}`, body).then(extractData),

  remove: (id) => apiClient.delete(`/admin/balloon-colors/${id}`).then(extractData),

  // Sends the full desired order; the server renumbers everything.
  reorder: (ids) => apiClient.post('/admin/balloon-colors/reorder', { ids }).then(extractList),

  // Finishes (matte / pastel / chrome …) — managed alongside the colours.
  listFinishes: () => apiClient.get('/admin/balloon-finishes').then(extractList),
  createFinish: (body) => apiClient.post('/admin/balloon-finishes', body).then(extractData),
  updateFinish: (id, body) => apiClient.patch(`/admin/balloon-finishes/${id}`, body).then(extractData),
  removeFinish: (id) => apiClient.delete(`/admin/balloon-finishes/${id}`).then(extractData),
  reorderFinishes: (ids) => apiClient.post('/admin/balloon-finishes/reorder', { ids }).then(extractList),
};
