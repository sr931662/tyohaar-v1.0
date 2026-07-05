import axios from 'axios';

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
  return config;
});

// Single shared in-flight refresh so concurrent 401s only trigger one refresh call.
let refreshPromise = null;

function refreshAccessToken() {
  if (!refreshPromise) {
    const refreshToken = localStorage.getItem('admin_refresh_token') || sessionStorage.getItem('admin_refresh_token');
    if (!refreshToken) {
      refreshPromise = Promise.reject(new Error('No refresh token available.'));
    } else {
      refreshPromise = axios
        .post(`${BASE_URL}/auth/token/refresh`, { refresh_token: refreshToken })
        .then((res) => {
          const data = res.data?.data ?? res.data;
          const store = getStore();
          store.setItem('admin_token', data.access_token);
          if (data.refresh_token) store.setItem('admin_refresh_token', data.refresh_token);
          return data.access_token;
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

export function extractPaginated(res) {
  const raw = res.data;

  // Cursor-paginated: { data: [...], meta: { cursor, has_next, page_size } }
  if (Array.isArray(raw?.data) && raw?.meta !== undefined) {
    return {
      items: raw.data,
      total: raw.data.length,
      page: 1,
      per_page: raw.meta?.page_size ?? 20,
      pages: raw.meta?.has_next ? 2 : 1,
      next_cursor: raw.meta?.cursor ?? null,
      has_next: raw.meta?.has_next ?? false,
    };
  }

  // Offset-paginated (SuccessResponse-wrapped): { data: { items, total, pages, ... } }
  const d = raw?.data;
  return {
    items: d?.items ?? d?.data ?? [],
    total: d?.total ?? 0,
    page: d?.page ?? 1,
    per_page: d?.per_page ?? 20,
    pages: d?.pages ?? 1,
    next_cursor: d?.next_cursor ?? null,
  };
}
