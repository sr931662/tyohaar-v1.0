import { apiClient, extractData, extractList, extractPaginated } from '../client';

export const notificationsApi = {
  // Templates
  listTemplates: () =>
    apiClient.get('/notifications/templates').then(extractList),

  getTemplate: (templateId) =>
    apiClient.get(`/notifications/templates/${templateId}`).then(extractData),

  createTemplate: (body) =>
    apiClient.post('/notifications/templates', body).then(extractData),

  updateTemplate: (templateId, body) =>
    apiClient.put(`/notifications/templates/${templateId}`, body).then(extractData),

  deleteTemplate: (templateId) =>
    apiClient.delete(`/notifications/templates/${templateId}`).then(extractData),

  // Send
  send: (body) =>
    apiClient.post('/notifications/send', body).then(extractData),

  sendFromTemplate: (body) =>
    apiClient.post('/notifications/template/send', body).then(extractData),

  broadcast: (body) =>
    apiClient.post('/notifications/broadcast', body).then(extractData),

  // List (admin context — uses /notifications for logged-in user)
  list: (params) =>
    apiClient.get('/notifications', { params }).then(extractPaginated),

  unreadCount: () =>
    apiClient.get('/notifications/unread-count').then(extractData),

  markAllRead: () =>
    apiClient.post('/notifications/mark-all-read').then(extractData),
};
