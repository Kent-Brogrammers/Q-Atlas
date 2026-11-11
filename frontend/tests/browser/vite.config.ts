// Serve the live browser regression only when this test configuration is requested.
import { readFileSync } from 'node:fs';
import { defineConfig, mergeConfig } from 'vite';
import app from '../../vite.config.ts';

export default mergeConfig(
  defineConfig({
    define: { 'import.meta.env.VITE_API_BASE_URL': JSON.stringify('/api') },
    server: { proxy: { '/api': 'http://127.0.0.1:8000' } },
    plugins: [
      {
        name: 'neutrino-browser-regression',
        enforce: 'pre',
        configureServer(server) {
          server.middlewares.use('/tests/browser/neutrinos.html', (_req, res) => {
            res.setHeader('Content-Type', 'text/html; charset=utf-8');
            res.end(readFileSync(new URL('./neutrinos.html', import.meta.url)));
          });
        }
      }
    ]
  }),
  app
);
