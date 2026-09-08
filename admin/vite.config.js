import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Served at the same tenant subdomain as client/, distinguished only by
// port (e.g. office1.lvh.me:5174) — see client/vite.config.js for why
// allowedHosts needs the *.lvh.me wildcard.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5174,
    strictPort: true,
    allowedHosts: ['.lvh.me'],
  },
})
