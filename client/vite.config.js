import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Served at a real tenant subdomain (e.g. office1.lvh.me:5173), never plain
// localhost — the backend's CORS allow_origin_regex only trusts
// *.{BASE_DOMAIN} origins, and session cookies are scoped to .lvh.me.
// allowedHosts opts every lvh.me subdomain in (Vite's dev server otherwise
// rejects unrecognized Host headers as a DNS-rebinding guard).
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    strictPort: true,
    allowedHosts: ['.lvh.me'],
  },
})
