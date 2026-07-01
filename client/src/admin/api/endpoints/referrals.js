import { apiClient, extractData, extractList, extractPaginated } from '../client';

export const referralsApi = {
  stats: () =>
    apiClient.get('/referrals/admin/stats').then(extractData),

  list: (params) =>
    apiClient.get('/referrals/admin', { params }).then(extractPaginated),

  getReward: (rewardId) =>
    apiClient.get(`/referrals/rewards/${rewardId}`).then(extractData),

  activateReward: (rewardId) =>
    apiClient.post(`/referrals/rewards/${rewardId}/activate`).then(extractData),

  triggerReward: (data) =>
    apiClient.post('/referrals/admin/trigger-rewards', data).then(extractData),
};
