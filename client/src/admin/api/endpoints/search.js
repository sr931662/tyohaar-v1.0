import { apiClient, extractData } from '../client';

export const searchApi = {
  globalSearch: (q, params) =>
    apiClient.get('/admin/cms/search/', { params: { q, ...params } }).then(extractData),
};
