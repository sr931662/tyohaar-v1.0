import { apiClient, extractData, extractList, extractPaginated } from '../client';

export const membershipsApi = {
  // Plans
  listPlans: () =>
    apiClient.get('/memberships/plans').then(extractList),

  getPlan: (planId) =>
    apiClient.get(`/memberships/plans/${planId}`).then(extractData),

  createPlan: (body) =>
    apiClient.post('/memberships/plans', body).then(extractData),

  updatePlan: (planId, body) =>
    apiClient.put(`/memberships/plans/${planId}`, body).then(extractData),

  deactivatePlan: (planId) =>
    apiClient.delete(`/memberships/plans/${planId}`).then(extractData),

  // All memberships (admin)
  listAll: (params) =>
    apiClient.get('/memberships/admin/all', { params }).then(extractPaginated),

  forceExpire: (membershipId) =>
    apiClient.post(`/memberships/admin/${membershipId}/expire`).then(extractData),

  get: (membershipId) =>
    apiClient.get(`/memberships/${membershipId}`).then(extractData),
};
