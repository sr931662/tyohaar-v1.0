import { apiClient, extractData, extractList, extractPaginated } from '../client';

export const paymentsApi = {
  list: (params) =>
    apiClient.get('/payments', { params }).then(extractPaginated),

  get: (paymentId) =>
    apiClient.get(`/payments/${paymentId}`).then(extractData),

  getTransactions: (paymentId) =>
    apiClient.get(`/payments/${paymentId}/transactions`).then(extractList),

  initiateRefund: (paymentId, body) =>
    apiClient.post(`/payments/${paymentId}/refunds`, body).then(extractData),

  listRefunds: (bookingId) =>
    apiClient.get(`/payments/bookings/${bookingId}/refunds`).then(extractList),

  createSplit: (paymentId, body) =>
    apiClient.post(`/payments/${paymentId}/splits`, body).then(extractData),

  listSplits: (paymentId) =>
    apiClient.get(`/payments/${paymentId}/splits`).then(extractList),

  // Coupons
  listCoupons: () =>
    apiClient.get('/payments/coupons').then(extractList),

  createCoupon: (body) =>
    apiClient.post('/payments/coupons', body).then(extractData),

  deactivateCoupon: (couponId) =>
    apiClient.delete(`/payments/coupons/${couponId}`).then(extractData),

  validateCoupon: (params) =>
    apiClient.get('/payments/coupons/validate', { params }).then(extractData),

  // Invoices
  listInvoices: (params) =>
    apiClient.get('/payments/invoices', { params }).then(extractList),

  getInvoice: (invoiceId) =>
    apiClient.get(`/payments/invoices/${invoiceId}`).then(extractData),
};
