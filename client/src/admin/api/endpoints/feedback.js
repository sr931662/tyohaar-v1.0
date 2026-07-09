import { apiClient, extractData, extractPaginated } from '../client';

export const feedbackApi = {
  listAll: (params) =>
    apiClient.get('/feedback/admin/all', { params }).then(extractPaginated),

  get: (feedbackId) =>
    apiClient.get(`/feedback/admin/${feedbackId}`).then(extractData),

  markReviewed: (feedbackId) =>
    apiClient.post(`/feedback/admin/${feedbackId}/review`).then(extractData),
};
