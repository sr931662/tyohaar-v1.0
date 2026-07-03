import { apiClient, extractData } from '../client';

export const authApi = {
  login: (email, password) =>
    apiClient.post('/admin/auth/login', { email, password }).then(extractData),

  logout: () =>
    apiClient.post('/admin/auth/logout').then(extractData),

  me: () =>
    apiClient.get('/admin/auth/me').then(extractData),

  updateUserProfile: (userId, body) =>
    apiClient.put(`/users/${userId}/profile`, body).then(extractData),
};
