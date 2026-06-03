import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/ws': {
  target      : 'ws://10.85.83.60:5000',
  ws          : true,
  changeOrigin: true,
},
'/api': {
  target      : 'http://10.85.83.60:5000',
  changeOrigin: true,
},
'/stream': {
  target      : 'http://10.85.83.60:5000',
  changeOrigin: true,
},
'/detect': {
  target      : 'http://10.85.83.60:5000',
  changeOrigin: true,
},
    }
  },
  build: {
    outDir  : 'dist',
    sourcemap: true,
  }
})