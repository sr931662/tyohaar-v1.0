import { apiClient, extractData } from '../client';

const BASE = '/admin/cms/bulk';

export const bulkApi = {
  approveVendors: (vendorIds) =>
    apiClient.post(`${BASE}/vendors/approve`, { ids: vendorIds }).then(extractData),

  rejectVendors: (vendorIds, reason) =>
    apiClient.post(`${BASE}/vendors/reject`, { ids: vendorIds, reason }).then(extractData),

  suspendVendors: (vendorIds, reason) =>
    apiClient.post(`${BASE}/vendors/suspend`, { ids: vendorIds, reason }).then(extractData),

  activateVendors: (vendorIds) =>
    apiClient.post(`${BASE}/vendors/activate`, { ids: vendorIds }).then(extractData),

  publishPackages: (packageIds) =>
    apiClient.post(`${BASE}/packages/publish`, { ids: packageIds }).then(extractData),

  unpublishPackages: (packageIds) =>
    apiClient.post(`${BASE}/packages/unpublish`, { ids: packageIds }).then(extractData),

  archivePackages: (packageIds) =>
    apiClient.post(`${BASE}/packages/archive`, { ids: packageIds }).then(extractData),

  bulkPriceUpdate: (body) =>
    apiClient.post(`${BASE}/packages/price`, body).then(extractData),

  sendNotifications: (body) =>
    apiClient.post(`${BASE}/notifications/send`, body).then(extractData),

  generateCoupons: (body) =>
    apiClient.post(`${BASE}/coupons/generate`, body).then(extractData),

  enableDiscounts: (ids) =>
    apiClient.post(`${BASE}/coupons/enable`, { ids }).then(extractData),

  disableDiscounts: (ids) =>
    apiClient.post(`${BASE}/coupons/disable`, { ids }).then(extractData),

  archiveDiscounts: (ids) =>
    apiClient.post(`${BASE}/coupons/archive`, { ids }).then(extractData),

  assignMemberships: (body) =>
    apiClient.post(`${BASE}/memberships/assign`, body).then(extractData),

  // ── Delete ──────────────────────────────────────────────────────────────
  deleteVendors: (ids, reason) =>
    apiClient.post(`${BASE}/vendors/delete`, { ids, reason }).then(extractData),

  deletePackageCategories: (ids) =>
    apiClient.post(`${BASE}/packages/categories/delete`, { ids }).then(extractData),

  deleteOccasions: (ids) =>
    apiClient.post(`${BASE}/occasions/delete`, { ids }).then(extractData),

  deleteOccasionThemes: (ids) =>
    apiClient.post(`${BASE}/occasions/themes/delete`, { ids }).then(extractData),

  deleteMediaImages: (ids) =>
    apiClient.post(`${BASE}/media/images/delete`, { ids }).then(extractData),

  deleteMediaVideos: (ids) =>
    apiClient.post(`${BASE}/media/videos/delete`, { ids }).then(extractData),

  deleteRoles: (ids) =>
    apiClient.post(`${BASE}/roles/delete`, { ids }).then(extractData),

  deactivateNotificationTemplates: (ids) =>
    apiClient.post(`${BASE}/notifications/templates/deactivate`, { ids }).then(extractData),

  deleteStates: (ids) =>
    apiClient.post(`${BASE}/states/delete`, { ids }).then(extractData),

  deleteCities: (ids) =>
    apiClient.post(`${BASE}/cities/delete`, { ids }).then(extractData),

  deleteFaqs: (ids) =>
    apiClient.post(`${BASE}/faqs/delete`, { ids }).then(extractData),

  deactivateMembershipPlans: (ids) =>
    apiClient.post(`${BASE}/memberships/plans/deactivate`, { ids }).then(extractData),
};
