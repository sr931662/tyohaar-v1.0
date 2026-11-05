// SPA fallback for any request that isn't a real static asset (e.g. /admin,
// /vendor, /workspace/login on a hard refresh). This catch-all function
// runs for every request BEFORE static-asset matching — it does not run
// only after a static match fails — so it must explicitly delegate
// asset-shaped paths to the real static asset resolver itself, not assume
// they've already been checked.
//
// Path-like requests (anything under /assets/, or ending in a file
// extension) are handed to context.env.ASSETS.fetch(context.request),
// which serves the real file if it exists, or a genuine 404 if not.
// Everything else (an actual client-side route) gets index.html with 200.
//
// /i/* is the exception: guest invitation links. They are served by the API so
// WhatsApp's preview crawler (which runs no JavaScript) gets real Open Graph
// tags from the response. API_ORIGIN can override the default in the Cloudflare
// Pages settings.
const DEFAULT_API_ORIGIN = 'https://tyohaar-v1-0-527701068133.asia-south1.run.app';

export async function onRequest(context) {
  const url = new URL(context.request.url);
  if (url.pathname.startsWith('/i/')) {
    const origin = context.env.API_ORIGIN || DEFAULT_API_ORIGIN;
    // Dropping Host and leaving X-Forwarded-Host unset keeps the page's API
    // calls pointed at the API directly, so rate limits see each guest's own IP.
    const headers = new Headers(context.request.headers);
    headers.delete('host');
    return fetch(new Request(origin + url.pathname + url.search, {
      method: context.request.method,
      headers,
      body: ['GET', 'HEAD'].includes(context.request.method) ? undefined : context.request.body,
      redirect: 'manual',
    }));
  }
  if (url.pathname.startsWith('/assets/') || /\.[a-zA-Z0-9]+$/.test(url.pathname)) {
    return context.env.ASSETS.fetch(context.request);
  }
  return context.env.ASSETS.fetch(new URL('/index.html', url));
}
