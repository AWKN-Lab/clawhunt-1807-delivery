# EVIDENCE · ClawHunt #1807（求职者端 H5）

生成时间：2026-11-07（Asia/Shanghai）。以下命令与输出均来自本机实际执行，未做改写；未能实跑的项目单独标注。

## 0. 本机环境

| 项 | 实测值 |
| --- | --- |
| 操作系统 | Windows |
| Python（验收 venv） | 3.12.13（`.venv\Scripts\python.exe`） |
| Node / npm | v24.14.1 / 11.11.0 |
| Playwright | 1.65.0 |
| Docker CLI | 29.9.2（daemon 不可用） |
| 浏览器 | Playwright chromium（默认缓存；已清空本机失效的 `PLAYWRIGHT_BROWSERS_PATH=G:\ms-playwright`） |

> 环境说明：本机默认 `python` 是 3.10.11，实测其 `socket.socketpair()` / `asyncio.run()` 会阻塞，无法跑 TestClient/uvicorn。按契约要求改用 Python 3.12 创建 `.venv` 后全部通过；README 已写明该前置与替代命令。

## 1. 干净环境安装与启动（README 三步法）

干净副本：`D:\AWKN-Lab\clawhunt\work\1807\cleancheck`（从仓库复制，排除 `node_modules/.venv/dist/evidence/receipt/test-results`）。

### 1.1 `npm ci`

```text
added 65 packages in 2s
7 packages are looking for funding
NPM_EXIT=0
```

### 1.2 创建 venv + 安装 Python 依赖

README 原文命令为 `python -m venv .venv; .venv\Scripts\python -m pip install -r requirements.txt`。本机因 `python` 为 3.10（socketpair 阻塞），等价地用 Python 3.12 解释器执行：

```text
& "C:\Users\10919\AppData\Roaming\uv\python\cpython-3.12-windows-x86_64-none\python.exe" -m venv .venv
.venv\Scripts\python -m pip install -q -r requirements.txt
PIP_EXIT=0
deps ok
```

### 1.3 `.\run.ps1`

```text
[dev] mock ready: http://127.0.0.1:8001/api/v1/health
[dev] H5 ready: http://127.0.0.1:5173/?source_channel=poster_qr
服务已就绪，按 Ctrl+C 停止。

GET http://127.0.0.1:8001/api/v1/health → 200
{"status":"ok","service":"clawhunt-1807-mock","ai_banner":"本服务由 AI 提供 · 可随时转人工","consent_version":"v1.0","stations":3}

GET http://127.0.0.1:5173/ → 200，699 bytes，包含 <div id="root">
```

## 2. 一键验收 `.\verify.ps1`

```text
ClawHunt #1807 · verify（pytest → build → Playwright E2E）
python: D:\AWKN-Lab\clawhunt\work\1807\repo\.venv\Scripts\python.exe (3.12.13)

PASS pytest              exit=0 41 passed / 41 total (failures=0, errors=0, skipped=0)
PASS build               exit=0
PASS playwright          exit=0 8 passed / 8 total (unexpected=0, flaky=0, skipped=0)
PASS evidence-artifacts  exit=0 screenshots=4, perf=yes
conclusion: PASS
receipt: receipt/verify.json (sha256:9041dde990cde25754b5de2a94dd05c87124ebd4ae3733edd54639a6ead9596f)
VERIFY PASS (exit 0)
```

耗时（写入 `receipt/verify.json`）：pytest 1,274 ms；build 1,421 ms；Playwright 26,944 ms。`git_commit=0d4f308`。

### 测试分解（41 个 pytest）

| 文件 | 数量 | 覆盖 |
| --- | --- | --- |
| `tests/test_api.py` | 27 | 健康检查、同意版本/时间/保留期、会话、7 槽位、未成年 `end_minor`、出生格式不推进、政策命中/未命中、转人工、站点、预约/冲突/取消/改约、个人信息与掩码、更正、导出、撤回 410、vault 权限/审计、outbox HMAC、员工 JWT、错误体 |
| `tests/test_contract.py` | 9 | OpenAPI 可访问、必需路径、`/api/v1` 前缀、candidate/station/booking 字段、message shape、错误体、事件枚举、`docs/openapi.json` 与运行时同步 |
| `tests/test_repo_layout.py` | 5 | 必需文件存在、README Windows/Unix 三步命令锁定、verify 编排关键串、compose 服务与端口 |

Playwright 8 条：AC1 全链路、AC2 同意门、AC3 AI banner ×2、AC4 自助四项+撤回、AC5 三宽度+150% 字体、AC6 断网 10 秒、语音不可用回退文字。

### 构建产物

```text
dist/index.html                 484 B
dist/assets/index-DDfkK5He.css  10,412 B  (gzip 2.69 kB)
dist/assets/index-C6r_FJtR.js  168,069 B  (gzip 53.84 kB)
dist 合计：3 files / 178,965 bytes
```

## 3. 截图证据（Playwright 全页 PNG）

| 文件 | 宽度×高度 | 字节 |
| --- | --- | --- |
| `evidence/screenshots/375x667-chat.png` | 375×809 | 37,526 |
| `evidence/screenshots/390x844-chat.png` | 390×844 | 40,389 |
| `evidence/screenshots/414x896-chat.png` | 414×896 | 40,880 |
| `evidence/screenshots/375x667-font150.png` | 375×1,406 | 76,701 |

布局实测：375/390/414 三视口 `scrollWidth == clientWidth`（375/375、390/390、414/414），150% 字体下关键容器无溢出。

## 4. 性能

`evidence/perf.json`：

```json
{
  "metric": "domContentLoadedEventEnd - navigationStart (ms)",
  "value_ms": 86,
  "environment": "本地 Vite dev + mock（不代表 4G 现场）",
  "measured_at": "2026-11-07T03:39:17.821Z"
}
```

结论仅限本地 dev 首屏 86 ms；**不代表 4G 现场 ≤2s 已达标**，该指标需真机/弱网复测。

## 5. 容器与 CI

```text
docker compose config                                   → exit 0
docker compose up --build --abort-on-container-exit     → UP_EXIT=0
GET http://127.0.0.1:8001/api/v1/health                  → 200（mock）
GET http://127.0.0.1:8080/                              → 200，含 <div id="root">
GET http://127.0.0.1:8080/api/v1/health                 → 200（nginx /api 反代）
docker compose stop 后退出码                             → mock=0 / web=0
```

环境：WSL2 Ubuntu 26.04 + Docker Engine 29.1.3 + Compose v2.40.3（宿主 Docker Desktop 4.98.0 daemon 在非交互会话中无法驻留，故改用 WSL 内 Engine；镜像加速与 `UP_EXIT` 判定见 `DELIVERY-NOTES.md` 第 8 节）。

`docker-compose.yml`（mock:8001 + web:8080→80）、`Dockerfile`（python:3.12-slim + healthcheck）、`Dockerfile.web`（node:20-alpine 构建 + nginx:1.27-alpine）均已按上表实跑。`.github/workflows/container.yml`、`ci.yml` 仍是未推送的静态文件，未在 GitHub 实际运行。

## 6. 复跑入口

```powershell
.\verify.ps1                      # Windows 一键验收（fail-closed）
./verify.sh                       # Linux / macOS
.venv\Scripts\python -m pytest -q tests
npm run build
npx playwright test
python scripts/export_openapi.py  # 重新生成 docs/openapi.json
```
