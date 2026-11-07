# #1807 交付说明（任务 2/5：求职者端 H5）

> 验收口径：**本地可复跑证据为准**。本轮不启用 GitHub Actions，不声称任何 CI run 号。

## 1. 交付物

| 项 | 值 |
|---|---|
| 远端仓库 | https://github.com/AWKN-Lab/clawhunt-1807-delivery |
| 分支 / 基线 SHA（本轮更正前） | `master` / `c0218be81935d8d109e13dad42bf4aee8fe250fb` |
| 远端文件数 | 61（不含 `.github/workflows/*`；本轮新增本说明） |
| 本地工程 | `D:\AWKN-Lab\clawhunt\work\1807\repo` |
| 技术栈 | React 18 + Vite（H5）+ FastAPI mock（契约 v1）+ Playwright；全部 MIT / Apache-2.0 / BSD |

## 2. 启动与复跑（README 三步法）

```powershell
npm ci
python -m venv .venv; .venv\Scripts\python -m pip install -r requirements.txt
.\run.ps1
```

- 环境注记：本机 `python` 3.10 存在 `socketpair` 阻塞，按 README 用 **Python 3.12** 创建 `.venv`；命令形式与 README 一致。
- 一键验收：`.\verify.ps1` → **VERIFY PASS，exit 0**
- 启动后：mock `:8001` health 200；H5 `:5173` 200。

## 3. 本地实测证据

| 项 | 实测结果 |
|---|---|
| 单元测试 | **41 passed / 41**，exit 0 |
| 构建 | exit 0，`dist` 3 files / **178,965 bytes** |
| Playwright E2E | **8 passed / 8**（主流程 / 同意门 / AI 标识 / 自助四项 / 布局 / 断网恢复 / 输入） |
| 截图 | 4 张：375×809、390×844、414×896、375×1406（150% 字体） |
| 三宽度横向溢出 | 375 / 390 / 414 均 `scrollWidth <= clientWidth + 1` |
| 断网 10 秒恢复 | 进度 3/7 保留 → 恢复 → 续答到 4/7 |
| 撤回授权 | localStorage 两会话键清空、旧 token 410 |
| 干净环境 | `npm ci` exit 0（65 packages）；pip exit 0；`run.ps1` → mock ready / H5 ready |
| 一键验收摘要 | `conclusion: PASS`，`exit_code: 0`（`receipt/verify.json`） |
| 容器一键起（2026-11-07 补测） | **PASS**：`docker compose up --build --abort-on-container-exit` → UP_EXIT=0；mock/web 均启动，停止后退出码 0/0 |

### 3b. 容器路径实测（2026-11-07 补测）

执行目录：`D:\AWKN-Lab\clawhunt\work\1807\repo`（`delivery\1807` 目录只含交付说明与 CI 附件，compose 定义位于工程仓库）。

```text
docker compose config                                 → exit 0
docker compose up --build --abort-on-container-exit   → UP_EXIT=0
GET http://127.0.0.1:8001/api/v1/health                → 200 {"status":"ok","service":"clawhunt-1807-mock","ai_banner":"本服务由 AI 提供 · 可随时转人工","consent_version":"v1.0","stations":3}
GET http://127.0.0.1:8080/                            → 200，index 含 <div id="root">
GET http://127.0.0.1:8080/api/v1/health               → 200（nginx /api 反代到 mock）
docker compose stop 后各容器退出码                     → mock=0 / web=0
```

运行环境：WSL2 Ubuntu 26.04 内 Docker Engine 29.1.3（`apt install docker.io`）+ Docker Compose v2.40.3；`docker version` Client/Server 均 29.1.3，API 1.52（linux/amd64）；`docker run --rm hello-world` exit 0。

证据文件（仓库相对路径）：

- `receipt/verify.json`（含 pytest/Playwright 统计、dist 字节数、截图尺寸与 sha256）
- `receipt/pytest.xml`、`receipt/logs/*.log`
- `evidence/screenshots/*.png`、`evidence/playwright.json`、`evidence/perf.json`
- `docs/AC-MAP.md`、`docs/EVIDENCE.md`、`docs/USABILITY-GATE-1807.md`
- `e2e/*.spec.js`、`tests/`

## 4. AC 状态：8/8

| AC | 状态 | 说明 |
|---|---|---|
| AC0 三个服务可启动 / 契约可用 | PASS | pytest 41 + Playwright webServer 实测 |
| AC1 全链路（入口→同意→7 项→政策→站点→预约→结果） | PASS | `e2e/full-flow.spec.js` |
| AC2 同意门与回传字段 | PASS | 不勾选不能开始、拒绝出口、`consent_version/at` |
| AC3 每屏 AI 标识 | PASS | 逐屏断言 + 滚动后可见 |
| AC4 个人信息自助四项 + 撤回清缓存 | PASS | 查看/更正/下载/撤回 + `tel:` |
| AC5 三宽度 / 150% 字体 | PASS | 4 张截图 + 无横向溢出断言 |
| AC6 断网 10 秒不丢进度 | PASS | `e2e/offline.spec.js` |
| AC7 交付闭环（README 三步 / verify / 容器与 CI） | PASS | README 与 verify 实测通过；容器已真实运行通过（见 3b）；CI 未推送仍如实标注 |

