import axios from 'axios';
import { extractPaginated, preparePagination } from './pagination';

const BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

export const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

function getStore() {
  return localStorage.getItem('admin_token') ? localStorage : sessionStorage;
}

function clearSession() {
  localStorage.removeItem('admin_token');
  localStorage.removeItem('admin_refresh_token');
  localStorage.removeItem('admin_user');
  sessionStorage.removeItem('admin_token');
  sessionStorage.removeItem('admin_refresh_token');
  sessionStorage.removeItem('admin_user');
}

// Attach admin token to every request
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('admin_token') || sessionStorage.getItem('admin_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  // The instance default 'Content-Type: application/json' would otherwise
  // stick on FormData requests and stop the browser from setting the
  // multipart boundary, so the server sees an unparseable body (missing
  // `file`/`usage` fields → 422). Let the browser set it instead.
  if (config.data instanceof FormData) delete config.headers['Content-Type'];
  return preparePagination(config);
});

// Single shared in-flight refresh so concurrent 401s only trigger one refresh call.
let refreshPromise = null;

function refreshAccessToken() {
  if (!refreshPromise) {
    const attemptedToken = localStorage.getItem('admin_refresh_token') || sessionStorage.getItem('admin_refresh_token');
    if (!attemptedToken) {
      refreshPromise = Promise.reject(new Error('No refresh token available.'));
    } else {
      refreshPromise = axios
        .post(`${BASE_URL}/auth/token/refresh`, { refresh_token: attemptedToken })
        .then((res) => {
          const data = res.data?.data ?? res.data;
          const store = getStore();
          store.setItem('admin_token', data.access_token);
          if (data.refresh_token) store.setItem('admin_refresh_token', data.refresh_token);
          return data.access_token;
        })
        .catch((err) => {
          // Two tabs sharing one login can both race to refresh the same
          // (about-to-expire) token. If another tab already won that race,
          // storage now holds a newer token than the one we just tried —
          // use it instead of forcing a logout for what is really a no-op.
          const currentToken = localStorage.getItem('admin_refresh_token') || sessionStorage.getItem('admin_refresh_token');
          if (currentToken && currentToken !== attemptedToken) {
            const currentAccess = localStorage.getItem('admin_token') || sessionStorage.getItem('admin_token');
            if (currentAccess) return currentAccess;
          }
          throw err;
        });
    }
    refreshPromise.finally(() => { refreshPromise = null; });
  }
  return refreshPromise;
}

// Normalize API responses — backend always wraps in { data, success, message }
apiClient.interceptors.response.use(
  (res) => res,
  async (error) => {
    const { config, response } = error;
    if (response?.status === 401 && config && !config._retried && !config.url?.includes('/auth/')) {
      config._retried = true;
      try {
        const newToken = await refreshAccessToken();
        config.headers.Authorization = `Bearer ${newToken}`;
        return apiClient(config);
      } catch {
        clearSession();
        window.location.href = '/workspace/login';
        return Promise.reject(error);
      }
    }
    if (response?.status === 401) {
      clearSession();
      window.location.href = '/workspace/login';
    }
    return Promise.reject(error);
  }
);

export function extractData(res) {
  return res.data?.data ?? res.data;
}

export function extractList(res) {
  const d = res.data?.data;
  if (Array.isArray(d)) return d;
  if (d?.items) return d.items;
  if (d?.data) return d.data;
  return [];
}

export { extractPaginated };
