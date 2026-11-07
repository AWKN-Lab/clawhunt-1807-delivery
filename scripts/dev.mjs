// scripts/dev.mjs：一条命令同时启动 mock（8001）+ H5（5173）
import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import path from 'node:path';
import process from 'node:process';

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1')), '..');
const IS_WIN = process.platform === 'win32';
const PREVIEW = process.argv.includes('--preview');
const MOCK_URL = 'http://127.0.0.1:8001/api/v1/health';
const H5_URL = 'http://127.0.0.1:5173/';
const CHILDREN = [];

function candidates() {
  const list = [];
  if (process.env.CH1807_PYTHON) list.push(process.env.CH1807_PYTHON);
  list.push(path.join(ROOT, '.venv', IS_WIN ? 'Scripts/python.exe' : 'bin/python'));
  list.push(IS_WIN ? 'python' : 'python3');
  list.push('python');
  return list;
}

function findPython() {
  for (const item of candidates()) {
    if (item.includes(path.sep) && !existsSync(item)) continue;
    return item;
  }
  return IS_WIN ? 'python' : 'python3';
}

async function reachable(url, timeoutMs = 40000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    try {
      const response = await fetch(url);
      if (response.ok) return true;
    } catch {
      // not ready yet
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  return false;
}

async function alreadyUp(url) {
  try {
    const response = await fetch(url);
    return response.ok;
  } catch {
    return false;
  }
}

function start(command, args, name) {
  const child = spawn(command, args, {
    cwd: ROOT,
    stdio: 'inherit',
    env: process.env,
    shell: false,
  });
  child.on('exit', (code) => {
    if (code !== 0) console.error(`[dev] ${name} exited with code ${code}`);
  });
  CHILDREN.push(child);
  return child;
}

function shutdown() {
  for (const child of CHILDREN) {
    if (child && !child.killed) {
      try {
        if (IS_WIN) spawn('taskkill', ['/pid', String(child.pid), '/T', '/F'], { stdio: 'ignore' });
        else child.kill('SIGTERM');
      } catch {
        // ignore
      }
    }
  }
  CHILDREN.length = 0;
}

process.on('SIGINT', () => {
  shutdown();
  process.exit(0);
});
process.on('SIGTERM', () => {
  shutdown();
  process.exit(0);
});

if (process.argv.includes('--help')) {
  console.log('用法: node scripts/dev.mjs [--preview]');
  console.log('  mock: http://127.0.0.1:8001/api/v1/health');
  console.log('  H5:   http://127.0.0.1:5173/?source_channel=poster_qr');
  process.exit(0);
}

const python = findPython();
console.log(`[dev] python: ${python}`);

if (await alreadyUp(MOCK_URL)) {
  console.log('[dev] mock 已在运行，复用 127.0.0.1:8001');
} else {
  start(
    python,
    ['-m', 'uvicorn', 'mock.app:app', '--host', '127.0.0.1', '--port', '8001'],
    'mock',
  );
  if (!(await reachable(MOCK_URL))) {
    console.error('[dev] mock 启动失败：40 秒内 /api/v1/health 未就绪');
    shutdown();
    process.exit(1);
  }
  console.log('[dev] mock ready: http://127.0.0.1:8001/api/v1/health');
}

if (await alreadyUp(H5_URL)) {
  console.log('[dev] H5 已在运行，复用 127.0.0.1:5173');
} else {
  const viteBin = path.join(ROOT, 'node_modules', 'vite', 'bin', 'vite.js');
  const viteArgs = PREVIEW
    ? [viteBin, 'preview', '--host', '127.0.0.1', '--port', '5173', '--strictPort']
    : [viteBin, '--host', '127.0.0.1', '--port', '5173', '--strictPort'];
  start(process.execPath, viteArgs, 'vite');
  if (!(await reachable(H5_URL))) {
    console.error('[dev] H5 启动失败：40 秒内 127.0.0.1:5173 未就绪（是否缺少 npm ci？）');
    shutdown();
    process.exit(1);
  }
  console.log('[dev] H5 ready: http://127.0.0.1:5173/?source_channel=poster_qr');
}

console.log('\n服务已就绪，按 Ctrl+C 停止。');
setInterval(() => {}, 1 << 30);
