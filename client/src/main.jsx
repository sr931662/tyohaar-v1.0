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
window.addEventListener('vite:preloadError', () => {
  window.location.reload();
});

// A prior chunk-load reload succeeded (we got this far), so clear the
// one-shot guard — otherwise a second stale-deploy later in the same tab
// session would be unable to trigger another recovery reload.
sessionStorage.removeItem('ty_chunk_reload_attempted');

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
