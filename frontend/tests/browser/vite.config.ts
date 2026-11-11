// Serve the live browser regression only when this test configuration is requested.
import { readFileSync } from 'node:fs';
import { defineConfig, mergeConfig } from 'vite';
import app from '../../vite.config.ts';

export default mergeConfig(
  defineConfig({
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
