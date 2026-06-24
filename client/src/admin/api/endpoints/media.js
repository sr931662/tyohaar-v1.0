import { apiClient, extractData } from '../client';

export const mediaApi = {
  listPendingModeration: (params) =>
    apiClient.get('/media/images/pending-moderation', { params }).then(extractData),

  moderateImage: (imageId, approved) =>
    apiClient.post(`/media/images/${imageId}/moderate`, null, { params: { approved } }).then(extractData),

  listImagesForEntity: (entityId, entityType) =>
    apiClient.get(`/media/images/entity/${entityId}`, { params: { entity_type: entityType } }).then(extractData),

  deleteImage: (imageId) =>
    apiClient.delete(`/media/images/${imageId}`).then(extractData),
};
