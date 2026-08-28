import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // The API runs on :8000 and the dev server on :5173, which the browser treats
  // as different origins. Proxying here keeps every request same-origin, so no
  // CORS setup is needed in app/main.py — a file the whole group shares.
  //
  // Dev only. Vite does not run in production; deploying this needs a real
  // answer (CORS on the API, or the API and the built assets behind one host).
  server: {
    proxy: {
      // Preferred: one prefix, stripped on the way through, so a new endpoint
      // needs no change here. src/api/client.js sends everything this way.
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },

      // Kept from the subscriptions branch so existing calls that hit these
      // paths directly keep working. Note this style needs every prefix listed
      // by hand — `/accounts`, `/transfers` and `/subscriptions` are all
      // missing, so anything calling those directly will 404. Worth collapsing
      // into `/api` above once the group agrees.
      '/auth': 'http://localhost:8000',
      '/admin': 'http://localhost:8000',
    },
  },
})
