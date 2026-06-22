import { apiClient, extractData, extractList, extractPaginated } from '../client';

const BASE = '/admin/cms/io';

export const ioApi = {
  getTemplate: (entityType) =>
    apiClient.get(`${BASE}/import/template`, { params: { entity_type: entityType }, responseType: 'blob' }),

  validateImport: (formData) =>
    apiClient.post(`${BASE}/import/validate`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(extractData),

  executeImport: (logId) =>
    apiClient.post(`${BASE}/import/execute`, { log_id: logId }).then(extractData),

  listImportLogs: (params) =>
    apiClient.get(`${BASE}/import/logs`, { params }).then(extractPaginated),

  getImportLog: (logId) =>
    apiClient.get(`${BASE}/import/logs/${logId}`).then(extractData),

  undoImport: (logId) =>
    apiClient.post(`${BASE}/import/logs/${logId}/undo`).then(extractData),

  triggerExport: (body) =>
    apiClient.post(`${BASE}/export`, body).then(extractData),

  listExportLogs: (params) =>
    apiClient.get(`${BASE}/export/logs`, { params }).then(extractPaginated),

  getExportLog: (logId) =>
    apiClient.get(`${BASE}/export/logs/${logId}`).then(extractData),
};
