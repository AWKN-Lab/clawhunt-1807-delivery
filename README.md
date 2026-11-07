# ClawHunt #1807 · 骑手招聘 Agent 化信息收集平台（任务 2/5：求职者端 H5）

一个可运行的求职者端 H5 + FastAPI mock 服务，覆盖「渠道入口 → 告知同意 → 7 项报名 → 政策问答 → 站点推荐 → 选时段预约 → 结果页 → 个人信息自助」全链路。

- 技术栈：React 18 + Vite（手写 CSS，无重 UI 库）+ FastAPI + uvicorn
- 数据：全部为合成数据（`poster_qr`、`王小明`、`13900000000`），不含真实个人信息
- 小程序：**未包含**（Taro 同源小程序为加分项，本仓库不为主交付增加风险）
- 依赖许可：React/Vite/FastAPI/uvicorn/pytest/httpx/Playwright 均为 MIT / Apache-2.0 / BSD 类许可，无 GPL/AGPL

## 快速开始（3 条命令）

前置：Node.js ≥ 18、Python 3.12（契约要求；本机实测 Python 3.12.13 / Node 24）。首次需联网下载 npm/pip 依赖与 Playwright 浏览器。

> 若本机 `python` 不是 3.12（例如 3.10），请用 `uv venv --python 3.12 .venv` 或已安装的 3.12 解释器创建 `.venv`；本仓库已提供 `.venv` 时，`run.ps1` / `verify.ps1` 会直接复用。Windows 上 3.10 的 `socket.socketpair()` 在本机实测会阻塞，故不作为验收环境。

### Windows（PowerShell）

```powershell
npm ci
python -m venv .venv; .venv\Scripts\python -m pip install -r requirements.txt
.\run.ps1
```

### Linux / macOS

```bash
npm ci
python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt
./run.sh
```

启动后终端会打印：

```text
[dev] mock ready: http://127.0.0.1:8001/api/v1/health
[dev] H5 ready: http://127.0.0.1:5173/?source_channel=poster_qr
服务已就绪，按 Ctrl+C 停止。
```

浏览器打开 **http://127.0.0.1:5173/?source_channel=poster_qr**，按以下路径走：

1. 阅读告知同意页 → 勾选「我已阅读并同意」→「同意并开始」
2. 逐项回答：`王小明` → `1998-05` → `浦东新区张江镇` → 点「全职」→「有电动车」→「本周内」→「1-3 年」
3. 输入 `站点有住宿吗？` 查看政策回答卡（含出处标签与免责声明）
4. 在站点卡选一个时段 → 点「预约」→ 结果页可导航、改约、取消、看到站须知、拨站长虚拟号
5. 点「我的信息」可查看/更正/下载副本/撤回授权并删除

真实回包示例（`curl http://127.0.0.1:8001/api/v1/health`）：

```json
{"status":"ok","service":"clawhunt-1807-mock","ai_banner":"本服务由 AI 提供 · 可随时转人工","consent_version":"v1.0","stations":3}
```

## 一键验收

```powershell
.\verify.ps1   # Windows
./verify.sh    # Linux / macOS
```

`verify.ps1` 依次执行 `pytest` → `npm run build` → `npx playwright test`，并把结果写入 `receipt/verify.json`（含每步 exit code、耗时、pytest/Playwright 统计、截图尺寸与 sha256）。任一环节失败即 exit 非 0（fail-closed）。

单独跑：

```powershell
.venv\Scripts\python -m pytest -q          # mock 单测 + 契约测试
npm run build                              # 前端构建
npx playwright test                        # E2E（自动起 mock + H5）
```

首次跑 E2E 前需安装浏览器：

```powershell
npx playwright install chromium
```

> 若本机 `PLAYWRIGHT_BROWSERS_PATH` 指向不存在的盘符（会导致 `ENOENT mkdir '\\?'`），先清空该变量再安装：
> `$env:PLAYWRIGHT_BROWSERS_PATH=''`（`playwright.config.js` 已对失效路径做回退）。

## 服务与端口

| 服务 | 地址 | 说明 |
| --- | --- | --- |
| H5 | http://127.0.0.1:5173 | Vite dev，`/api` 代理到 8001 |
| mock API | http://127.0.0.1:8001/api/v1 | FastAPI，OpenAPI 见 http://127.0.0.1:8001/docs |
| OpenAPI 快照 | `docs/openapi.json` | `python scripts/export_openapi.py` 生成 |
| 容器 H5 | http://127.0.0.1:8080 | `docker compose up -d --build`（nginx 静态托管 + /api 反代） |

## 目录结构

```text
repo/
├─ src/                     React 前端（App / 同意页 / 对话页 / 结果页 / 自助页 / 卡片 / 进度 / banner）
├─ mock/                    FastAPI mock（app / agent 槽位 / state / vault / security）
├─ tests/                   pytest：test_api.py / test_contract.py / test_repo_layout.py
├─ e2e/                     Playwright：全链路 / 同意 / AI banner / 自助 / 布局 / 断网 / 语音回退
├─ scripts/                 dev.mjs（一键起双服务）/ verify.py（验收编排）/ export_openapi.py
├─ docs/                    AC-MAP / EVIDENCE / USABILITY-GATE-1807 / openapi.json
├─ evidence/screenshots/    375 / 390 / 414 / 150% 字体截图
├─ receipt/verify.json      一键验收凭据（自动生成）
├─ Dockerfile                mock 镜像
├─ Dockerfile.web            H5 镜像（Node 构建 + nginx）
├─ docker-compose.yml        mock + web
├─ verify.ps1 / verify.sh    一键验收入口
├─ run.ps1 / run.sh          一键启动入口
└─ VERIFICATION.md           验证记录（含变异自证）
```

## 契约与 mock 边界

- REST 前缀 `/api/v1`，错误体统一 `{code, message}`；求职者端用 Bearer 会话令牌；员工端 mock 提供 Bearer JWT（`/api/v1/admin/token`）。
- 已实现：告知同意（版本/时间/保存期限）、Agent 会话与 7 槽位、未成年终止、政策问答（出处 + 免责声明）、站点/时段、预约/改约/取消、个人信息查看/更正/导出/撤回、vault tokenize/detokenize（权限 + 审计）、outbox 事件 HMAC-SHA256。
- 明确为 mock：Agent 引擎、保险箱服务、大模型、短信/电话；本仓库不接真实模型，不产生真实个人信息。
- 事件类型：`candidate.created / candidate.updated / candidate.completed / booking.created / booking.cancelled / handoff.requested`。

## 已知限制

- 微信小程序打包未包含（加分项，非必需）。
- 容器已在 WSL2 Docker Engine 29.1.3 + Compose v2.40.3 上实跑（UP_EXIT=0，mock/web 退出码 0/0）；GitHub Actions 未推送、未实际运行，无 CI run 号。
- 首屏耗时是本地 Vite dev 环境测量（见 `evidence/perf.json`），不代表 4G 现场。
- mock 使用进程内内存，重启即清空；生产需替换为 PostgreSQL + 真实 Agent/保险箱服务。
- CI workflow 已编写，但尚未推送到远程，未在 GitHub 上实际运行。

## 许可

仅使用 MIT / Apache-2.0 / BSD / PostgreSQL 兼容依赖。合成演示数据可自由用于评审。
