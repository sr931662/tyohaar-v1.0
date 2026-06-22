import { apiClient, extractData, extractList, extractPaginated } from '../client';

export const vendorsApi = {
  list: (params) =>
    apiClient.get('/vendors', { params }).then(extractPaginated),

  get: (vendorId) =>
    apiClient.get(`/vendors/${vendorId}`).then(extractData),

  verify: (vendorId, body) =>
    apiClient.post(`/vendors/${vendorId}/verify`, body).then(extractData),

  updateCategories: (vendorId, categories) =>
    apiClient.put(`/vendors/${vendorId}/categories`, { categories }).then(extractData),

  updateProfile: (vendorId, body) =>
    apiClient.put(`/vendors/${vendorId}/profile`, body).then(extractData),

  // Documents
  listDocuments: (vendorId) =>
    apiClient.get(`/vendors/${vendorId}/documents`).then(extractList),

  addDocument: (vendorId, body) =>
    apiClient.post(`/vendors/${vendorId}/documents`, body).then(extractData),

  updateDocument: (vendorId, docId, body) =>
    apiClient.put(`/vendors/${vendorId}/documents/${docId}`, body).then(extractData),

  deleteDocument: (vendorId, docId) =>
    apiClient.delete(`/vendors/${vendorId}/documents/${docId}`).then(extractData),

  // Gallery
  listGallery: (vendorId) =>
    apiClient.get(`/vendors/${vendorId}/gallery`).then(extractList),

  addGalleryItem: (vendorId, body) =>
    apiClient.post(`/vendors/${vendorId}/gallery`, body).then(extractData),

  deleteGalleryItem: (vendorId, itemId) =>
    apiClient.delete(`/vendors/${vendorId}/gallery/${itemId}`).then(extractData),

  // Reviews
  listReviews: (vendorId, params) =>
    apiClient.get(`/vendors/${vendorId}/reviews`, { params }).then(extractPaginated),

  deleteReview: (vendorId, reviewId) =>
    apiClient.delete(`/vendors/${vendorId}/reviews/${reviewId}`).then(extractData),

  // CRM
  crmList: (params) =>
    apiClient.get('/admin/cms/crm/vendors', { params }).then(extractPaginated),

  crmProfile: (vendorId) =>
    apiClient.get(`/admin/cms/crm/vendors/${vendorId}`).then(extractData),
};
