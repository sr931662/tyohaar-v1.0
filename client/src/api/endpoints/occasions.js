import { publicClient, extractPaginated } from '../publicClient.js';

// Public occasions catalogue for the marketing landing page.
// Follows the same params/unwrapping conventions as
// `client/src/admin/api/endpoints/occasions.js`, scoped to active entries.
// The backend already returns results ordered by `display_order` — no
// explicit ordering param exists on `GET /occasions`.
export function getOccasions() {
  return publicClient
    // page_size raised to the API max (100) — the occasions catalogue is
    // small and static, and the landing page needs the whole list in one
    // call rather than paging through the default page size of 20.
    .get('/occasions', { params: { is_active: true, page_size: 100 } })
    .then(extractPaginated)
    .then((res) => res.items);
}
