import { apiClient, extractData, extractList, extractPaginated } from '../client';

const BASE = '/admin/cms/io';

export const ioApi = {
  getTemplate: (entityType) =>
    apiClient.get(`${BASE}/import/template`, { params: { entity_type: entityType }, responseType: 'blob' }),

  validateImport: (formData) =>
    apiClient.post(`${BASE}/import/validate`, formData).then(extractData),

  // Backend re-parses the file at execute time (it doesn't persist the
  // upload from /validate), so the same file must be resent here alongside
  // the log_id from that validation call.
  executeImport: (formData) =>
    apiClient.post(`${BASE}/import/execute`, formData).then(extractData),

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
