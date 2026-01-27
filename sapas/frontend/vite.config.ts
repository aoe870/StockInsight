import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    'api': path.resolve(__dirname, './src/api'),
      'components': path.resolve(__dirname, './src/components'),
      'stores': path.resolve(__dirname, './src/stores'),
    'utils': path.resolve(__dirname, './src/utils'),
      'types': path.resolve(__dirname, './src/types')
    },
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: 'http://localhost:8082',
          changeOrigin: true
        },
        '/ws': {
          target: 'ws://localhost:8082',
          ws: true
        }
      }
    }
  })
