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
};
