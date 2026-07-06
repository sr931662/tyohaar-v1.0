import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

export const vendorClient = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

function getStore() {
  return localStorage.getItem('vendor_token') ? localStorage : sessionStorage;
}

function clearSession() {
  localStorage.removeItem('vendor_token');
  localStorage.removeItem('vendor_refresh_token');
  localStorage.removeItem('vendor_user');
  sessionStorage.removeItem('vendor_token');
  sessionStorage.removeItem('vendor_refresh_token');
  sessionStorage.removeItem('vendor_user');
}

vendorClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('vendor_token') || sessionStorage.getItem('vendor_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  // The instance default 'Content-Type: application/json' would otherwise
  // stick on FormData requests and stop the browser from setting the
  // multipart boundary, so the server sees an unparseable body (missing
  // `file`/`usage` fields → 422). Let the browser set it instead.
  if (config.data instanceof FormData) delete config.headers['Content-Type'];
  return config;
});

// Single shared in-flight refresh so concurrent 401s only trigger one refresh call.
let refreshPromise = null;

function refreshAccessToken() {
  if (!refreshPromise) {
    const attemptedToken = localStorage.getItem('vendor_refresh_token') || sessionStorage.getItem('vendor_refresh_token');
    if (!attemptedToken) {
      refreshPromise = Promise.reject(new Error('No refresh token available.'));
    } else {
      refreshPromise = axios
        .post(`${BASE_URL}/auth/token/refresh`, { refresh_token: attemptedToken })
        .then((res) => {
          const data = res.data?.data ?? res.data;
          const store = getStore();
          store.setItem('vendor_token', data.access_token);
          if (data.refresh_token) store.setItem('vendor_refresh_token', data.refresh_token);
          return data.access_token;
        })
        .catch((err) => {
          // Two tabs sharing one login can both race to refresh the same
          // (about-to-expire) token. If another tab already won that race,
          // storage now holds a newer token than the one we just tried —
          // use it instead of forcing a logout for what is really a no-op.
          const currentToken = localStorage.getItem('vendor_refresh_token') || sessionStorage.getItem('vendor_refresh_token');
          if (currentToken && currentToken !== attemptedToken) {
            const currentAccess = localStorage.getItem('vendor_token') || sessionStorage.getItem('vendor_token');
            if (currentAccess) return currentAccess;
          }
          throw err;
        });
    }
    refreshPromise.finally(() => { refreshPromise = null; });
  }
  return refreshPromise;
}

vendorClient.interceptors.response.use(
  (res) => res,
  async (error) => {
    const { config, response } = error;
    if (response?.status === 401 && config && !config._retried && !config.url?.includes('/auth/')) {
      config._retried = true;
      try {
        const newToken = await refreshAccessToken();
        config.headers.Authorization = `Bearer ${newToken}`;
        return vendorClient(config);
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
