import { apiClient, extractData, extractList, extractPaginated } from '../client';

export const occasionsApi = {
  // Occasions
  list: (params) =>
    apiClient.get('/occasions', { params }).then(extractPaginated),

  get: (occasionId) =>
    apiClient.get(`/occasions/${occasionId}`).then(extractData),

  create: (body) =>
    apiClient.post('/occasions', body).then(extractData),

  update: (occasionId, body) =>
    apiClient.put(`/occasions/${occasionId}`, body).then(extractData),

  delete: (occasionId) =>
    apiClient.delete(`/occasions/${occasionId}`).then(extractData),

  // Reference data
  listCategories: () =>
    apiClient.get('/occasions/categories').then(extractList),

  createCategory: (body) =>
    apiClient.post('/occasions/categories', body).then(extractData),

  listMoods: () =>
    apiClient.get('/occasions/moods').then(extractList),

  createMood: (body) =>
    apiClient.post('/occasions/moods', body).then(extractData),

  listTags: () =>
    apiClient.get('/occasions/tags').then(extractList),

  createTag: (body) =>
    apiClient.post('/occasions/tags', body).then(extractData),

  listThemes: () =>
    apiClient.get('/occasions/themes').then(extractList),

  createTheme: (body) =>
    apiClient.post('/occasions/themes', body).then(extractData),
};
