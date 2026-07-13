import { useQuery } from '@tanstack/react-query';
import { getOccasions } from '../api/endpoints/occasions.js';
import { FALLBACK_OCCASIONS } from '../data/occasions.js';

// Shared query key so the landing page's occasion grid (Occasions.jsx) and
// scrolling ticker (Marquee.jsx) both read from one cached query instead of
// firing two network calls.
export const OCCASIONS_QUERY_KEY = ['public', 'occasions'];

const TINTS = ['saffron', 'rose', 'leaf', 'gold'];
const FALLBACK_BY_SLUG = Object.fromEntries(FALLBACK_OCCASIONS.map((o) => [o.id, o]));

// The public OccasionResponse only exposes id/name/slug/description/icon_url/
// display_order etc — it has no notion of the mother-tongue "sub" label,
// blurb copy, tint, or emblem key the current design uses. Where a live
// occasion's slug matches one of the existing hand-authored entries, reuse
// its copy/styling; otherwise fall back to sensible generic defaults so new
// occasions added purely on the backend still render sensibly.
function shapeOccasion(raw, index) {
  const match = FALLBACK_BY_SLUG[raw.slug];
  return {
    id: raw.id,
    en: raw.name,
    sub: match?.sub ?? '',
    emblem: match?.emblem ?? 'sparkles',
    tint: match?.tint ?? TINTS[index % TINTS.length],
    blurb: raw.description ?? match?.blurb ?? '',
    iconUrl: raw.icon_url ?? null,
  };
}

export function useOccasions() {
  const query = useQuery({
    queryKey: OCCASIONS_QUERY_KEY,
    queryFn: async () => {
      const items = await getOccasions();
      return items.map(shapeOccasion);
    },
    // Near-static marketing content — no need to refetch aggressively.
    staleTime: 30 * 60 * 1000, // 30 minutes
    gcTime: 60 * 60 * 1000, // 1 hour
    retry: 1,
  });

  const hasData = Array.isArray(query.data) && query.data.length > 0;

  return {
    ...query,
    // On error, or while loading with nothing cached yet, fall back to the
    // static list so the landing page is never blank.
    occasions: hasData ? query.data : FALLBACK_OCCASIONS,
    isFallback: !hasData,
  };
}
