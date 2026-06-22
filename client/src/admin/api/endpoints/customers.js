import { apiClient, extractData, extractPaginated } from '../client';

export const customersApi = {
  crmList: (params) =>
    apiClient.get('/admin/cms/crm/customers', { params }).then(extractPaginated),

  crmProfile: (userId) =>
    apiClient.get(`/admin/cms/crm/customers/${userId}`).then(extractData),

  getFull: (userId) =>
    apiClient.get(`/users/${userId}/full`).then(extractData),

  getProfile: (userId) =>
    apiClient.get(`/users/${userId}`).then(extractData),
};
