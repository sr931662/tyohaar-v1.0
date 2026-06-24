import { vendorClient, extractData, extractList, extractPaginated } from './client';

// ── Auth (OTP-based) ──────────────────────────────────────────────────────────

export const vendorAuthApi = {
  loginWithPassword: (email, password) =>
    vendorClient.post('/auth/vendor/login', { email, password }).then(extractData),

  logout: () =>
    vendorClient.post('/auth/logout').then(extractData),

  me: () =>
    vendorClient.get('/users/me').then(extractData),
};

// ── Vendor Profile ────────────────────────────────────────────────────────────

export const vendorProfileApi = {
  create: (body) =>
    vendorClient.post('/vendors', body).then(extractData),

  getMe: () =>
    vendorClient.get('/vendors/me').then(extractData),

  get: (vendorId) =>
    vendorClient.get(`/vendors/${vendorId}`).then(extractData),

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
};

// ── Packages ──────────────────────────────────────────────────────────────────

export const vendorPackagesApi = {
  list: (params) =>
    vendorClient.get('/packages', { params }).then(extractPaginated),

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

  listCategories: () =>
    vendorClient.get('/packages/categories').then(extractList),

  addItem: (packageId, body) =>
    vendorClient.post(`/packages/${packageId}/items`, body).then(extractData),

  listItems: (packageId) =>
    vendorClient.get(`/packages/${packageId}/items`).then(extractList),
};
