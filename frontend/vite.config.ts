import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        // SSE 支持：当响应是 event-stream 时，禁用代理缓冲
        configure: (proxy) => {
          proxy.on('proxyRes', (proxyRes, req) => {
            // 检测 SSE 响应，禁用缓冲
            const contentType = proxyRes.headers['content-type'] || '';
            if (contentType.includes('text/event-stream')) {
              // 禁用 http-proxy 的响应缓冲
              // 通过设置 socket 的 noDelay 和修改响应头
              proxyRes.headers['X-Accel-Buffering'] = 'no';
              proxyRes.headers['Cache-Control'] = 'no-cache, no-transform';
            }
          });
        },
      },
    },
  },
})
