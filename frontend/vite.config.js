import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': 'http://localhost:8000',
      '/projects': 'http://localhost:8000',
      '/scans': 'http://localhost:8000',
      '/scan': 'http://localhost:8000',
      '/deploy': 'http://localhost:8000',
      '/github': 'http://localhost:8000',
      '/llm': 'http://localhost:8000',
      '/apply-fix': 'http://localhost:8000',
      '/add-suggestion-comment': 'http://localhost:8000',
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true
      }
    }
  }
})
