// e2e/self-service.spec.js：AC4 查看 / 更正 / 下载副本 / 撤回删除 + 联系人工
import { test, expect } from '@playwright/test';
import { resetMock, gotoEntry, acceptConsent, completeSlots, openProfile } from './helpers.js';

test.beforeEach(async ({ request }) => {
  await resetMock(request);
});

test('AC4 自助四项可用；撤回后本地缓存清空且会话失效', async ({ page, request }) => {
  await gotoEntry(page, 'poster_qr');
  await acceptConsent(page);
  await completeSlots(page);
  await openProfile(page);

  await expect(page.getByTestId('profile-name')).toHaveText('王**');
  await expect(page.getByTestId('profile-phone')).toHaveText('139****0000');
  await expect(page.getByTestId('profile-area')).toContainText('浦东新区张江镇');
  await expect(page.getByTestId('profile-consent-version')).toHaveText('v1.0');
  await expect(page.getByTestId('profile-consent-at')).toContainText('T');

  await page.getByTestId('edit-info').click();
  await expect(page.getByTestId('edit-panel')).toBeVisible();
  await page.getByTestId('edit-area').fill('闵行区七宝镇');
  await page.getByTestId('edit-job').selectOption('parttime');
  await page.getByTestId('save-edit').click();
  await expect(page.getByTestId('profile-notice')).toContainText('信息已更正');
  await expect(page.getByTestId('profile-area')).toContainText('闵行区七宝镇');
  await expect(page.locator('.info-row', { hasText: '岗位意向' })).toContainText('兼职');

  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.getByTestId('download-copy').click(),
  ]);
  expect(download.suggestedFilename()).toMatch(/candidate-.*\.json$/);
  await expect(page.getByTestId('profile-notice')).toContainText('信息副本已下载');

  await expect(page.getByTestId('contact-human')).toHaveAttribute('href', /^tel:400/);

  const stored = await page.evaluate(() => ({
    session: window.localStorage.getItem('ch1807.session'),
    progress: window.localStorage.getItem('ch1807.progress'),
  }));
  expect(stored.session).not.toBeNull();
  expect(stored.progress).not.toBeNull();
  const session = JSON.parse(stored.session);

  await page.getByTestId('revoke-consent').click();
  await expect(page.getByTestId('revoke-confirm-panel')).toBeVisible();
  await page.getByTestId('revoke-confirm').click();
  await expect(page.getByTestId('revoked-screen')).toBeVisible();

  const cleared = await page.evaluate(() => ({
    session: window.localStorage.getItem('ch1807.session'),
    progress: window.localStorage.getItem('ch1807.progress'),
  }));
  expect(cleared.session).toBeNull();
  expect(cleared.progress).toBeNull();

  const expired = await request.get(`/api/v1/agent/sessions/${session.session_id}`, {
    headers: { Authorization: `Bearer ${session.token}` },
  });
  expect(expired.status()).toBe(410);
  const candidate = await request.get(`/api/v1/candidates/${session.candidate_id}`, {
    headers: { Authorization: `Bearer ${session.token}` },
  });
  expect(candidate.status()).toBe(410);
});
