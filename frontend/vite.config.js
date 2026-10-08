import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // The app calls /api/... on its own address and Vite forwards it to the
    // Flask backend. That keeps cookies same-origin, and it means a phone on
    // the same Wi-Fi only needs to reach this one port (5173).
    proxy: {
      '/api': 'http://127.0.0.1:5001',
    },
  },
})
