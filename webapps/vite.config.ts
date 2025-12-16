import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import path from 'path';

const tradersRoot = path.resolve(__dirname, 'traders-app');

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [svelte()],
  root: tradersRoot,
  publicDir: path.resolve(__dirname, 'traders-app/public'),
  resolve: {
    alias: {
      '$lib': path.resolve(__dirname, 'traders-app/src/lib'),
      '$components': path.resolve(__dirname, 'traders-app/src/components'),
      '$stores': path.resolve(__dirname, 'traders-app/src/stores'),
      '$contexts': path.resolve(__dirname, 'traders-app/src/contexts'),
      '$services': path.resolve(__dirname, 'traders-app/src/services'),
      '$mocks': path.resolve(__dirname, 'traders-app/src/mocks')
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: '../../static/webapps/traders-app',
    emptyOutDir: true,
    sourcemap: true,
    rollupOptions: {
      output: {
        entryFileNames: 'index.js',
        assetFileNames: 'assets/[name].[ext]',
        chunkFileNames: 'assets/[name]-[hash].js',
      }
    },
  }
});