import { fileURLToPath, URL } from 'node:url'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [react()],
  server: {
    // El asistente real vive en el backend de desarrollo (puerto 8000); así no hace falta CORS.
    proxy: {
      '/dev': { target: 'http://127.0.0.1:8000', changeOrigin: true, timeout: 150_000 },
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true, timeout: 150_000 },
    },
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    coverage: {
      provider: 'v8',
      include: ['src/**/*.{ts,tsx}'],
      // main.tsx solo monta la app; lo verifica el build y la prueba en navegador.
      exclude: [
        'src/**/*.test.{ts,tsx}',
        'src/test/**',
        'src/main.tsx',
        'src/data/graphql/generated/**',
      ],
      thresholds: { lines: 80, functions: 80, branches: 80, statements: 80 },
    },
  },
})
