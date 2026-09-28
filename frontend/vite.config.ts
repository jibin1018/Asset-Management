import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  // 기본값 'assets'는 자산 화면 경로(/assets)와 겹치므로 변경
  build: { assetsDir: 'static' },
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
});
