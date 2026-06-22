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

export const walletsApi = {
  get: () =>
    apiClient.get('/wallets/me').then(extractData),

  getById: (walletId) =>
    apiClient.get(`/wallets/${walletId}`).then(extractData),

  credit: (userId, params) =>
    apiClient.post(`/wallets/admin/credit/${userId}`, null, { params }).then(extractData),

  debit: (userId, params) =>
    apiClient.post(`/wallets/admin/debit/${userId}`, null, { params }).then(extractData),

  freeze: (walletId, reason) =>
    apiClient.post(`/wallets/${walletId}/freeze`, null, { params: { reason } }).then(extractData),

  unfreeze: (walletId) =>
    apiClient.post(`/wallets/${walletId}/unfreeze`).then(extractData),

  close: (walletId) =>
    apiClient.post(`/wallets/${walletId}/close`).then(extractData),

  listTransactions: (params) =>
    apiClient.get('/wallets/me/transactions', { params }).then(extractPaginated),

  awardReward: (userId, body) =>
    apiClient.post(`/wallets/admin/rewards/${userId}`, body).then(extractData),

  listRewards: (params) =>
    apiClient.get('/wallets/me/rewards', { params }).then(extractPaginated),

  activateReward: (rewardId) =>
    apiClient.post(`/wallets/rewards/${rewardId}/activate`).then(extractData),
};
