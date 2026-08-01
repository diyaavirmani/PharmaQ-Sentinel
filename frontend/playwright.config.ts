import { defineConfig, devices } from "@playwright/test";

const uiTestPort = Number(process.env.PLAYWRIGHT_PORT ?? 5173);
const baseURL = `http://127.0.0.1:${uiTestPort}`;

export default defineConfig({
  testDir: "./tests/ui",
  outputDir: "./test-results/playwright",
  reporter: "list",
  use: {
    baseURL,
    trace: "on-first-retry"
  },
  webServer: {
    command: `npm run dev -- --host 127.0.0.1 --port ${uiTestPort}`,
    url: baseURL,
    reuseExistingServer: !process.env.CI,
    env: {
      VITE_ENABLE_WORKSPACE_TEST_STATES: "true"
    },
    timeout: 120000
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 960 } }
    }
  ]
});
