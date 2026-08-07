// SPA fallback for any request that isn't a real static asset (e.g. /admin,
// /vendor, /workspace/login on a hard refresh). Pages Functions only run
// once static-asset matching has already failed, so this always serves
// index.html — with a genuine 200, unlike the custom-404.html fallback,
// which works but always reports 404 to the browser/console.
export async function onRequest(context) {
  return context.env.ASSETS.fetch(new URL('/index.html', context.request.url));
}
