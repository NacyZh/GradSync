/// <reference types="vitest" />
import react from '@vitejs/plugin-react';
import path from 'node:path';
import { defineConfig } from 'vite';

import { productionChunkSizeWarningLimit, productionManualChunks } from './build-guards';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': process.env.VITE_API_PROXY_TARGET ?? 'http://backend:8000',
    },
  },
  build: {
    manifest: 'asset-manifest.json',
    chunkSizeWarningLimit: productionChunkSizeWarningLimit,
    rollupOptions: {
      output: {
        manualChunks: productionManualChunks,
      },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    include: ['tests/component/**/*.test.{ts,tsx}', 'src/**/*.test.{ts,tsx}'],
    env: {
      VITE_API_BASE_URL: 'http://localhost:8000',
    },
  },
});
