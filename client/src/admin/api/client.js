import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

export const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// Attach admin token to every request
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('admin_token') || sessionStorage.getItem('admin_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Normalize API responses — backend always wraps in { data, success, message }
apiClient.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('admin_token');
      localStorage.removeItem('admin_user');
      window.location.href = '/admin/login';
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
  const d = res.data?.data;
  return {
    items: d?.items ?? d?.data ?? [],
    total: d?.total ?? 0,
    page: d?.page ?? 1,
    per_page: d?.per_page ?? 20,
    pages: d?.pages ?? 1,
    next_cursor: d?.next_cursor ?? null,
  };
}
