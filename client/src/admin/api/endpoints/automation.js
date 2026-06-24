import { apiClient, extractData, extractList } from '../client';

const BASE = '/admin/cms/automation';

export const automationApi = {
  listRules: (params) =>
    apiClient.get(`${BASE}/rules`, { params }).then(extractList),

  getRule: (ruleId) =>
    apiClient.get(`${BASE}/rules/${ruleId}`).then(extractData),

  createRule: (body) =>
    apiClient.post(`${BASE}/rules`, body).then(extractData),

  updateRule: (ruleId, body) =>
    apiClient.patch(`${BASE}/rules/${ruleId}`, body).then(extractData),

  deleteRule: (ruleId) =>
    apiClient.delete(`${BASE}/rules/${ruleId}`).then(extractData),

  toggleRule: (ruleId) =>
    apiClient.post(`${BASE}/rules/${ruleId}/toggle`).then(extractData),

  manualTrigger: (ruleId, payload) =>
    apiClient.post(`${BASE}/rules/${ruleId}/trigger`, payload).then(extractData),

  listLogs: (params) =>
    apiClient.get(`${BASE}/logs`, { params }).then(extractList),

  getLog: (logId) =>
    apiClient.get(`${BASE}/logs/${logId}`).then(extractData),
};
