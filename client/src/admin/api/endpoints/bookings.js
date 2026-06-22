import { apiClient, extractData, extractList, extractPaginated } from '../client';

export const bookingsApi = {
  list: (params) =>
    apiClient.get('/bookings', { params }).then(extractPaginated),

  get: (bookingId) =>
    apiClient.get(`/bookings/${bookingId}`).then(extractData),

  confirm: (bookingId) =>
    apiClient.post(`/bookings/${bookingId}/confirm`).then(extractData),

  start: (bookingId) =>
    apiClient.post(`/bookings/${bookingId}/start`).then(extractData),

  complete: (bookingId) =>
    apiClient.post(`/bookings/${bookingId}/complete`).then(extractData),

  assignVendor: (bookingId, itemId, vendorId) =>
    apiClient.post(`/bookings/${bookingId}/items/${itemId}/assignments/${vendorId}`).then(extractData),

  unassignVendor: (bookingId, assignmentId) =>
    apiClient.delete(`/bookings/${bookingId}/assignments/${assignmentId}`).then(extractData),

  requestCancellation: (bookingId, body) =>
    apiClient.post(`/bookings/${bookingId}/cancellation`, body).then(extractData),

  processCancellation: (bookingId, approved) =>
    apiClient.post(`/bookings/${bookingId}/cancellation/process`, null, { params: { approved } }).then(extractData),

  requestReschedule: (bookingId, body) =>
    apiClient.post(`/bookings/${bookingId}/reschedule`, body).then(extractData),

  processReschedule: (bookingId, rescheduleId, approved) =>
    apiClient.post(`/bookings/${bookingId}/reschedules/${rescheduleId}/process`, null, { params: { approved } }).then(extractData),

  history: (bookingId) =>
    apiClient.get(`/bookings/${bookingId}/history`).then(extractList),

  statusHistory: (bookingId) =>
    apiClient.get(`/bookings/${bookingId}/status-history`).then(extractList),

  getInvoice: (bookingId) =>
    apiClient.get(`/bookings/${bookingId}/invoice`).then(extractData),

  generateInvoice: (bookingId) =>
    apiClient.post(`/bookings/${bookingId}/invoice`).then(extractData),
};
