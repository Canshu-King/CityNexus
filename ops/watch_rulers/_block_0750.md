## 亲测 @2026-09-25 07:4x+08 —— 手机链端到端重测 **HEALTHY**（并交叉印证"现在手机上是落地代那一棵"）；**ORD-0288 T-1 判据加两条**；**新单 ORD-0295 派红队**（我采用了 F 的普查数当底稿 ⇒ 按我自己的规矩得有第二观察者）

### ① 手机预览链 07:49 端到端实测（我亲自走的，不是看进程表）
`https://obligation-plain-arcade-bean.trycloudflare.com`（cloudflared pid 55160 / preview 4781 pid 12076 / 认证代理 4782 pid 34324）：
```text
无凭据 GET /            -> 401                        （门在）
带凭据 GET /            -> 200 text/html 1,200 B 1.45 s
  index 引用 2 个资产：/assets/index-CtuiCkKf.js  -> 200 text/javascript 1,248,629 B 8.10 s ✅
                        /assets/index-I45CQek8.css -> 200 text/css         183,897 B 2.05 s ✅（没有"JS URL 回 HTML"）
带凭据 GET /api/v1/health            -> 200 json    84 B（ai/database/e2e_run_id/status）
带凭据 GET /api/v1/agent/runtime-status -> 200 json 379 B
带凭据 GET /api/v1/demo/scene        -> 200 json 583 B（journey_id/evidence_state/demo_mode）
带凭据 GET /api/v1/destinations/capability -> 422 json 287 B —— 诚实答案（该路由要显式区域参数，见旧结论），不是坏
```
⇒ **结论：链 HEALTHY，用户现在打开地址就能用**；一次误判我先自我更正：我先前拿 `/api/v1/today`、`/api/v1/journeys` 猜路名得到 404/405，那是**我没读路由表**；读表后（落地导出 `D:/moodle/_qoder_wt_45b0a5e/backend` 里 `@app.get` 全清单）这两个路名本来就不存在 ⇒ 404/405 是路由正确行为，**不构成缺陷**。
**顺带一枚交叉印证**：现在服务的是 `index-CtuiCkKf.js`，而 HJ-P1 那份 0290 收据里 B2c 的"未修复臂 45b0a5e2"读到的正是 `CtuiCkKf` ⇒ **两套互不相干的仪器指向同一代**，手机上就是落地代，没有旧代残留。

### ② ORD-0288 的 T-1 判据加两条（来自红队 0293 实测的承重事实）
原判据只问"带键有没有落 `idempotency_keys` 行"。现在补：
```text
T-1(a) 同键 + 不同请求体 => 必须 409，且第二次不得再落新行（凭条绑的是"请求"，不是"键字符串"）；
T-1(b) 错误路径也要如实：若产品选择"落行并记 response_status"，收据必须把落行的 status 值一起给出
        （红队实测 plans/generate 在 422 上仍落一行且 response_status=422 —— 这不是 bug，但**判据不许把它当 200 蒙过去**）。
反控不变：不带键 => +0 行（与源码 `if idempotency_key is not None:` 对齐）。
```
⇒ 谁交 0288 都得覆盖 a/b，缺一条就是 PARTIAL。

### ③ 新单 **ORD-0295 → @红队（d2305848）**：第二观察者复现"写腿普查"的 AST 口径
```text
背景（我为什么自己派这一单）：07:4x 块里我把 F 的 AST 普查当成了 0280/0281/0288 的**清单底稿**
（站点 39 / 写腿 14 / 带 signal 2 / 带计时器 0，tree=落地代 45b0a5e2）。
按我自己的规矩"只信亲测数字"——我采用别人的数就得有第二双眼睛。
要件：
 1) 用**你自己写的** AST 脚本（不要读 F 的实现、不要借它的 visitor），对**GitHub tarball 干净导出**的 45b0a5e2 复现同一口径；
 2) 四张数各自独立报（站点/写腿/signal/timer），并**逐处点名**与 F 的差异：一致就写"逐处一致"，不一致就给出 file:line + 你的判定理由；
 3) 口径声明必须自带：`.d.ts` 与 node_modules 的排除、`method` 取不到字面量时记 unresolved（不许猜）、
    signal/timer 只看同一调用表达式（不许借窗口）；
 4) **判别性自证**：脚本要跑两枚反例——(i) 注释里的 `fetch(` 字面量不得算站点；(ii) 同文件里 method 在窗口外/AST 上属另一发的 POST 不得算第二根写腿。
    两枚反例都要"移除判定 ⇒ 红"，不许只在正例上绿；
 5) 先读权威尖（应为 45b0a5e2…）并在收据里存 `ref_tip_read`；收据走 `evidence/ord0295-census-second-observer/<自己的文件名>.json`，**新路径、0 覆盖**；
 6) `claimed_result` 由你写、`derived_result` 留 null（闭单口径按 B-1，我这边机械派生）。
```

### ④ 队列与纪律
0294（HJ-P1 重切 B2c + 每格独立 `why`）在跑 ⇒ 0274 仍拦停；0291（HJ-P3）/0292（D 本代击杀）/0280（B 三句归因）在跑；**0287（F：权威线专属 K8 载体回归测试）我去敲门**——F 现在是 ready 不是 running。**权威线未动**（`45b0a5e2…`）；已发布路径 0 覆盖 0 删除；用户库 0 读写；`demo/reset` 0 次；凭据 0 打印（本次探针只输出状态码/字节数/Content-Type）；手机链最后实测 **07:49 HEALTHY**。
