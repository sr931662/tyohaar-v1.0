import { apiClient, extractData, extractList, extractPaginated } from '../client';

export const supportApi = {
  listAll: (params) =>
    apiClient.get('/support/tickets/all', { params }).then(extractPaginated),

  get: (ticketId) =>
    apiClient.get(`/support/tickets/${ticketId}`).then(extractData),

  updateStatus: (ticketId, status) =>
    apiClient.patch(`/support/tickets/${ticketId}/status`, { status }).then(extractData),

  assign: (ticketId, assigneeId) =>
    apiClient.post(`/support/tickets/${ticketId}/assignments/${assigneeId}`).then(extractData),

  listMessages: (ticketId, params) =>
    apiClient.get(`/support/tickets/${ticketId}/messages`, { params }).then(extractPaginated),

  addMessage: (ticketId, body) =>
    apiClient.post(`/support/tickets/${ticketId}/messages`, body).then(extractData),

  listAttachments: (ticketId) =>
    apiClient.get(`/support/tickets/${ticketId}/attachments`).then(extractList),
};
