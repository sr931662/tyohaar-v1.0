import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'sonner';
import App from './App.jsx';
import ChunkErrorBoundary from './components/ChunkErrorBoundary.jsx';
import { ThemeProvider } from './context/ThemeContext.jsx';
import './index.css';

// Same class of failure as ChunkErrorBoundary (a stale tab referencing
// chunk hashes a newer deploy removed), but for module *preloading*
// (<link rel="modulepreload">, router route prefetch) rather than a
// React.lazy() import — Vite fires this event specifically for that case.
// Guarded by the same one-shot flag as ChunkErrorBoundary so a persistently
// stale bundle (or CDN/browser still serving an old index.html) can't reload
// forever.
function reloadFresh() {
  const url = new URL(window.location.href);
  url.searchParams.set('ty_cache_bust', String(Date.now()));
  window.location.replace(url.toString());
}

window.addEventListener('vite:preloadError', () => {
  if (!sessionStorage.getItem('ty_chunk_reload_attempted')) {
    sessionStorage.setItem('ty_chunk_reload_attempted', '1');
    reloadFresh();
  }
});

// Same stale-deploy failure mode as vite:preloadError, but for the
// index.html-referenced stylesheet <link> rather than a JS chunk. A missing
// hashed CSS file falls through the SPA catch-all redirect and comes back
// as index.html (text/html), which the browser refuses to apply as a
// stylesheet — that failure only surfaces as a capturing-phase 'error'
// event on the <link>, never a catchable JS exception, so it needs its own
// listener instead of going through ChunkErrorBoundary.
window.addEventListener(
  'error',
  (event) => {
    const target = event.target;
    if (
      target instanceof HTMLLinkElement &&
      target.rel === 'stylesheet' &&
      !sessionStorage.getItem('ty_chunk_reload_attempted')
    ) {
      sessionStorage.setItem('ty_chunk_reload_attempted', '1');
      reloadFresh();
    }
  },
  true
);

// A prior chunk-load reload succeeded (we got this far), so clear the
// one-shot guard — otherwise a second stale-deploy later in the same tab
// session would be unable to trigger another recovery reload.
//
// This has to be delayed, not immediate: this script runs on *every* load,
// including the one the boundary's own reload() just triggered. If the
// reload didn't actually fix anything (e.g. index.html itself is still
// being served stale by a CDN edge cache), clearing the flag right away lets
// the very next lazy chunk failure re-arm the guard and reload again.
window.setTimeout(() => {
  sessionStorage.removeItem('ty_chunk_reload_attempted');
}, 5000);

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider>
          <ChunkErrorBoundary>
            <App />
          </ChunkErrorBoundary>
          <Toaster position="top-right" richColors closeButton />
        </ThemeProvider>
      </QueryClientProvider>
    </BrowserRouter>
  </React.StrictMode>
);
