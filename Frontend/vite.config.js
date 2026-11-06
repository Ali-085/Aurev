import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],

  server: {
    port: 5173,

    // Allow external hosts (ngrok, cloudflare tunnel)
    host: true,
    allowedHosts: [
      "", // add your tunnel host here
    ],

    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },

  preview: {
    allowedHosts: [
      "", // needed when using vite preview
    ]
  }
})
