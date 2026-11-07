// e2e/helpers.js：共享流程步骤
import { expect } from '@playwright/test';

export async function resetMock(request) {
  const response = await request.post('/api/v1/_mock/reset');
  expect(response.ok()).toBeTruthy();
}

export async function gotoEntry(page, channel = 'poster_qr') {
  await page.goto(`/?source_channel=${channel}`);
  await expect(page.getByTestId('consent-screen')).toBeVisible();
}

export async function acceptConsent(page) {
  await page.getByTestId('consent-checkbox').check();
  await page.getByTestId('consent-start').click();
  await expect(page.getByTestId('chat-screen')).toBeVisible();
}

export async function answer(page, text, expectedDone) {
  await page.getByTestId('message-input').fill(text);
  await page.getByTestId('send-btn').click();
  if (expectedDone) {
    await expect(page.getByTestId('progress-text')).toHaveText(`已收集 ${expectedDone}/7 项`);
  }
}

export async function quickAnswer(page, label, expectedDone) {
  await page.getByTestId('quick-reply').filter({ hasText: label }).first().click();
  await expect(page.getByTestId('progress-text')).toHaveText(`已收集 ${expectedDone}/7 项`);
}

export async function completeSlots(page) {
  await answer(page, '王小明', 1);
  await answer(page, '1998-05', 2);
  await answer(page, '浦东新区张江镇', 3);
  await quickAnswer(page, '全职', 4);
  await quickAnswer(page, '有电动车', 5);
  await quickAnswer(page, '本周内', 6);
  await quickAnswer(page, '1-3 年', 7);
  await expect(page.getByTestId('stations-card')).toBeVisible();
}

export async function bookFirstStation(page) {
  await page.getByTestId('slot-btn').first().click();
  await expect(page.getByTestId('booking-bar')).toBeVisible();
  await page.getByTestId('booking-confirm').click();
  await expect(page.getByTestId('result-screen')).toBeVisible();
}

export async function openProfile(page) {
  await page.getByTestId('open-profile').first().click();
  await expect(page.getByTestId('profile-screen')).toBeVisible();
}
