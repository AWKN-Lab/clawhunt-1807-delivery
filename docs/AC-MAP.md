# AC-MAP · ClawHunt #1807（任务 2/5：求职者端 H5）

每条 AC 都给出 **判定性验收方式 → 实现文件 → 可复跑命令 → 证据路径**。本文只记录仓库内可复跑的事实；未实测项在状态栏明确标注。

| AC | 判定性要求 | 验收方式（自动化） | 实现文件 | 可复跑命令 | 证据路径 | 状态 |
| --- | --- | --- | --- | --- | --- | --- |
| AC0 | 三个服务可启动；mock 健康检查、错误体、7 项字段、政策/站点/预约契约真实可用 | pytest：`tests/test_api.py`（27）+ `tests/test_contract.py`（9）+ `tests/test_repo_layout.py`（5）；Playwright webServer 自动起 mock+H5 | `mock/app.py`、`mock/agent.py`、`mock/state.py`、`scripts/dev.mjs`、`run.ps1` | `.\verify.ps1` 或 `.venv\Scripts\python -m pytest -q tests` | `receipt/pytest.xml`、`receipt/logs/pytest.log`、`receipt/verify.json` | PASS（本机实测） |
| AC1 | 渠道入口 → 同意 → 7 项 → 政策问答 → 站点 → 预约 → 结果页全链路 | E2E `AC1 ...`；断言 `source_channel`、0/7→7/7、政策出处 `POL-1807 §3.2` + 免责声明、3 个站点、预约/改约/取消、导航/虚拟号/到站须知 | `src/App.jsx`、`src/screens/ConsentScreen.jsx`、`src/screens/ChatScreen.jsx`、`src/screens/ResultScreen.jsx`、`src/components/Cards.jsx`、`mock/agent.py` | `npx playwright test e2e/full-flow.spec.js` | `evidence/playwright.json`、`receipt/logs/playwright.log` | PASS（本机实测） |
| AC2 | 同意门：不勾选不能开始；不同意有电话出口；`consent_version`/`consent_at`/`source_channel` 真实回传 | E2E `AC2 ...`；路由拦截 `/api/v1/consents` 检查 payload；pytest 同意记录/保留期 | `src/screens/ConsentScreen.jsx`、`mock/app.py` | `npx playwright test e2e/consent.spec.js` | `evidence/playwright.json` | PASS（本机实测） |
| AC3 | 每屏/每步都显示「本服务由 AI 提供 · 可随时转人工」 | E2E 两条：同意页、7 步对话、站点卡、结果页、自助页；滚动后仍可见 | `src/components/Banner.jsx`、`src/App.jsx` | `npx playwright test e2e/ai-banner.spec.js` | `evidence/playwright.json` | PASS（本机实测） |
| AC4 | 个人信息查看/更正/下载副本/撤回删除 + 联系人工；撤回后本地缓存清空且会话失效 | E2E `AC4 ...`；断言脱敏姓名/手机、更正持久化、下载文件名、`tel:`、localStorage 两键为 null、旧 token 410 | `src/screens/ProfileScreen.jsx`、`src/storage.js`、`src/api.js`、`mock/app.py` | `npx playwright test e2e/self-service.spec.js` | `evidence/playwright.json` | PASS（本机实测） |
| AC5 | iOS/Android 三宽度（375/390/414）无横向溢出；系统字体 150% 不错位；截图可核 | E2E：三宽度全页截图 + `documentElement.scrollWidth <= clientWidth + 1`；150% 检查 app-shell/chat-screen/progress/composer/bot 气泡 | `src/styles.css`、`e2e/layout.spec.js` | `npx playwright test e2e/layout.spec.js` | `evidence/screenshots/*.png`、`receipt/verify.json` 中尺寸/字节 | PASS（本机实测） |
| AC6 | 断网 10 秒进度不丢；恢复后会话续接 | E2E：`setOffline(true)` → 10 秒 → 进度 3/7 与 localStorage 一致 → 恢复 → 继续作答到 4/7 | `src/components/Banner.jsx`（在线状态）、`src/storage.js`、`src/screens/ChatScreen.jsx` | `npx playwright test e2e/offline.spec.js` | `evidence/playwright.json` | PASS（本机实测） |
| AC7 | 交付闭环：README 三步、verify 一键、容器与 CI 文件、证据可核 | `.\verify.ps1` + `docker compose config` 静态校验 + workflow YAML 存在性 | `README.md`、`verify.ps1`、`scripts/verify.py`、`Dockerfile`、`Dockerfile.web`、`docker-compose.yml`、`.github/workflows/*.yml` | `.\verify.ps1`；容器见 `docker-compose.yml` | `receipt/verify.json`、`docs/USABILITY-GATE-1807.md` | 部分 PASS：本机 verify 实测通过；**Docker daemon 不可用，容器未本机实跑**；CI 未推送 |

## 补充说明

- AC5 的截图是 Playwright 在 375×667 / 390×844 / 414×896 三个视口下 `fullPage` 生成，尺寸与字节写入 `receipt/verify.json` 的 `screenshots` 数组。
- 首屏性能（AC 的 4G ≤2s）只在本地 Vite dev 测量（`evidence/perf.json`），**不能外推为 4G 现场结论**；4G 现场需真机/弱网环境复测。
- 微信小程序为加分项，未包含在本仓库（见 README「已知限制」）。
