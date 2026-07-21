import { Component } from 'react';

const RELOAD_FLAG = 'ty_chunk_reload_attempted';

// After a new deploy, every lazy-loaded chunk gets a new content hash and
// the old hashed files are gone from the server. A tab that's had the app
// open since before the deploy still references the old hashes, so its next
// route navigation (or lazy component mount) fails with "Failed to fetch
// dynamically imported module" / "Failed to load module script" — the
// browser has no way to recover from that on its own.
function isChunkLoadError(error) {
  const msg = String(error?.message ?? error ?? '');
  return (
    msg.includes('Failed to fetch dynamically imported module') ||
    msg.includes('error loading dynamically imported module') ||
    msg.includes('Importing a module script failed') ||
    msg.includes('Failed to load module script')
  );
}

export default class ChunkErrorBoundary extends Component {
  state = { hasError: false, error: null };

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error) {
    if (isChunkLoadError(error) && !sessionStorage.getItem(RELOAD_FLAG)) {
      // Reload once to pick up the fresh index.html and current chunk map.
      // Guarded by sessionStorage so a genuinely broken deploy (or offline
      // network) can't trap the tab in a reload loop.
      sessionStorage.setItem(RELOAD_FLAG, '1');
      window.location.reload();
    }
  }

  render() {
    if (this.state.hasError) {
      if (isChunkLoadError(this.state.error)) {
        return (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', fontFamily: 'sans-serif', color: '#888' }}>
            Updating to the latest version…
          </div>
        );
      }
      return (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100vh', fontFamily: 'sans-serif', color: '#888', gap: 12 }}>
          <div>Something went wrong.</div>
          <button
            onClick={() => window.location.reload()}
            style={{ padding: '8px 16px', cursor: 'pointer', border: '1px solid #888', borderRadius: 6, background: 'transparent', color: 'inherit' }}
          >
            Reload
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
