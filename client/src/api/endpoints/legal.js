import { publicClient, extractData } from '../publicClient.js';

// Public legal-document endpoints — mirror the admin's read-current calls in
// `client/src/admin/api/endpoints/settings.js`, minus auth. All three are
// documented as public on the backend (see server/app/routes/common/routes.py).
export function getCurrentTerms() {
  return publicClient.get('/common/terms').then(extractData);
}

export function getCurrentPrivacy() {
  return publicClient.get('/common/privacy-policy').then(extractData);
}

export function getCurrentCancellationPolicy() {
  return publicClient.get('/common/cancellation-policy').then(extractData);
}
