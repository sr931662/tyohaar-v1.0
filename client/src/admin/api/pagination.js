// Pagination glue shared by the admin and vendor API clients.
//
// The backend lists come in three shapes, and pages only ever ask for
// `{ page, per_page }`:
//
//   1. Offset:  { data: [...], meta: { page, page_size, total, total_pages, has_next, has_prev } }
//   2. Cursor:  { data: [...], meta: { cursor, has_next, page_size } }
//   3. Wrapped: { data: { items, total, pages, page, per_page } }
//
// Offset endpoints read `page` + `page_size` (not `per_page`), and cursor
// endpoints ignore `page` entirely and need the opaque `cursor` the previous
// page returned. The request hook below bridges both: it mirrors `per_page`
// into `page_size`, and for page N > 1 attaches the cursor that page N-1's
// response handed back. Pages therefore keep paginating by number and work
// against either kind of endpoint.

// list identity -> Map(page -> cursor that fetches that page)
const cursorStore = new Map();

function listKey(config) {
  const { page, cursor, ...rest } = config.params || {};
  const query = Object.keys(rest)
    .filter((k) => rest[k] !== undefined && rest[k] !== null && rest[k] !== '')
    .sort()
    .map((k) => `${k}=${rest[k]}`)
    .join('&');
  return `${config.url}?${query}`;
}

/** Axios request interceptor body: normalise paging params on list GETs. */
export function preparePagination(config) {
  if ((config.method || 'get').toLowerCase() !== 'get' || !config.params) return config;

  const params = { ...config.params };
  if (params.per_page !== undefined && params.page_size === undefined) {
    params.page_size = params.per_page;
  }
  config.params = params;

  if (params.page === undefined) return config;
  const page = Number(params.page) || 1;
  const key = listKey(config);
  config.paginationKey = { key, page };

  if (page > 1 && !params.cursor) {
    const cursor = cursorStore.get(key)?.get(page);
    if (cursor) config.params = { ...params, cursor };
  }
  return config;
}

function rememberNextCursor(res, nextCursor, hasNext) {
  const info = res.config?.paginationKey;
  if (!info) return;
  let pages = cursorStore.get(info.key);
  if (!pages) {
    pages = new Map();
    cursorStore.set(info.key, pages);
  }
  if (hasNext && nextCursor) pages.set(info.page + 1, nextCursor);
  else pages.delete(info.page + 1);
}

/** Normalise any paginated list response into one shape for the pages. */
export function extractPaginated(res) {
  const raw = res.data;
  const meta = raw?.meta;

  if (Array.isArray(raw?.data) && meta) {
    // Offset-paginated: real totals from the server.
    if (meta.total_pages !== undefined || meta.total !== undefined) {
      const perPage = meta.page_size ?? 20;
      const total = meta.total ?? raw.data.length;
      return {
        items: raw.data,
        total,
        page: meta.page ?? 1,
        per_page: perPage,
        pages: meta.total_pages ?? Math.max(1, Math.ceil(total / perPage)),
        has_next: meta.has_next ?? false,
        next_cursor: null,
        cursor_mode: false,
      };
    }

    // Cursor-paginated: no totals exist, only "is there a next page".
    const page = res.config?.paginationKey?.page ?? 1;
    const hasNext = meta.has_next ?? false;
    rememberNextCursor(res, meta.cursor ?? null, hasNext);
    return {
      items: raw.data,
      total: null,
      page,
      per_page: meta.page_size ?? 20,
      pages: hasNext ? page + 1 : page,
      has_next: hasNext,
      next_cursor: meta.cursor ?? null,
      cursor_mode: true,
    };
  }

  // Offset-paginated inside a SuccessResponse envelope.
  const d = raw?.data;
  const items = d?.items ?? d?.data ?? (Array.isArray(d) ? d : []);
  const perPage = d?.per_page ?? d?.page_size ?? 20;
  const total = d?.total ?? items.length;
  return {
    items,
    total,
    page: d?.page ?? 1,
    per_page: perPage,
    pages: d?.pages ?? d?.total_pages ?? Math.max(1, Math.ceil(total / perPage)),
    has_next: d?.has_next ?? false,
    next_cursor: d?.next_cursor ?? null,
    cursor_mode: false,
  };
}
