import { vendorClient, extractData, extractList, extractPaginated } from './client';

// ── Auth ──────────────────────────────────────────────────────────────────────

export const vendorAuthApi = {
  loginWithPassword: (email, password) =>
    vendorClient.post('/auth/vendor/login', { email, password }).then(extractData),
  register: (body) =>
    vendorClient.post('/auth/vendor/register', body).then(extractData),
  loginWithGoogle: (idToken) =>
    vendorClient.post('/auth/vendor/google', { id_token: idToken }).then(extractData),
  requestPasswordResetOtp: (email) =>
    vendorClient.post('/auth/otp/request', { identifier: email, channel: 'email', purpose: 'password_reset' }).then(extractData),
  resetPassword: (email, otpCode, newPassword) =>
    vendorClient.post('/auth/password/reset', { email, otp_code: otpCode, new_password: newPassword }).then(extractData),
  logout: () =>
    vendorClient.post('/auth/logout').then(extractData),
  me: () =>
    vendorClient.get('/users/me').then(extractData),
  getUserProfile: (userId) =>
    vendorClient.get(`/users/${userId}`).then(extractData),
  updateUserProfile: (userId, body) =>
    vendorClient.put(`/users/${userId}/profile`, body).then(extractData),
};

// ── Media ─────────────────────────────────────────────────────────────────────

export const vendorMediaApi = {
  uploadImage: (file, usage, { entityType, entityId } = {}) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('usage', usage);
    if (entityType) formData.append('entity_type', entityType);
    if (entityId) formData.append('entity_id', entityId);
    return vendorClient.post('/media/upload', formData).then(extractData);
  },
};

// ── Vendor Profile ────────────────────────────────────────────────────────────

export const vendorProfileApi = {
  create: (body) =>
    vendorClient.post('/vendors', body).then(extractData),
  getMe: () =>
    vendorClient.get('/vendors/me').then(extractData),
  get: (vendorId) =>
    vendorClient.get(`/vendors/${vendorId}`).then(extractData),
  update: (vendorId, body) =>
    vendorClient.put(`/vendors/${vendorId}`, body).then(extractData),
  updateProfile: (vendorId, body) =>
    vendorClient.put(`/vendors/${vendorId}/profile`, body).then(extractData),

  // Gallery
  listGallery: (vendorId) =>
    vendorClient.get(`/vendors/${vendorId}/gallery`).then(extractList),
  addGalleryItem: (vendorId, body) =>
    vendorClient.post(`/vendors/${vendorId}/gallery`, body).then(extractData),
  deleteGalleryItem: (vendorId, itemId) =>
    vendorClient.delete(`/vendors/${vendorId}/gallery/${itemId}`).then(extractData),

  // Documents
  listDocuments: (vendorId) =>
    vendorClient.get(`/vendors/${vendorId}/documents`).then(extractList),
  addDocument: (vendorId, body) =>
    vendorClient.post(`/vendors/${vendorId}/documents`, body).then(extractData),
  deleteDocument: (vendorId, docId) =>
    vendorClient.delete(`/vendors/${vendorId}/documents/${docId}`).then(extractData),

  // Bank accounts
  listBankAccounts: (vendorId) =>
    vendorClient.get(`/vendors/${vendorId}/bank-accounts`).then(extractList),
  addBankAccount: (vendorId, body) =>
    vendorClient.post(`/vendors/${vendorId}/bank-accounts`, body).then(extractData),
  updateBankAccount: (vendorId, bankId, body) =>
    vendorClient.put(`/vendors/${vendorId}/bank-accounts/${bankId}`, body).then(extractData),
  deleteBankAccount: (vendorId, bankId) =>
    vendorClient.delete(`/vendors/${vendorId}/bank-accounts/${bankId}`).then(extractData),

  // Availability
  listAvailability: (vendorId, params) =>
    vendorClient.get(`/vendors/${vendorId}/availability`, { params }).then(extractList),
  createAvailability: (vendorId, body) =>
    vendorClient.post(`/vendors/${vendorId}/availability`, body).then(extractData),
  updateAvailability: (vendorId, slotId, body) =>
    vendorClient.put(`/vendors/${vendorId}/availability/${slotId}`, body).then(extractData),
  deleteAvailability: (vendorId, slotId) =>
    vendorClient.delete(`/vendors/${vendorId}/availability/${slotId}`).then(extractData),

  // Reviews (for my vendor)
  listReviews: (vendorId, params) =>
    vendorClient.get(`/vendors/${vendorId}/reviews`, { params }).then(extractPaginated),
};

