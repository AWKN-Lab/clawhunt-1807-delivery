// playwright.config.js：E2E 入口（默认自带 dev server；设置 CH1807_BASE_URL 可复用外部服务）
import fs from 'node:fs';
import { defineConfig } from '@playwright/test';

// 本机存在失效的 PLAYWRIGHT_BROWSERS_PATH（指向不存在盘符）时回退默认缓存目录
if (process.env.PLAYWRIGHT_BROWSERS_PATH && !fs.existsSync(process.env.PLAYWRIGHT_BROWSERS_PATH)) {
  delete process.env.PLAYWRIGHT_BROWSERS_PATH;
}

const BASE_URL = process.env.CH1807_BASE_URL || 'http://127.0.0.1:5173';

export default defineConfig({
  testDir: './e2e',
  timeout: 60000,
  expect: { timeout: 10000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list'], ['json', { outputFile: 'evidence/playwright.json' }]],
  use: {
    baseURL: BASE_URL,
    viewport: { width: 390, height: 844 },
    locale: 'zh-CN',
    timezoneId: 'Asia/Shanghai',
    trace: 'retain-on-failure',
  },
  webServer: process.env.CH1807_BASE_URL
    ? undefined
    : {
        command: 'node scripts/dev.mjs',
        url: 'http://127.0.0.1:5173',
        reuseExistingServer: true,
        timeout: 120000,
        stdout: 'pipe',
        stderr: 'pipe',
      },
});
