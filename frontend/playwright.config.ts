import { defineConfig } from '@playwright/test';
import { existsSync } from 'node:fs';
import { resolve } from 'node:path';

const localPython = resolve('../venv/Scripts/python.exe');
const python = process.env.BACKEND_PYTHON || (existsSync(localPython) ? localPython : 'python');

export default defineConfig({
  testDir: './tests',
  use: { baseURL: 'http://127.0.0.1:4175', channel: process.env.CI ? undefined : 'msedge' },
  webServer: [{
    command: `"${python}" -m tests.e2e_server`,
    cwd: '../backend',
    url: 'http://127.0.0.1:8175/health',
    reuseExistingServer: false,
  }, {
    command: 'npm run dev -- --host 127.0.0.1 --port 4175 --strictPort',
    url: 'http://127.0.0.1:4175',
    reuseExistingServer: false,
    env: { API_URL: 'http://127.0.0.1:8175', API_KEY: 'e2e-local-api-key' },
  }],
});
