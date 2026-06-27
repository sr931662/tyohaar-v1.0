import { apiClient, extractData, extractList } from '../client';

export const budgetsApi = {
  listCategories: () =>
    apiClient.get('/budgets/categories').then(extractList),

  createCategory: (body) =>
    apiClient.post('/budgets/categories', body).then(extractData),

  updateCategory: (categoryId, body) =>
    apiClient.put(`/budgets/categories/${categoryId}`, body).then(extractData),

  deleteCategory: (categoryId) =>
    apiClient.delete(`/budgets/categories/${categoryId}`).then(extractData),
};
