// src/components/Banner.jsx：AI 身份标识（每一屏可见）+ 离线提示
import { useEffect, useState } from 'react';

export const AI_BANNER_TEXT = '本服务由 AI 提供 · 可随时转人工';

export function useOnlineStatus() {
  const [online, setOnline] = useState(() => (typeof navigator === 'undefined' ? true : navigator.onLine));
  useEffect(() => {
    const onUp = () => setOnline(true);
    const onDown = () => setOnline(false);
    window.addEventListener('online', onUp);
    window.addEventListener('offline', onDown);
    return () => {
      window.removeEventListener('online', onUp);
      window.removeEventListener('offline', onDown);
    };
  }, []);
  return online;
}

export default function AiBanner() {
  const online = useOnlineStatus();
  return (
    <>
      <div className="ai-banner" data-testid="ai-banner" role="banner">
        <span className="ai-dot" aria-hidden="true" />
        {AI_BANNER_TEXT}
      </div>
      {!online && (
        <div className="offline-banner" data-testid="offline-banner" role="status">
          网络已断开：进度已保存在本机，恢复网络后会自动续接会话
        </div>
      )}
    </>
  );
}
