// src/storage.js：会话与进度持久化（键名固定，断网恢复靠它；撤回授权时清空）
export const KEYS = {
  session: 'ch1807.session',
  progress: 'ch1807.progress',
};

export function readJSON(key, fallback = null) {
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

export function writeJSON(key, value) {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // 隐私模式下 localStorage 可能不可写：不阻断主流程
  }
}

export function saveProgress(progress) {
  writeJSON(KEYS.progress, progress);
}

export function clearRegistration() {
  try {
    window.localStorage.removeItem(KEYS.session);
    window.localStorage.removeItem(KEYS.progress);
  } catch {
    // ignore
  }
}
