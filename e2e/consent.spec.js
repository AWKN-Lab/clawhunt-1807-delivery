// e2e/consent.spec.js：AC2 同意门（不勾选不可开始 / 拒绝出口 / 版本与时间回传）
import { test, expect } from '@playwright/test';
import { resetMock, gotoEntry } from './helpers.js';

test.beforeEach(async ({ request }) => {
  await resetMock(request);
});

test('AC2 不勾选无法开始；不同意有电话出口；payload 含 consent_version 与 consent_at', async ({ page }) => {
  await gotoEntry(page, 'poster_qr');

  await expect(page.getByTestId('consent-start')).toBeDisabled();
  await expect(page.getByTestId('consent-phone')).toHaveCount(0);

  await page.getByTestId('consent-reject').click();
  await expect(page.getByTestId('consent-phone')).toBeVisible();
  await expect(page.getByTestId('consent-phone')).toContainText('400-000-1807');
  await expect(page.getByTestId('consent-phone').getByRole('link')).toHaveAttribute('href', /^tel:400/);
  await expect(page.getByTestId('chat-screen')).toHaveCount(0);

  let payload = null;
  await page.route('**/api/v1/consents', async (route) => {
    try {
      payload = JSON.parse(route.request().postData() || '{}');
    } catch {
      payload = {};
    }
    await route.continue();
  });

  await expect(page.getByTestId('consent-start')).toBeDisabled();
  await page.getByTestId('consent-checkbox').check();
  await expect(page.getByTestId('consent-start')).toBeEnabled();
  await page.getByTestId('consent-start').click();
  await expect(page.getByTestId('chat-screen')).toBeVisible();

  expect(payload).not.toBeNull();
  expect(payload.consent_version).toBe('v1.0');
  expect(payload.consent_at).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/);
  expect(new Date(payload.consent_at).getTime()).toBeGreaterThan(Date.now() - 10 * 60 * 1000);
  expect(payload.source_channel).toBe('poster_qr');
});
