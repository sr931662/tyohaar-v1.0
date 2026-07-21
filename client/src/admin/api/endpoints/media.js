import { apiClient, extractData } from '../client';

export const mediaApi = {
  uploadImage: (file, usage, { entityType, entityId } = {}) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('usage', usage);
    if (entityType) formData.append('entity_type', entityType);
    if (entityId) formData.append('entity_id', entityId);
    return apiClient.post('/media/upload', formData).then(extractData);
  },

  listPendingModeration: (params) =>
    apiClient.get('/media/images/pending-moderation', { params }).then(extractData),

  moderateImage: (imageId, approved) =>
    apiClient.post(`/media/images/${imageId}/moderate`, null, { params: { approved } }).then(extractData),

  listImagesForEntity: (entityId, entityType) =>
    apiClient.get(`/media/images/entity/${entityId}`, { params: { entity_type: entityType } }).then(extractData),

  deleteImage: (imageId) =>
    apiClient.delete(`/media/images/${imageId}`).then(extractData),

  listVideosForEntity: (entityId, entityType) =>
    apiClient.get(`/media/videos/entity/${entityId}`, { params: { entity_type: entityType } }).then(extractData),

  deleteVideo: (videoId) =>
    apiClient.delete(`/media/videos/${videoId}`).then(extractData),
};
