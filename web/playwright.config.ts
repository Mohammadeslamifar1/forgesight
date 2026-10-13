import { defineConfig } from '@playwright/test';
import path from 'node:path';

const root = path.resolve(import.meta.dirname, '..');
const python = path.join(
  root,
  '.venv',
  process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python',
);
export default defineConfig({
  testDir: './e2e',
  workers: 1,
  retries: 0,
  timeout: 30000,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: 'http://127.0.0.1:8011',
    viewport: { width: 1440, height: 1050 },
    channel:
      process.env.FORGESIGHT_BROWSER_CHANNEL ||
      (process.platform === 'win32' ? 'msedge' : undefined),
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: `"${python}" "${path.join(root, 'scripts/e2e_server.py')}"`,
    url: 'http://127.0.0.1:8011/api/health',
    reuseExistingServer: false,
    timeout: 90000,
  },
});
