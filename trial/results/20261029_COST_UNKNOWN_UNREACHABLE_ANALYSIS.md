# 「费用：未知」这一格为什么在屏上永远读不到 —— 链条事实与两条待裁修法

日期：2026-10-29 凌晨 · 代次 `3d5725fe2a`（`rescue/v3-final-departure-20261022`，远端已回验）
出处：第 2 刀 2a 的验收句「new/old diff beside the accept key with **missing cost written as unknown**」
状态：**只交事实，未改产品语义**。这一格归 #344，改法需要号令者/主人点名。

## 一、前端确实把 unknown 写出来了

`frontend/src/trial/mobile/ClassroomPresenterPanel.tsx:307`、`:308` 两枝都在：

    路上：{proposalDiff.travel == null ? "未知" : …}
    费用：{proposalDiff.cost   == null ? "未知" : …}

喂给它的是 `:181`、`:182`：

    cost:   typeof row.diff.cost_delta_minor === "number" ? row.diff.cost_delta_minor : null,
    travel: typeof row.diff.travel_delta_min === "number" ? row.diff.travel_delta_min : null,

屏上证到的是「费用：不变」（bf110 那条链的读数），也就是 `cost` 取到了数字那一枝。
**「费用：未知」至今没有任何一次屏上证词** —— 这不是漏测，是因为它拿不到 `null`。

## 二、上游从不给 null：三处把"没有花费证据"折成 0

| 位置 | 现读到的写法 | 后果 |
| --- | --- | --- |
| `backend/app/agent/contracts.py:93` | `cost_delta_minor: int = 0` | 契约字段本身是整数，默认零，不是 Optional |
| `backend/app/agent/gateway.py:543` | `cost_delta_minor=int(diff.get("cost_delta_minor") or 0)` | 模型提案里没这个键 ⇒ 0 |
| `backend/app/agent/guardian.py:624` | `cost_delta = max(0, int(diff.get("cost_delta_minor") or 0))` | 同样先折成 0 再跟授权上限比 |

其余写者（`gateway.py:2779`、`:3386`、`:3529`）都是 `某侧总价 − 另一侧总价` 的整数相减。
所以 `typeof … === "number"` 恒真，前端那两枝里的「未知」**在当前契约下不可达**。

## 三、为什么这是产品问题而不是显示问题

计划活动里"价未核实"的活动，在本产品的既有口径下**不计入总额**
（`frontend/src/i18n/LocaleContext.tsx:1219`「供应商价格 · 未知费用不计入总额」、`:1230`「未知费用保持未知」）。
而 diff 是对两个"已知部分之和"作差 ⇒ 当两侧都有未核实项时，`cost_delta_minor = 0` 的真义是
**"已知费用的差额是 0"**，屏上却写成「费用：不变」——旅客读到的是"总花费没变"。
这与 `LocaleContext.tsx:1230` 那条口径直接矛盾，也正是验收句要防的那件事。

## 四、两条修法（都需要点名，我不自取）

甲、**给"算不出来"一个形状**：`contracts.py:93` 改 `cost_delta_minor: int | None = None`，
`gateway.py:543` 去掉 `or 0` 改为保留 None，并让 `guardian.py:624` 明确裁决"拿不到差额时算放行还是算拦"。
影响面：授权门（自动重规划的花费上限比较）。0 与 None 在这扇门上的语义不同 ——
现在 0 表示"没有花费增量 ⇒ 允许自动"；若 None 被继续折成 0，等于"不知道就放行"；
若 None 变成拒绝，就会把一批原本自动通过的提案改判成"要人按"。**这一句必须由号令者/主人裁**。

乙、**只改屏、不改门**：diff 增加一个"本侧是否存在未核实价格的活动"的布尔（后端在算差时顺手带出），
课堂面板在有未核实项时写「费用：含未核实项，差额未计」，其余情形保持现有三枝。
影响面：只读侧与展示，授权门不动；代价是要在后端补一个字段（不是语义裁决，但仍属跨端改动）。

## 五、本档没有做的事

一、没改 `contracts.py`、`gateway.py`、`guardian.py`、`ClassroomPresenterPanel.tsx` 任何一行。
二、没跑课堂模拟 run 去"碰"未知费用那一格：现有契约下碰不出来，跑它只会再得到「费用：不变」。
三、没写断言去钉这个形状 —— 值得钉的是"未知不许被折成 0"，而那要先有甲/乙裁语才谈得上断言什么。
四、`#344` 保持 OPEN。裁语一到我就补屏证与断言。
