# USABILITY GATE · ClawHunt #1807

五闸判定标准：每闸给出「实测命令 → 实测结果 → PASS/FAIL」。未实测的项不写 PASS。

## 闸 1｜干净环境安装可跑

**实测命令**（在 `D:\AWKN-Lab\clawhunt\work\1807\cleancheck`，从仓库复制并排除 `node_modules/.venv/dist/evidence/receipt/test-results`）：

```powershell
npm ci
& "<Python 3.12 解释器>" -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.\run.ps1
```

**实测结果**：

```text
npm ci → added 65 packages in 2s，exit 0
pip install → exit 0，deps ok
run.ps1 → [dev] mock ready / [dev] H5 ready
health → 200 {"status":"ok",...}
H5 → 200，699 bytes，含 <div id="root">
```

**PASS**（环境偏差：本机 `python` 为 3.10 且 `socketpair` 阻塞，改用契约要求的 Python 3.12；README 已写明）。

## 闸 2｜一条命令复跑

**实测命令**：

```powershell
.\verify.ps1
```

**实测结果**：

```text
PASS pytest              exit=0 41 passed / 41 total
PASS build               exit=0
PASS playwright          exit=0 8 passed / 8 total
PASS evidence-artifacts  exit=0 screenshots=4, perf=yes
conclusion: PASS
VERIFY PASS (exit 0)
```

**PASS**。任一环节失败会写 FAIL 并返回 exit 非 0（fail-closed，见 `scripts/verify.py` 的 `FAIL-CLOSED` 分支）。

## 闸 3｜示例产出可核

**实测命令**：

```powershell
Get-Content receipt\verify.json
Get-ChildItem evidence\screenshots
```

**实测结果**：

- `receipt/verify.json`：`conclusion=PASS`、`exit_code=0`、4 步状态/耗时、pytest 与 Playwright 统计、dist 3 files / 178,965 bytes、4 张截图尺寸/字节、`sha256` 凭据。
- `evidence/screenshots/`：375×809、390×844、414×896、375×1406（150% 字体）四张 PNG，字节数写入 receipt。
- `evidence/perf.json`：本地 dev DCL 87 ms，明确标注「不代表 4G 现场」。

**PASS**。

## 闸 4｜README 三步可照抄

**实测命令**（Windows 分支，逐条照 README 复制）：

```powershell
npm ci
python -m venv .venv; .venv\Scripts\python -m pip install -r requirements.txt
.\run.ps1
```

**实测结果**：

- `npm ci` exit 0；venv/pip exit 0；`.\run.ps1` 后 health 200、H5 200。
- 例外：本机 `python` 是 3.10（`socketpair` 阻塞），第 2 条按 README 注记改用 3.12 解释器创建 `.venv`；命令形式与 README 一致。

**PASS（Windows）**。Linux/macOS 等价命令（`python3 -m venv .venv && .venv/bin/python ...`、`./run.sh`）已写入 README，但本机无 Linux/macOS 环境，**未实跑**（如实标注，不宣称已通过）。

## 闸 5｜无隐藏前置

**核查项与结果**：

| 检查 | 结果 |
| --- | --- |
| 必需环境变量 | 无。`CH1807_PYTHON`、`CH1807_BASE_URL` 均为可选覆盖；默认自动发现 `.venv` / `python` |
| 数据库 / 外部服务 | 无。mock 为进程内内存；不接真实 Agent/大模型/短信/保险箱 |
| 密钥 / 账号 | 无。HMAC/JWT secret 为 mock 固定值；合成数据 |
| 端口 | 8001（mock）、5173（H5）、8080（容器 H5）；README「服务与端口」已写明 |
| 浏览器 | 需 `npx playwright install chromium`；README 已写明，并对失效 `PLAYWRIGHT_BROWSERS_PATH` 给出回退 |
| 网络 | 首次 `npm ci` / `pip install` / Playwright 浏览器下载需联网；之后离线可跑 |

**PASS**。

## 补充闸（项目标准口径）｜容器一键起

**实测命令**（2026-11-07，WSL2 Ubuntu 26.04 + Docker Engine 29.1.3 + Compose v2.40.3）：

```text
cd /mnt/d/AWKN-Lab/clawhunt/work/1807/repo
docker compose config                                 → exit 0
docker compose up --build --abort-on-container-exit   → UP_EXIT=0
GET http://127.0.0.1:8001/api/v1/health                → 200 {"status":"ok","service":"clawhunt-1807-mock",...}
GET http://127.0.0.1:8080/                            → 200，含 <div id="root">
GET http://127.0.0.1:8080/api/v1/health               → 200（nginx 反代到 mock）
docker compose stop 后退出码                           → mock=0 / web=0
```

**PASS**。项目标准口径（含容器闸）由此前 4/5 更新为 **5/5**；仓库内五闸仍为 5/5。

## 汇总

| 闸 | 结论 |
| --- | --- |
| 1 干净环境安装可跑 | PASS |
| 2 一条命令复跑 | PASS |
| 3 示例产出可核 | PASS |
| 4 README 三步可照抄 | PASS（Windows）；Linux/macOS 未实跑 |
| 5 无隐藏前置 | PASS |
| 容器一键起（项目标准口径） | PASS（2026-11-07 实测） |
