import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests', workers: 1,
  use: {
    baseURL: 'http://127.0.0.1:8768',
    viewport: {width: 1040, height: 760},
    launchOptions: {executablePath: process.env.WESI_CHROMIUM_PATH || undefined},
  },
  webServer: {
    command: 'python3 -m http.server 8768 --bind 127.0.0.1',
    url: 'http://127.0.0.1:8768', reuseExistingServer: false,
  },
});
