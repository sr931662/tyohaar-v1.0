import { apiClient, extractData, extractPaginated } from '../client';

export const discountsApi = {
  list: (params) =>
    apiClient.get('/payments/coupons/admin', { params }).then(extractPaginated),

  create: (body) =>
    apiClient.post('/payments/coupons', body).then(extractData),

  update: (couponId, body) =>
    apiClient.patch(`/payments/coupons/${couponId}`, body).then(extractData),

  duplicate: (couponId) =>
    apiClient.post(`/payments/coupons/${couponId}/duplicate`).then(extractData),

  archive: (couponId) =>
    apiClient.post(`/payments/coupons/${couponId}/archive`).then(extractData),

  deactivate: (couponId) =>
    apiClient.delete(`/payments/coupons/${couponId}`).then(extractData),
};
