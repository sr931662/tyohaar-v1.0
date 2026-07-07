import { apiClient, extractData, extractList, extractPaginated } from '../client';

export const supportApi = {
  listAll: (params) =>
    apiClient.get('/support/tickets/all', { params }).then(extractPaginated),

  get: (ticketId) =>
    apiClient.get(`/support/tickets/${ticketId}`).then(extractData),

  updateStatus: (ticketId, ticketStatus, resolutionSummary) =>
    apiClient.patch(`/support/tickets/${ticketId}/status`, {
      ticket_status: ticketStatus,
      resolution_summary: resolutionSummary || undefined,
    }).then(extractData),

  assign: (ticketId, assigneeId) =>
    apiClient.post(`/support/tickets/${ticketId}/assignments/${assigneeId}`).then(extractData),

  // Backend returns the full thread as a plain list (not cursor-paginated).
  listMessages: (ticketId) =>
    apiClient.get(`/support/tickets/${ticketId}/messages`).then(extractList),

  addMessage: (ticketId, body) =>
    apiClient.post(`/support/tickets/${ticketId}/messages`, body).then(extractData),

  listAttachments: (ticketId) =>
    apiClient.get(`/support/tickets/${ticketId}/attachments`).then(extractList),
};
