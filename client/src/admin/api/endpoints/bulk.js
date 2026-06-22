import { apiClient, extractData } from '../client';

const BASE = '/admin/cms/bulk';

export const bulkApi = {
  approveVendors: (vendorIds) =>
    apiClient.post(`${BASE}/vendors/approve`, { vendor_ids: vendorIds }).then(extractData),

  rejectVendors: (vendorIds, reason) =>
    apiClient.post(`${BASE}/vendors/reject`, { vendor_ids: vendorIds, reason }).then(extractData),

  suspendVendors: (vendorIds, reason) =>
    apiClient.post(`${BASE}/vendors/suspend`, { vendor_ids: vendorIds, reason }).then(extractData),

  activateVendors: (vendorIds) =>
    apiClient.post(`${BASE}/vendors/activate`, { vendor_ids: vendorIds }).then(extractData),

  publishPackages: (packageIds) =>
    apiClient.post(`${BASE}/packages/publish`, { package_ids: packageIds }).then(extractData),

  unpublishPackages: (packageIds) =>
    apiClient.post(`${BASE}/packages/unpublish`, { package_ids: packageIds }).then(extractData),

  archivePackages: (packageIds) =>
    apiClient.post(`${BASE}/packages/archive`, { package_ids: packageIds }).then(extractData),

  bulkPriceUpdate: (body) =>
    apiClient.post(`${BASE}/packages/price`, body).then(extractData),

  sendNotifications: (body) =>
    apiClient.post(`${BASE}/notifications/send`, body).then(extractData),

  generateCoupons: (body) =>
    apiClient.post(`${BASE}/coupons/generate`, body).then(extractData),

  assignMemberships: (body) =>
    apiClient.post(`${BASE}/memberships/assign`, body).then(extractData),
};
