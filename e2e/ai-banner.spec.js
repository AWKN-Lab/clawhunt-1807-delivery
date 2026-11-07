// e2e/ai-banner.spec.js：AC3 AI 身份标识逐屏/逐步可见
import { test, expect } from '@playwright/test';
import { resetMock, gotoEntry, acceptConsent, answer, quickAnswer, completeSlots, bookFirstStation, openProfile } from './helpers.js';

const BANNER = '本服务由 AI 提供 · 可随时转人工';

test.beforeEach(async ({ request }) => {
  await resetMock(request);
});

test('AC3 AI banner 在同意页/每一步对话/站点卡/结果页/自助页均可见', async ({ page }) => {
  await gotoEntry(page, 'poster_qr');
  await expect(page.getByTestId('ai-banner')).toHaveText(BANNER);

  await acceptConsent(page);
  await expect(page.getByTestId('ai-banner')).toHaveText(BANNER);
  await expect(page.getByTestId('ai-banner')).toBeVisible();

  for (const [index, text] of ['王小明', '1998-05', '浦东新区张江镇'].entries()) {
    await answer(page, text, index + 1);
    await expect(page.getByTestId('ai-banner')).toBeVisible();
    await expect(page.getByTestId('ai-banner')).toHaveText(BANNER);
  }
  for (const [index, label] of ['全职', '有电动车', '本周内', '1-3 年'].entries()) {
    await quickAnswer(page, label, index + 4);
    await expect(page.getByTestId('ai-banner')).toHaveText(BANNER);
  }
  await expect(page.getByTestId('stations-card')).toBeVisible();
  await expect(page.getByTestId('ai-banner')).toBeVisible();

  await bookFirstStation(page);
  await expect(page.getByTestId('result-screen')).toBeVisible();
  await expect(page.getByTestId('ai-banner')).toHaveText(BANNER);

  await openProfile(page);
  await expect(page.getByTestId('ai-banner')).toHaveText(BANNER);
  await expect(page.getByTestId('ai-banner')).toBeVisible();
});

test('AC3 对话中政策卡与结果页仍保留 banner（不因滚动/吸顶丢失）', async ({ page }) => {
  await gotoEntry(page, 'poster_qr');
  await acceptConsent(page);
  await completeSlots(page);
  await page.getByTestId('message-input').fill('工资怎么结算？');
  await page.getByTestId('send-btn').click();
  await expect(page.getByTestId('policy-card')).toBeVisible();
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await expect(page.getByTestId('ai-banner')).toBeVisible();
  await expect(page.getByTestId('ai-banner')).toHaveText(BANNER);
  await bookFirstStation(page);
  await expect(page.getByTestId('ai-banner')).toHaveText(BANNER);
});
