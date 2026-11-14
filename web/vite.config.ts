import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // MapLibre starts its own web worker from a file URL; pre-bundling it in dev breaks that.
  optimizeDeps: { exclude: ['maplibre-gl'] },
});