## 5. 必须如实写的限制

1. **GitHub Actions 未运行**：workflow 未推送，没有任何 run 号；所有数字来自本机执行。
2. **容器已真实运行（GitHub Actions 仍未运行）**：2026-11-07 在 WSL2 Ubuntu 26.04 内安装 Docker Engine 29.1.3 + Compose v2.40.3，`docker compose up --build` 启动 mock/web 并验证 mock 健康、H5 200 与 `/api` 反代；仍**没有**任何 CI run 号。
3. **闸门口径有两个数字，不要混读**：
   - 仓库内 `docs/USABILITY-GATE-1807.md` 定义的五闸（安装 / 一键复跑 / 产出可核 / README 三步 / 无隐藏前置）= **5/5 PASS**；
   - 项目标准口径（含容器闸）= **5/5**（容器闸 2026-11-07 实测通过）。
4. **AC 8/8**：AC7 的容器路径已实测通过，CI 未推送部分仍如实标注。
5. **Linux/macOS** 命令已写入 README，但本机无该环境，**未实跑**。
6. **首屏性能**只在本地 Vite dev 测得（DCL 约 87ms），**不能外推为 4G 现场结论**；4G ≤2s 需真机/弱网复测。
7. **微信小程序**为加分项，未包含在本仓库。
8. mock 为进程内内存，不接真实 Agent / 大模型 / 短信 / 保险箱；合成数据，无真实个人信息。

## 6. 未启用的 CI 附件

`D:\AWKN-Lab\clawhunt\work\delivery\1807\workflows\`
- `ci.yml`、`container.yml`：**已备好、未推送、未启用**（说明见同目录 `README.md`）。

## 7. 平台侧

- 本轮**未发送任何 PATCH、未新增投标**；#1807/13433 的投标文案维持现状。

## 8. 复现环境（容器路径）

本机 Docker Desktop 4.98.0 虽已安装，但其 daemon 在非交互会话中启动后即被回收（`com.docker.service` 为 Stopped，`\\.\pipe\dockerDesktopLinuxEngine` 不存在），因此容器验证改用 **WSL2 内的 Docker Engine**，不需要 Docker Desktop 商业授权，也不需要 UAC。

| 项 | 实测值 |
|---|---|
| 宿主 | Windows 10.0.26200.9711；Hyper-V hypervisor present |
| WSL | WSL 2.6.3.0（内核 6.6.87.2-1），默认发行版 Ubuntu、版本 2 |
| 发行版 | Ubuntu 26.04 LTS（PID1 = systemd，cgroup v2 可用） |
| 引擎 | Docker Engine **29.1.3**（`apt install docker.io`），containerd 2.2.2 |
| Compose | Docker Compose **v2.40.3**（`docker-compose-v2`） |
| API | Client/Server 29.1.3，API 1.52，linux/amd64 |
| 冒烟 | `docker run --rm hello-world` → `Hello from Docker!`，exit 0 |

### 8.1 安装命令（WSL 内，无需 UAC）

```bash
sudo apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y docker.io docker-compose-v2
sudo systemctl enable --now docker
```

### 8.2 镜像加速的坑

- 现象：Docker Hub 直连拉取 `hello-world` 报 `registry-1.docker.io: i/o timeout`；`node:20-alpine` / `nginx:1.27-alpine` 同样会被卡住。
- 处理：写入 `/etc/docker/daemon.json` 后 `sudo systemctl restart docker`：

```json
{"registry-mirrors":["https://docker.m.daocloud.io","https://docker.1ms.run","https://docker.xuanyuan.me"]}
```

- 其他坑：PyPI 直连速度约 20–30 kB/s，`pip install` 阶段会明显拉长构建时间，属网络环境因素，不是 Dockerfile/compose 定义问题；换到正常网络或配置 PyPI 镜像即可。
- 镜像加速只影响本机拉取基础镜像，不写进任何交付物，也不影响 CI。

### 8.3 `UP_EXIT` 判定方式

`mock` / `web` 是长驻服务，`docker compose up --build --abort-on-container-exit` 不会自行结束。判定步骤：

```bash
# 1) 后台起栈，退出码写入日志
docker compose up --build --abort-on-container-exit > /tmp/up.log 2>&1; echo UP_EXIT=$? >> /tmp/up.log
# 2) 等健康
curl -fsS http://127.0.0.1:8001/api/v1/health
curl -fsS -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/
# 3) 主动 stop 触发 abort，再读 UP_EXIT
docker compose stop
grep UP_EXIT /tmp/up.log
# 4) 每个容器的退出码（必须在 down 之前取）
docker compose ps -aq | xargs -r docker inspect --format 'name={{.Name}} exit={{.State.ExitCode}} status={{.State.Status}}'
# 5) 清理
docker compose down -v
```

本次结果：`UP_EXIT=0`，`mock=0 / web=0`。构建失败时 `UP_EXIT` 非 0 且完整日志在 `/tmp/up.log`，需按日志定位，不要只报“失败”。

### 8.4 复现路径差异

`delivery\1807` 目录只放交付说明与 CI 附件，**compose 与 Dockerfile 在工程仓库** `D:\AWKN-Lab\clawhunt\work\1807\repo`，容器命令必须在工程目录执行。
