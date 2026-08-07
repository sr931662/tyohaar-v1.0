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
export async function onRequest(context) {
  const url = new URL(context.request.url);
  if (url.pathname.startsWith('/assets/') || /\.[a-zA-Z0-9]+$/.test(url.pathname)) {
    return context.env.ASSETS.fetch(context.request);
  }
  return context.env.ASSETS.fetch(new URL('/index.html', url));
}
