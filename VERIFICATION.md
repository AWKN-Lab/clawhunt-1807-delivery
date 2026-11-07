# VERIFICATION · ClawHunt #1807（任务 2/5：求职者端 H5）

- 仓库：`D:\AWKN-Lab\clawhunt\work\1807\repo`
- 验证时间：2026-11-07（Asia/Shanghai）
- 结论：`.\verify.ps1` → **PASS**，exit code **0**

## 1. 验证命令与结果

| # | 命令 | 输入 | 期望 | 实际 | 结论 |
| --- | --- | --- | --- | --- | --- |
| 1 | `.venv\Scripts\python -m pytest -q tests` | `tests/`（41 个） | 全部通过 | `41 passed, 1 warning in 0.65s` | PASS |
| 2 | `npm run build` | `src/` | 构建成功、产物 3 文件 | `40 modules transformed`，`built in 648ms`，`dist` 3 files / 178,965 bytes | PASS |
| 3 | `npx playwright test` | `e2e/`（8 条） | 8/8 通过 | `8 passed (25.6s)` | PASS |
| 4 | `.\verify.ps1` | 上述 1–3 + 证据检查 | 全 PASS、exit 0 | `conclusion: PASS`，`VERIFY PASS (exit 0)` | PASS |

`receipt/verify.json` 关键字段：

```json
{
  "conclusion": "PASS",
  "exit_code": 0,
  "steps": [
    {"name": "pytest", "exit_code": 0, "summary": "41 passed / 41 total (failures=0, errors=0, skipped=0)"},
    {"name": "build", "exit_code": 0},
    {"name": "playwright", "exit_code": 0, "summary": "8 passed / 8 total (unexpected=0, flaky=0, skipped=0)"},
    {"name": "evidence-artifacts", "exit_code": 0, "summary": "screenshots=4, perf=yes"}
  ],
  "dist": {"files": 3, "bytes": 178965}
}
```

凭据：`receipt/verify.json`，`sha256:9041dde990cde25754b5de2a94dd05c87124ebd4ae3733edd54639a6ead9596f`（同时写入 `receipt/verify.sha256`），`git_commit=0d4f308`。

## 2. 覆盖映射

| AC | 测试 | 结果 |
| --- | --- | --- |
| AC0 | `tests/test_api.py` 27 + `tests/test_contract.py` 9 + `tests/test_repo_layout.py` 5 | PASS |
| AC1 | `e2e/full-flow.spec.js` 1 条 | PASS |
| AC2 | `e2e/consent.spec.js` 1 条 | PASS |
| AC3 | `e2e/ai-banner.spec.js` 2 条 | PASS |
| AC4 | `e2e/self-service.spec.js` 1 条 | PASS |
| AC5 | `e2e/layout.spec.js` 1 条（三宽度 + 150%） | PASS |
| AC6 | `e2e/offline.spec.js` 1 条（断网 10 秒） | PASS |
| 语音降级 | `e2e/chat-input.spec.js` 1 条 | PASS |

## 3. 变异自证（红/绿）

目的：证明 AC 相关断言不是「摆设」，改坏实现后测试必须变红；撤销后必须变绿。

### 3.1 变异（临时清空政策条款出处）

对 `mock/agent.py` 的 `POLICY_ENTRIES[0]["sources"]` 做临时修改：

```diff
-        "sources": [
-            {
-                "title": "站点用工政策摘要",
-                "reference": "POL-1807 §3.2",
-                "updated_at": "2026-06-30",
-            }
-        ],
+        "sources": [],
```

命令：

```powershell
.venv\Scripts\python -m pytest -q tests/test_api.py::test_policy_hit_has_sources_and_disclaimer
```

**红色输出（预期失败）**：

```text
        assert data["card"]["type"] == "policy"
>       assert data["card"]["sources"]
E       assert []

tests\test_api.py:126: AssertionError
=========================== short test summary info ============================
FAILED tests/test_api.py::test_policy_hit_has_sources_and_disclaimer - assert []
1 failed, 1 warning in 0.14s
EXIT=1
```

### 3.2 撤销变异

```powershell
Copy-Item receipt\_agent_backup.py mock\agent.py -Force
.venv\Scripts\python -m pytest -q tests/test_api.py::test_policy_hit_has_sources_and_disclaimer
```

**绿色输出（恢复后通过）**：

```text
1 passed, 1 warning in 0.05s
EXIT=0
```

恢复确认：`mock\agent.py:59` 重新包含 `"reference": "POL-1807 §3.2"`。

结论：该 AC 断言确实能捕获「政策出处丢失」回归，变异自证 **PASS（红→绿）**。

## 4. 未验证 / 边界（不冒充 PASS）

| 项 | 状态 | 原因 |
| --- | --- | --- |
| Docker 容器本机实跑 | **已实跑 PASS** | 2026-11-07 在 WSL2 Ubuntu 26.04 + Docker Engine 29.1.3 + Compose v2.40.3 上执行；`UP_EXIT=0`，mock/web 退出码 0/0，健康与 `/api` 反代均 200 |
| GitHub Actions 实际运行 | **未运行** | 仓库未推送、不建远程；`ci.yml` / `container.yml` 仅静态存在 |
| 4G 首屏 ≤2s | **未验证** | `evidence/perf.json` 是本地 Vite dev 的 87 ms，不代表 4G 现场 |
| iOS/Android 真机 | **未验证** | 仅 Playwright Chromium 三视口 + 150% 字体模拟 |
| 微信小程序 | **未做** | 加分项，本仓库不含 Taro 小程序 |
| Linux/macOS 三步命令 | **未实跑** | 本机无对应环境；命令已写入 README |

## 5. 复跑

```powershell
.\verify.ps1
```

验收凭据会自动重写 `receipt/verify.json` 与 `receipt/verify.sha256`；证据截图重写 `evidence/screenshots/*.png`。
