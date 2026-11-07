// e2e/layout.spec.js：AC5 375/390/414 无横向溢出 + 系统字体 150% 不错位
import { test, expect } from '@playwright/test';
import { resetMock, gotoEntry, acceptConsent, answer } from './helpers.js';

const VIEWPORTS = [
  { width: 375, height: 667 },
  { width: 390, height: 844 },
  { width: 414, height: 896 },
];

test.beforeEach(async ({ request }) => {
  await resetMock(request);
});

test('AC5 三宽度全页截图 + 无横向溢出；150% 字体关键容器不溢出', async ({ page }) => {
  await gotoEntry(page, 'poster_qr');
  await acceptConsent(page);
  await answer(page, '王小明', 1);
  await answer(page, '1998-05', 2);

  const viewportResults = [];
  for (const size of VIEWPORTS) {
    await page.setViewportSize(size);
    await page.waitForTimeout(250);
    await page.screenshot({
      path: `evidence/screenshots/${size.width}x${size.height}-chat.png`,
      fullPage: true,
    });
    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    const clientWidth = await page.evaluate(() => document.documentElement.clientWidth);
    expect(scrollWidth, `${size.width}x${size.height} 横向溢出`).toBeLessThanOrEqual(clientWidth + 1);
    viewportResults.push({ viewport: `${size.width}x${size.height}`, scrollWidth, clientWidth });
  }

  await page.setViewportSize({ width: 375, height: 667 });
  await page.evaluate(() => {
    document.documentElement.style.fontSize = '150%';
  });
  await page.waitForTimeout(400);

  const overflows = await page.evaluate(() => {
    const selectors = ['.app-shell', '.chat-screen', '.progress', '.composer', '.bubble.bot'];
    return selectors
      .map((selector) => {
        const element = document.querySelector(selector);
        if (!element) return { selector, missing: true };
        return {
          selector,
          scrollWidth: element.scrollWidth,
          clientWidth: element.clientWidth,
          overflow: element.scrollWidth > element.clientWidth + 1,
        };
      })
      .filter((item) => item.missing || item.overflow);
  });
  expect(overflows, `150% 字体溢出: ${JSON.stringify(overflows)}`).toEqual([]);

  const docScroll = await page.evaluate(() => document.documentElement.scrollWidth);
  const docClient = await page.evaluate(() => document.documentElement.clientWidth);
  expect(docScroll).toBeLessThanOrEqual(docClient + 1);

  await page.screenshot({
    path: 'evidence/screenshots/375x667-font150.png',
    fullPage: true,
  });

  console.log('layout results:', JSON.stringify(viewportResults));
});
