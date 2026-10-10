# Revolution R100 — Pocket Walk Result

日期：2026-10-11  
分支：`codex/revolution-r63-planned-parallel-journey`  
实现提交：`85f09b5f67`（待本结果文档提交后继续推送）

## 交付

R100 为 draft Journey 增加了 member-private 的持久化 Pocket Walk：

- 仅保存当前签名 member 的两个有序 `SAVED` shortlist identity 和可选 1–180 分钟步行偏好；表中没有坐标、GPS、receipt、route、navigation URL、Place 或 PlanVersion。
- 390×844 移动卡片显示 stop 1/stop 2、公共 OSM source、provider provenance 与 captured time；刷新后从后端恢复顺序和预算。
- stop 1 destination-only 导航与 public-to-public stop 1→stop 2 walking map 使用两次独立 consent；路由仍不写入 Journey 事实。
- public-only share 先展示精确文本，再由显式 consent 使用 Web Share/clipboard；只含两个公共名称、可信 OSM source URL、来源/捕获时间和可选人工预算。`TEST_PROVIDER` 内容明确标为 sample/unverified，私有 ID、token、Journey、GPS、receipt 均未进入分享文本。
- 删除任一 stop、改变顺序/预算、签名 member 改变或 DRAFT/PlanVersion 墙会使旧 Pocket Walk 不可继续使用；删除 stop 会等待持久化清除完成后再删 shortlist，避免刷新竞态。

## 受控验收证据

权威运行：`r100-pocket-20261011-08`，SQLite `backend/_r100-pocket-20261011-08.db`，frontend `4260`，backend `8260`，AI disabled，Python `D:\moodle\CityNexus\.venv\Scripts\python.exe`，390×844 Chromium，`--project=chromium`。

- `2 passed`：real-seed + R100 Chromium 场景。
- 受控 city-search/Overpass 返回三个 R100 public TEST_PROVIDER candidates；owner 保存两个有序站点并设置 20 分钟偏好。
- 刷新恢复同一 pair/order/budget；stop 1 目的地-only popup 不含 origin，随后 stop 1→stop 2 walking popup 使用独立 public map consent。
- 分享 preview 与实际 Web Share payload 含 OSM public source 和 `sample/unverified`，不含 Journey/traveler/token；collaborator 的 signed read 没有 Pocket Walk 或三个名称。
- 删除 stop 后，前端等待 DELETE 完成；后端再次读取 `pocket_walk=null`，数据库 explore-only 计数保持 Place/PlanVersion/AgentRun/GuardianRun/Booking 全零。

真实外部路由未作为验收依据；本轮证据仅来自明确标注的本地受控 provider emulator。

## 检查命令

```text
py -3.13 -m pytest -q backend/tests/test_r98_two_stop_walkability.py backend/tests/test_r99_adaptive_short_walk.py backend/tests/test_r100_pocket_walk.py
3 passed

cd frontend && npm run typecheck:all
cd frontend && npm run build
py -3.13 -m compileall -q backend/app backend/tests
git diff --check
cd frontend && npm run test:e2e -- e2e/r100-pocket-two-stop-city-walk.spec.ts --project=chromium --reporter=line
2 passed
```
