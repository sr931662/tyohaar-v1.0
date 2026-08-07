import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// Appended to every output filename so each build gets guaranteed-unique
// asset names, even for files whose content is byte-identical to a prior
// build. Cloudflare Pages dedupes uploads by filename/hash and skips
// re-uploading a name it already has on record — but that record can go
// stale (its "already uploaded" file 404s on the CDN), silently breaking
// whichever chunks/CSS collide with a bad entry. A per-build salt means
// nothing ever collides with a previous deploy's record.
const BUILD_SALT = Date.now().toString(36)

export default defineConfig({
  base: '/',
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    emptyOutDir: true,
    assetsDir: 'assets',
    rollupOptions: {
      output: {
        entryFileNames: `assets/[name]-[hash]-${BUILD_SALT}.js`,
        chunkFileNames: `assets/[name]-[hash]-${BUILD_SALT}.js`,
        assetFileNames: `assets/[name]-[hash]-${BUILD_SALT}.[ext]`,
      },
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  preview: {
    proxy: {
      '/api': {
        target: 'https://tyohaar-v1-0-527701068133.asia-south1.run.app',
        changeOrigin: true,
      },
    },
  },
})
