// e2e/chat-input.spec.js：语音不可用时回退文字输入（必须实现的降级路径）
import { test, expect } from '@playwright/test';
import { resetMock, gotoEntry, acceptConsent, answer } from './helpers.js';

test.beforeEach(async ({ request }) => {
  await resetMock(request);
});

test('语音识别不可用 → 提示并回退文字输入，随后可正常作答', async ({ page }) => {
  await page.addInitScript(() => {
    // 模拟不支持 SpeechRecognition 的浏览器（如部分 Android WebView / 无权限环境）
    Object.defineProperty(window, 'SpeechRecognition', { value: undefined, configurable: true });
    Object.defineProperty(window, 'webkitSpeechRecognition', { value: undefined, configurable: true });
  });
  await gotoEntry(page, 'poster_qr');
  await acceptConsent(page);

  const hasSpeech = await page.evaluate(
    () => Boolean(window.SpeechRecognition || window.webkitSpeechRecognition),
  );
  expect(hasSpeech).toBeFalsy();

  await page.getByTestId('voice-btn').click();
  await expect(page.getByTestId('voice-hint')).toBeVisible();
  await expect(page.getByTestId('voice-hint')).toContainText('回退为文字输入');
  await expect(page.getByTestId('message-input')).toBeEnabled();
  await expect(page.getByTestId('message-input')).toBeFocused();

  await answer(page, '王小明', 1);
  await expect(page.getByTestId('progress-text')).toHaveText('已收集 1/7 项');
});
