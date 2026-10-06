import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // In development the browser calls /api/..., and Vite forwards it to FastAPI.
    // Same origin for the browser, so no CORS setup is needed.
    proxy: {
      '/api': { target: 'http://localhost:8000', rewrite: (path) => path.replace(/^\/api/, '') },
    },
  },
})