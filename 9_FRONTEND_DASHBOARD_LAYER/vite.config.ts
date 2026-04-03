import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [
    react({
      jsxRuntime: 'classic'
    })
  ],
  server: {
    port: 3000,
    host: '127.0.0.1',
    open: false,
    strictPort: false
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    minify: 'esbuild'
  }
})
