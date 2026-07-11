import { apiClient, extractData, extractList, extractPaginated } from '../client';

export const settingsApi = {
  // App settings
  listSettings: () =>
    apiClient.get('/common/settings').then(extractList),

  getSetting: (key) =>
    apiClient.get(`/common/settings/${key}`).then(extractData),

  upsertSetting: (body) =>
    apiClient.put('/common/settings', body).then(extractData),

  deleteSetting: (key) =>
    apiClient.delete(`/common/settings/${key}`).then(extractData),

  // Banners
  listAllBanners: () =>
    apiClient.get('/common/banners/admin/all').then(extractList),

  createBanner: (body) =>
    apiClient.post('/common/banners', body).then(extractData),

  updateBanner: (bannerId, body) =>
    apiClient.put(`/common/banners/${bannerId}`, body).then(extractData),

  deleteBanner: (bannerId) =>
    apiClient.delete(`/common/banners/${bannerId}`).then(extractData),

  toggleBanner: (bannerId) =>
    apiClient.patch(`/common/banners/${bannerId}/toggle`).then(extractData),

  // FAQs
  listFaqs: () =>
    apiClient.get('/common/faqs').then(extractList),

  createFaq: (body) =>
    apiClient.post('/common/faqs', body).then(extractData),

  updateFaq: (faqId, body) =>
    apiClient.put(`/common/faqs/${faqId}`, body).then(extractData),

  deleteFaq: (faqId) =>
    apiClient.delete(`/common/faqs/${faqId}`).then(extractData),

  reorderFaqs: (ids) =>
    apiClient.post('/common/faqs/reorder', { ids }).then(extractList),

  // States & Cities
  listStates: () =>
    apiClient.get('/common/states').then(extractList),

  createState: (body) =>
    apiClient.post('/common/states', body).then(extractData),

  updateState: (stateId, body) =>
    apiClient.put(`/common/states/${stateId}`, body).then(extractData),

  deleteState: (stateId) =>
    apiClient.delete(`/common/states/${stateId}`).then(extractData),

  listCities: (params) =>
    apiClient.get('/common/cities', { params }).then(extractList),

  createCity: (body) =>
    apiClient.post('/common/cities', body).then(extractData),

  updateCity: (cityId, body) =>
    apiClient.put(`/common/cities/${cityId}`, body).then(extractData),

  deleteCity: (cityId) =>
    apiClient.delete(`/common/cities/${cityId}`).then(extractData),

  // Convenience aliases used by SettingsPage
  getAppSettings: () =>
    apiClient.get('/common/settings').then(r => {
      const list = Array.isArray(r.data?.data) ? r.data.data : (r.data ?? []);
      return Object.fromEntries(list.map(s => [s.key, s.value]));
    }),

  updateAppSettings: (form) =>
    apiClient.put('/common/settings', form).then(extractData),

  listBanners: () =>
    apiClient.get('/common/banners/admin/all').then(extractList),

  listFAQs: () =>
    apiClient.get('/common/faqs').then(extractList),

  createFAQ: (body) =>
    apiClient.post('/common/faqs', body).then(extractData),

  updateFAQ: (faqId, body) =>
    apiClient.put(`/common/faqs/${faqId}`, body).then(extractData),

  deleteFAQ: (faqId) =>
    apiClient.delete(`/common/faqs/${faqId}`).then(extractData),

  // Terms & Privacy
  getCurrentTerms: () =>
    apiClient.get('/common/terms').then(extractData),

  listTermsVersions: (params) =>
    apiClient.get('/common/terms/versions', { params }).then(extractPaginated),

  createTermsVersion: (body) =>
    apiClient.post('/common/terms/versions', body).then(extractData),

  getCurrentPrivacy: () =>
    apiClient.get('/common/privacy-policy').then(extractData),

  createPrivacyVersion: (body) =>
    apiClient.post('/common/privacy-policy/versions', body).then(extractData),

  // Cancellation & Refund Policy
  getCurrentCancellationPolicy: () =>
    apiClient.get('/common/cancellation-policy').then(extractData),

  listCancellationPolicyVersions: (params) =>
    apiClient.get('/common/cancellation-policy/versions', { params }).then(extractPaginated),

  createCancellationPolicyVersion: (body) =>
    apiClient.post('/common/cancellation-policy/versions', body).then(extractData),
};
