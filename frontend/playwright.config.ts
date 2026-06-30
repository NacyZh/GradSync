import { defineConfig, devices } from '@playwright/test';

const useFullStack = process.env.GRADSYNC_E2E_MODE === 'fullstack';
const backendPython = process.env.GRADSYNC_BACKEND_PYTHON ?? '../.venv/bin/python';
const backendEnv = {
  DJANGO_SETTINGS_MODULE: 'gradsync.settings.e2e',
  POSTGRES_HOST: '',
};

export default defineConfig({
  testDir: './tests/e2e',
  testMatch: '**/*.spec.ts',
  outputDir: '/tmp/gradsync-playwright-results',
  workers: useFullStack ? 1 : undefined,
  webServer: useFullStack
    ? [
        {
          command:
            `cd ../backend && ${backendPython} manage.py migrate --noinput && ${backendPython} manage.py seed_e2e_research_ops && ${backendPython} manage.py runserver 127.0.0.1:8000 --noreload`,
          url: 'http://127.0.0.1:8000/healthz/',
          reuseExistingServer: false,
          timeout: 120_000,
          env: backendEnv,
        },
        {
          command: 'npm run dev -- --host 127.0.0.1',
          url: 'http://127.0.0.1:5173',
          reuseExistingServer: !process.env.CI,
          timeout: 120_000,
          env: {
            VITE_API_PROXY_TARGET: 'http://127.0.0.1:8000',
          },
        },
      ]
    : {
        command: 'npm run dev',
        url: 'http://127.0.0.1:5173',
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
      },
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
