// e2e/full-flow.spec.js：AC1 主流程全链路 + 政策卡出处 + 结果页
import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { resetMock, gotoEntry, acceptConsent, completeSlots, bookFirstStation } from './helpers.js';

test.beforeEach(async ({ request }) => {
  await resetMock(request);
});

test('AC1 渠道入口 → 同意 → 7 项 → 政策问答 → 选站点 → 预约 → 结果页', async ({ page }) => {
  await gotoEntry(page, 'poster_qr');
  await expect(page.getByTestId('channel-chip')).toContainText('poster_qr');

  const dcl = await page.evaluate(() => {
    const nav = performance.getEntriesByType('navigation')[0];
    if (nav) return Math.round(nav.domContentLoadedEventEnd - nav.startTime);
    return performance.timing.domContentLoadedEventEnd - performance.timing.navigationStart;
  });
  fs.mkdirSync('evidence', { recursive: true });
  fs.writeFileSync(
    path.join('evidence', 'perf.json'),
    JSON.stringify(
      {
        metric: 'domContentLoadedEventEnd - navigationStart (ms)',
        value_ms: dcl,
        environment: '本地 Vite dev + mock（不代表 4G 现场）',
        measured_at: new Date().toISOString(),
      },
      null,
      2,
    ),
  );
  expect(dcl).toBeLessThan(2000);

  await acceptConsent(page);
  await expect(page.getByTestId('progress-text')).toHaveText('已收集 0/7 项');
  await completeSlots(page);
  await expect(page.getByTestId('progress-text')).toHaveText('已收集 7/7 项');
  await expect(page.getByTestId('progress-fields')).toContainText('配送经验');

  await page.getByTestId('message-input').fill('站点有住宿吗？');
  await page.getByTestId('send-btn').click();
  await expect(page.getByTestId('policy-card')).toBeVisible();
  await expect(page.getByTestId('policy-sources')).toContainText('出处：');
  await expect(page.getByTestId('policy-sources')).toContainText('POL-1807 §3.2');
  await expect(page.getByTestId('policy-disclaimer')).toContainText('免责声明');

  await expect(page.getByTestId('station-card')).toHaveCount(3);
  await expect(page.getByTestId('station-card').first()).toContainText('在招');
  await expect(page.getByTestId('station-card').first()).toContainText('km');

  await bookFirstStation(page);
  await expect(page.getByTestId('booking-status')).toHaveText('预约成功');
  await expect(page.getByTestId('booking-slot')).toContainText('时段：');
  await expect(page.getByTestId('nav-link')).toHaveAttribute('href', /uri\.amap\.com/);
  await expect(page.getByTestId('call-station-btn')).toHaveAttribute('href', /^tel:400/);
  await expect(page.getByTestId('arrival-notes')).toContainText('到站须知');
  await expect(page.getByTestId('arrival-notes')).toContainText('健康证');

  const originalSlot = await page.getByTestId('booking-slot').innerText();
  await page.getByTestId('reschedule-btn').click();
  await expect(page.getByTestId('reschedule-panel')).toBeVisible();
  const newSlotButton = page.getByTestId('reschedule-slot').nth(1);
  const newSlotText = await newSlotButton.innerText();
  await newSlotButton.click();
  await expect(page.getByTestId('booking-slot')).toContainText(newSlotText);

  await page.getByTestId('cancel-btn').click();
  await expect(page.getByTestId('cancel-panel')).toBeVisible();
  await page.getByTestId('cancel-confirm').click();
  await expect(page.getByTestId('booking-status')).toHaveText('预约已取消');
  await expect(page.getByTestId('booking-slot')).toContainText(newSlotText);
  expect(originalSlot).toContain('时段：');
});
