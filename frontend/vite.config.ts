import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/static/dist/',  // ✅ 关键：构建时自动生成正确的路径前缀
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:5011',
        changeOrigin: true
      },
      '/static': {
        target: 'http://localhost:5011',
        changeOrigin: true
      }
    },
    middlewareMode: false
  },
  build: {
    outDir: '../static/dist',
    assetsDir: 'assets',
    emptyOutDir: true,
    sourcemap: false
  }
})
