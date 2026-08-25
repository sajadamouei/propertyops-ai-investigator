import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',

  fullyParallel: false,
  workers: 1,

  retries: process.env.CI ? 1 : 0,

  reporter: [
    ['list'],
    ['html', { open: 'never' }],
  ],

  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'retain-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  webServer: [
    {
      name: 'MCP',
      command: 'uv run python -m propertyops_ai_investigator.mcp_servers.run_http',
      cwd: '..',
      port: 8000,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      name: 'FastAPI',
      command: 'uv run uvicorn propertyops_ai_investigator.api.main:app --host 127.0.0.1 --port 8080',
      cwd: '..',
      url: 'http://127.0.0.1:8080/api/health',
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      name: 'Vite',
      command: 'npm run dev -- --host 127.0.0.1 --port 5173 --strictPort',
      url: 'http://127.0.0.1:5173',
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
})