// ── Packages ──────────────────────────────────────────────────────────────────

export const vendorPackagesApi = {
  list: (params) =>
    vendorClient.get('/packages/vendor/mine', { params }).then(extractPaginated),
  get: (packageId) =>
    vendorClient.get(`/packages/${packageId}`).then(extractData),
  create: (body) =>
    vendorClient.post('/packages', body).then(extractData),
  update: (packageId, body) =>
    vendorClient.put(`/packages/${packageId}`, body).then(extractData),
  delete: (packageId) =>
    vendorClient.delete(`/packages/${packageId}`).then(extractData),
  submitForReview: (packageId) =>
    vendorClient.post(`/packages/${packageId}/publish`).then(extractData),
  unpublish: (packageId) =>
    vendorClient.post(`/packages/${packageId}/unpublish`).then(extractData),

  // Categories
  listCategories: () =>
    vendorClient.get('/packages/categories').then(extractList),

  // Items
  listItems: (packageId) =>
    vendorClient.get(`/packages/${packageId}/items`).then(extractList),
  addItem: (packageId, body) =>
    vendorClient.post(`/packages/${packageId}/items`, body).then(extractData),
  updateItem: (packageId, itemId, body) =>
    vendorClient.put(`/packages/${packageId}/items/${itemId}`, body).then(extractData),
  deleteItem: (packageId, itemId) =>
    vendorClient.delete(`/packages/${packageId}/items/${itemId}`).then(extractData),
};

// ── Occasions (reference data for package linking) ─────────────────────────────

export const vendorOccasionsApi = {
  list: (params) =>
    vendorClient.get('/occasions', { params: { per_page: 100, ...params } }).then(extractPaginated),
};

// ── Bookings ──────────────────────────────────────────────────────────────────

export const vendorBookingsApi = {
  list: ({ page, per_page, ...rest } = {}) =>
    vendorClient.get('/bookings/vendor', { params: { page_size: per_page, ...rest } }).then(extractPaginated),
  get: (bookingId) =>
    vendorClient.get(`/bookings/${bookingId}`).then(extractData),
  start: (bookingId) =>
    vendorClient.post(`/bookings/${bookingId}/start`).then(extractData),
  complete: (bookingId) =>
    vendorClient.post(`/bookings/${bookingId}/complete`).then(extractData),
  history: (bookingId) =>
    vendorClient.get(`/bookings/${bookingId}/history`).then(extractList),
  statusHistory: (bookingId) =>
    vendorClient.get(`/bookings/${bookingId}/status-history`).then(extractList),
};

// ── Wallet / Earnings ─────────────────────────────────────────────────────────

export const vendorWalletApi = {
  get: () =>
    vendorClient.get('/wallets/me').then(extractData),
  listTransactions: ({ page, per_page, ...rest } = {}) =>
    vendorClient.get('/wallets/me/transactions', { params: { page_size: per_page, ...rest } }).then(extractPaginated),
  getRewardBalance: () =>
    vendorClient.get('/wallets/me/rewards/balance').then(extractData),
};

// ── Notifications ─────────────────────────────────────────────────────────────

export const vendorNotificationsApi = {
  list: (params) =>
    vendorClient.get('/notifications', { params }).then(extractPaginated),
  unreadCount: () =>
    vendorClient.get('/notifications/unread-count').then(extractData),
  markRead: (notificationId) =>
    vendorClient.patch(`/notifications/${notificationId}/read`).then(extractData),
  markAllRead: () =>
    vendorClient.post('/notifications/mark-all-read').then(extractData),
  remove: (notificationId) =>
    vendorClient.delete(`/notifications/${notificationId}`).then(extractData),
};

// ── Support ───────────────────────────────────────────────────────────────────

export const vendorSupportApi = {
  list: (params) =>
    vendorClient.get('/support/tickets', { params }).then(extractPaginated),
  get: (ticketId) =>
    vendorClient.get(`/support/tickets/${ticketId}`).then(extractData),
  create: (body) =>
    vendorClient.post('/support/tickets', body).then(extractData),
  // Backend returns the full thread as a plain list (not cursor-paginated —
  // a ticket's message count is naturally bounded), so this uses extractList
  // rather than extractPaginated.
  listMessages: (ticketId) =>
    vendorClient.get(`/support/tickets/${ticketId}/messages`).then(extractList),
  addMessage: (ticketId, body) =>
    vendorClient.post(`/support/tickets/${ticketId}/messages`, body).then(extractData),
};
