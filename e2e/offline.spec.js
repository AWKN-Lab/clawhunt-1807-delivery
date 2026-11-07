// e2e/offline.spec.js：AC6 断网 10 秒 → 恢复，进度与会话不丢失
import { test, expect } from '@playwright/test';
import { resetMock, gotoEntry, acceptConsent, answer, quickAnswer } from './helpers.js';

test.beforeEach(async ({ request }) => {
  await resetMock(request);
});

test('AC6 断网 10 秒期间进度保留，恢复后会话续接', async ({ page, context }) => {
  test.setTimeout(120000);
  await gotoEntry(page, 'poster_qr');
  await acceptConsent(page);
  await answer(page, '王小明', 1);
  await answer(page, '1998-05', 2);
  await answer(page, '浦东新区张江镇', 3);

  const before = await page.getByTestId('progress-text').innerText();
  expect(before).toBe('已收集 3/7 项');
  const localBefore = await page.evaluate(() => JSON.parse(window.localStorage.getItem('ch1807.progress')));
  expect(localBefore.done).toBe(3);

  await context.setOffline(true);
  await expect(page.getByTestId('offline-banner')).toBeVisible();
  await expect(page.getByTestId('offline-note')).toBeVisible();

  await page.waitForTimeout(10000);

  await expect(page.getByTestId('progress-text')).toHaveText('已收集 3/7 项');
  await expect(page.getByTestId('progress-fields')).toContainText('意向区域');
  const during = await page.evaluate(() => ({
    progress: JSON.parse(window.localStorage.getItem('ch1807.progress')),
    session: JSON.parse(window.localStorage.getItem('ch1807.session')),
  }));
  expect(during.progress.done).toBe(3);
  expect(during.progress.fields).toEqual(localBefore.fields);
  expect(during.session.session_id).toBeTruthy();
  expect(during.session.token).toBeTruthy();

  await context.setOffline(false);
  await expect(page.getByTestId('offline-banner')).toHaveCount(0);
  await expect(page.getByTestId('progress-text')).toHaveText('已收集 3/7 项');

  await quickAnswer(page, '全职', 4);
  const after = await page.evaluate(() => JSON.parse(window.localStorage.getItem('ch1807.progress')));
  expect(after.done).toBe(4);
  await expect(page.getByTestId('progress-fields')).toContainText('岗位意向');
});
