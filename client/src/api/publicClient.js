import axios from 'axios';

// Unauthenticated axios instance for public marketing-site data (e.g. the
// landing page's occasions catalogue). No token/refresh interceptors —
// mirrors the shape of `client/src/admin/api/client.js` minus auth concerns.
const BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

export const publicClient = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

export function extractData(res) {
  return res.data?.data ?? res.data;
}

export function extractPaginated(res) {
  const raw = res.data;

  // Cursor-paginated: { data: [...], meta: { cursor, has_next, page_size } }
  if (Array.isArray(raw?.data) && raw?.meta !== undefined) {
    return {
      items: raw.data,
      next_cursor: raw.meta?.cursor ?? null,
      has_next: raw.meta?.has_next ?? false,
    };
  }

  // Offset-paginated (SuccessResponse-wrapped): { data: { items, ... } }
  const d = raw?.data;
  return {
    items: d?.items ?? d?.data ?? [],
    next_cursor: d?.next_cursor ?? null,
    has_next: false,
  };
}
