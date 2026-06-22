import { apiClient, extractData, extractList, extractPaginated } from '../client';

export const packagesApi = {
  list: (params) =>
    apiClient.get('/packages', { params }).then(extractPaginated),

  get: (packageId) =>
    apiClient.get(`/packages/${packageId}`).then(extractData),

  create: (body) =>
    apiClient.post('/packages', body).then(extractData),

  update: (packageId, body) =>
    apiClient.put(`/packages/${packageId}`, body).then(extractData),

  delete: (packageId) =>
    apiClient.delete(`/packages/${packageId}`).then(extractData),

  publish: (packageId) =>
    apiClient.post(`/packages/${packageId}/publish`).then(extractData),

  unpublish: (packageId) =>
    apiClient.post(`/packages/${packageId}/unpublish`).then(extractData),

  // Categories
  listCategories: () =>
    apiClient.get('/packages/categories').then(extractList),

  createCategory: (body) =>
    apiClient.post('/packages/categories', body).then(extractData),

  updateCategory: (catId, body) =>
    apiClient.put(`/packages/categories/${catId}`, body).then(extractData),

  deleteCategory: (catId) =>
    apiClient.delete(`/packages/categories/${catId}`).then(extractData),

  // Items
  listItems: (packageId) =>
    apiClient.get(`/packages/${packageId}/items`).then(extractList),

  addItem: (packageId, body) =>
    apiClient.post(`/packages/${packageId}/items`, body).then(extractData),

  updateItem: (packageId, itemId, body) =>
    apiClient.put(`/packages/${packageId}/items/${itemId}`, body).then(extractData),

  deleteItem: (packageId, itemId) =>
    apiClient.delete(`/packages/${packageId}/items/${itemId}`).then(extractData),

  // Reviews
  listReviews: (packageId, params) =>
    apiClient.get(`/packages/${packageId}/reviews`, { params }).then(extractPaginated),

  deleteReview: (packageId, reviewId) =>
    apiClient.delete(`/packages/${packageId}/reviews/${reviewId}`).then(extractData),
};
