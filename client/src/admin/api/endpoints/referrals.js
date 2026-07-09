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

  // Milestone rules — "for every N referrals, X% off the next M plans over ₹Y"
  listMilestoneRules: () =>
    apiClient.get('/referrals/milestones/rules').then(extractData),

  createMilestoneRule: (body) =>
    apiClient.post('/referrals/milestones/rules', body).then(extractData),

  updateMilestoneRule: (ruleId, body) =>
    apiClient.patch(`/referrals/milestones/rules/${ruleId}`, body).then(extractData),
};
