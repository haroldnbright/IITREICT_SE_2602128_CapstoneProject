// Vite build and dev server settings for the React frontend
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  // Enables JSX and fast refresh for React components
  plugins: [react()],
  // Fixed dev port so the backend's CORS settings can allow it
  server: { port: 5173 },
})
