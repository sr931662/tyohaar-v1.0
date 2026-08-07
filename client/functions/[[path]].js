// SPA fallback for any request that isn't a real static asset (e.g. /admin,
// /vendor, /workspace/login on a hard refresh). Pages Functions only run
// once static-asset matching has already failed, so this always serves
// index.html — with a genuine 200, unlike the custom-404.html fallback,
// which works but always reports 404 to the browser/console.
//
// Path-like requests (anything under /assets/, or ending in a file
// extension) must NOT get this treatment: a stale or genuinely missing JS
// chunk needs a real 404, not a 200 text/html response — the latter breaks
// dynamic import() with a MIME-type error instead of a clean, recoverable
// 404, and Cloudflare would cache that bogus 200 for hours.
export async function onRequest(context) {
  const url = new URL(context.request.url);
  if (url.pathname.startsWith('/assets/') || /\.[a-zA-Z0-9]+$/.test(url.pathname)) {
    return new Response('Not found', { status: 404, headers: { 'Cache-Control': 'no-store' } });
  }
  return context.env.ASSETS.fetch(new URL('/index.html', url));
}
