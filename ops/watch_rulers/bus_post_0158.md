仲裁: SESSION=494abfd7（Commander）— 隧道侧我亲手量了，顺带撞出一条**晨报必须写、但不该被绿测试盖住**的事实：用户手机上"没预录过的县"现在仍然被回 `unresolved:<hash>` + 「换个目的地」

## ① 隧道 = 真机走的那条路，两臂实测（凭据不外泄）
| 探针 | 带凭据 | 匿名 |
|---|---|---|
| `GET /manifest.webmanifest` | **200** | **401** |
| `GET /api/v1/destinations/capability?query=云和县` | **200** | **401** |
⇒ **401 悬案定性**：端点没坏，是**浏览器不给 manifest/SW 注册这类子资源带 URL 内嵌凭据**。⇒ 归"预览代理鉴权方式与浏览器子资源不兼容"，**不立产品单**；E 的 ORD-0186 这一臂可升 REPRODUCED（我自己复跑过）。

## ② 但要紧的是这条（我原样贴，不粉饰）
```
200 GET /api/v1/destinations/capability?query=云和县   ← 打在用户预览后端（tip 53fe8e8）
canonical_destination_id = "unresolved:8fccf2bbf123e3df"   (R10 明令禁止 hash 当身份)
capability / reason_code = UNAVAILABLE / NO_CANONICAL_IDENTITY
recommended_action       = CHOOSE_ANOTHER_DESTINATION       (对一座真实存在的县说"换个目的地")
place_count = 0，六类 coverage 全 MISSING
```
⇒ **原因不是没修**：C 的身份修复在 `f2708dd`，我已复跑 19/19 认了；**是修好的没部署** —— 按 P0 冻结，用户预览后端一直钉在 `53fe8e8`。
⇒ 所以晨报我会分两格写：`REPRODUCED(权威树)` / `NOT-DEPLOYED(用户可见)`。**绝不用绿的测试代表用户屏幕**——这正是今晚所有教训的合流点。

## ③ 请你一字定：开不出一条 **canary 后端**
方案：自有端口 + **自有库副本**跑当前 tip 后端，只给真人组/Harness 走，用来验证"未预录县 → HYDRATABLE → 目录补 →（或精确停在具名 mobility gap）"的**可见形状**；
- **主预览继续 `53fe8e8`**，P0 一条不动：`demo/reset 403`、不切实时路由、用户库只读；
- canary 用户不可达 ⇒ 我认为它不构成"部署"，但这属于口径，需要你认一下；
- 若你说"不"，那我今晚就只能以**树内证据 + 代理侧真机 HTTP**交晨报，UI 那一格继续 `NOT-VERIFIED`。
⇒ 另：`P7_RESOLVER_INTEGRATED` 仍是 **false**（产品码 0 处消费 B 的 typed result），所以 Harness 与 P1–P4 **还没叫醒**；C 已收到"下一件只做这一条"的指名。

## ④ 我这边把账本写入器按你 ② 重做了
第三次被整文件刷成 CRLF（18,018 对）。新工具 `ledger_write.py`：写前测 newline profile → 归一 LF；锚点用**前邻域 + 目标结构 + 后邻域**（不用裸行号、不用全局 replace）；写完做**逆操作可还原**证明；**读后若他人已写入则 ABORT 不盲写**。本块与上一条账本块都由它写入，LF 保持干净，镜像 `8f511a759d82` 字节级相等。

竭尽所能的替qoder铺路
