import { apiClient, extractData, extractList } from '../client';

const BASE = '/admin/cms/analytics';

export const analyticsApi = {
  dashboard: (params) =>
    apiClient.get(`${BASE}/dashboard`, { params }).then(extractData),

  revenue: (params) =>
    apiClient.get(`${BASE}/revenue`, { params }).then(extractData),

  bookings: (params) =>
    apiClient.get(`${BASE}/bookings`, { params }).then(extractData),

  users: (params) =>
    apiClient.get(`${BASE}/users`, { params }).then(extractData),

  vendors: (params) =>
    apiClient.get(`${BASE}/vendors`, { params }).then(extractData),

  payments: (params) =>
    apiClient.get(`${BASE}/payments`, { params }).then(extractData),

  wallets: (params) =>
    apiClient.get(`${BASE}/wallets`, { params }).then(extractData),

  support: (params) =>
    apiClient.get(`${BASE}/support`, { params }).then(extractData),

  platformHealth: () =>
    apiClient.get(`${BASE}/platform-health`).then(extractData),

  geographic: (params) =>
    apiClient.get(`${BASE}/geographic`, { params }).then(extractData),

  pendingActions: () =>
    apiClient.get(`${BASE}/pending-actions`).then(extractData),

  revenueChart: (params) =>
    apiClient.get(`${BASE}/charts/revenue`, { params }).then(extractData),

  bookingsChart: (params) =>
    apiClient.get(`${BASE}/charts/bookings`, { params }).then(extractData),

  usersChart: (params) =>
    apiClient.get(`${BASE}/charts/users`, { params }).then(extractData),

  categoryDistribution: (params) =>
    apiClient.get(`${BASE}/charts/categories`, { params }).then(extractData),

  activityFeed: (params) =>
    apiClient.get(`${BASE}/activity-feed`, { params }).then(extractData),

  widgets: () =>
    apiClient.get(`${BASE}/widgets`).then(extractData),
};
