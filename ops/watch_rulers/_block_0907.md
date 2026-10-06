## 亲测 @2026-09-25 09:0x+08 —— 手机上那一包**我从公网隧道里取回来对过字节**：`index-xKIGmoBz.js` 与盘上逐字节相等，且里面确实带着 0274 的那个事件名

```text
GET https://obligation-plain-arcade-bean.trycloudflare.com/assets/index-xKIGmoBz.js（带 Basic，凭据只走文件）
  served 1,249,346 B == 盘上 D:/moodle/_qoder_preview_20260920/dist/assets/index-xKIGmoBz.js  逐字节相等 True
  served sha256 前 16 位 ba6654a08dd6f98e
  子串命中：`citynexus.sw.generation-handover-pending` True、`generation-handover` True
  子串未命中（**如实，但原因是压缩，不是没落地**）：`inFlightWrites`（模块名被打包改写）、`safe point`/`safePoint`（注释被剥掉）
⇒ 落地代 `5c4608cede6cb7bd5f3ac7e704bfee379ca47abc` 的前端源码里 `frontend/src/main.tsx:1683` 有那个 pending-handover 键名、
   `frontend/src/lib/inFlightWrites.ts:2` 是 B2c 的注释；**手机取回的同一字节流里能搜到那个运行时事件名** ⇒ 这不是"重建了但没部署"。
收据：`evidence/ord0274-landed-generation/deployed_bundle_bytecheck_r1.json`
```
**没变的东西**：权威线未动；地址未变；用户库 0 读写；`demo/reset` 0；凭据 0 打印。
**还欠**：ORD-0297（HJ-P1 两格）、0298（D 换代次重跑）、0299（B 真跑 + 反件）、0295（红队普查）、0296（F 后端半）。
