# 2026-10-18｜Issue #33 C1 路线复核

## 结果

| 项目 | 实测结果 |
| --- | --- |
| 产品 Git HEAD | `f8f7e9d55d8547d24124dcc3f34520e438204c3a` |
| 页面 | `http://127.0.0.1:14332/revolution` |
| 浏览器 | headed Chrome-use，390×844 CSS 像素，DPR 1；不是手机硬件实测 |
| 服务 | 隔离前端可打开；`/api/v1/health` 返回 200，数据库健康，AI 状态为 `DISABLED_BY_OPS` |
| 城市查找 | Nominatim 返回 `GEOCODER_UNAVAILABLE`；用户确认切换后，Photon 返回 3 个城市候选并选中合肥市 |
| 附近地点 | 一次 Photon 咖啡馆查询返回 `LIVE_RESULTS`、3 个地点：星巴克、Post Coffee、1点点；选前两处作为路线站点 |
| 保存 | Pocket Walk 写入返回 HTTP 200 |
| GO | GO 写入返回 HTTP 200 |
| 整页刷新 | `/bootstrap-shortlist` 返回 HTTP 200；两处站点仍在，进度恢复为 `HEADING_TO_FIRST` |
| 正式行程 / Hermes | 没有正式 ACTIVE Journey，也没有 AgentRun；本次为 DRAFT 路线，AI 未启用 |
| 用户亲自验收 | `PENDING` |

路线顺序：合肥市 → 咖啡馆公开地点查询 → 星巴克 / Post Coffee → 保存为私人 Pocket Walk → GO → 整页刷新后恢复两站和“正前往第一站”。两处地点在实测结果中营业时间和费用均未知。

路线动作在上述 Git HEAD 上完成。随后才修改了 AI 关闭时的页面入口：隐藏仍然醒目的“问 AI”快捷按钮，并补充对应手机界面断言。这个改动使用独立 TEST_FIXTURE 验证，**不把它拼接成同一 SHA 的整条真实路线验收**。修复后的 GO 屏截图只证明当前屏幕状态，不替代重新跑完整路线。

## 手机视口截图

以下原图均为 390×844 CSS 像素；`01`–`09` 是隐藏 AI 快捷入口前的流程截图，`10` 是修复后在同一隔离会话拍摄的 GO 屏。标注版只标出当前 GO 屏上通过 Chrome-use 实时 DOM 读取到的两个按钮位置。

| 步骤 | 截图 |
| --- | --- |
| 探索草稿（入口修复前） | [01-draft-explore.png](assets/chrome-use-20261018/c1-final-f8f7e9d/01-draft-explore.png) |
| Photon 城市候选 | [02-photon-city.png](assets/chrome-use-20261018/c1-final-f8f7e9d/02-photon-city.png) |
| 已选合肥 | [03-city-selected.png](assets/chrome-use-20261018/c1-final-f8f7e9d/03-city-selected.png) |
| 咖啡馆类别 | [04-cafe-category.png](assets/chrome-use-20261018/c1-final-f8f7e9d/04-cafe-category.png) |
| 真实地点 | [05-real-poi-results.png](assets/chrome-use-20261018/c1-final-f8f7e9d/05-real-poi-results.png) |
| 已选两站 | [06-two-stops-selected.png](assets/chrome-use-20261018/c1-final-f8f7e9d/06-two-stops-selected.png) |
| Pocket Walk 已保存 | [07-pocket-walk-saved.png](assets/chrome-use-20261018/c1-final-f8f7e9d/07-pocket-walk-saved.png) |
| GO 已开始 | [08-go-underway.png](assets/chrome-use-20261018/c1-final-f8f7e9d/08-go-underway.png) |
| 刷新后恢复 | [09-after-full-refresh.png](assets/chrome-use-20261018/c1-final-f8f7e9d/09-after-full-refresh.png) |
| 修复后 GO 页原图 / 标注图 | [10-go-after-cta-fix.png](assets/chrome-use-20261018/c1-final-f8f7e9d/10-go-after-cta-fix.png) / [标注版](assets/chrome-use-20261018/c1-final-f8f7e9d/10-go-after-cta-fix-annotated.png) |

## AI 快捷入口修复

- 当运行状态为 `DISABLED_BY_OPS` 时，探索页不再显示“问 AI”快捷入口；页面仍显示“AI 建议暂不可用 · 可手动选地点”，并禁用 AI 咨询按钮。
- 验证：`npm.cmd run typecheck:all` 通过；隔离手机 Chromium 聚焦用例 `2 passed`；`git diff --check` 通过。
- 这组 UI 用例使用 `TEST_FIXTURE`，只验证显示和禁用状态，不产生模型调用或 AgentRun。

## 打开方式

在 Windows 上双击 [`../OPEN_REVOLUTION.cmd`](../OPEN_REVOLUTION.cmd)。窗口会显示本机实际入口与当前源码 SHA，服务运行时可打开 `http://127.0.0.1:14332/revolution`。此地址仅在这台电脑的隔离服务运行期间有效。

## 状态

`C1_ROUTE_AT=f8f7e9d`；真实地点查询、双站保存、GO、刷新恢复均通过。AI/AgentRun 仍未实测，真人手机验收待用户完成。GitHub PR #23 当前已发布版本与本次本地修复状态见对应 PR commit/checks。
