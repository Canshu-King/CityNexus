### 🧭 aad2d1f2 (SESSION=aad2d1f2) P3 · **写腿没有客户端期限**：可复现具名读数（ORD-0273 第①格的输入事实） @2026-09-24T12:0x+08

**我先说清身份**：ORD-0273 的写者是 D、runtime verifier 是 HJ-P1。**我这一枚是发现者/仪器侧证据**，不是那一格的验收结论；名义按包工头 11:3x 裁定归我，谁要引它进 0273 请按"HJ-P3 仪器侧读数"引。

### 机制（源码坐标，发布包本体，不是我推的）
文件 `index-ChOTTCvB.js` sha256 `2d56a79632efc0c6b30396ebbddcd54bd84c0d2fa6a30d3f20d09f4655d419de`：
```js
const pb = 12e3;                       // 读腿期限常数
class uS extends Error { … this.name = "ReadDeadlineMissed" … }
async function vb(t, e = {}, n = pb) {
  const r = (e.method ?? "GET").toUpperCase();
  if (r !== "GET" && r !== "HEAD") return fetch(t, e);   // ← 非 GET/HEAD：直接透传，不装 AbortController、不起计时器
  const i = new AbortController; …
  const l = setTimeout(() => { o = true; i.abort() }, n); // ← 期限只在这条分支里建
  …
}
```
⇒ **12 秒到期这件事只对 GET/HEAD 生效**；POST/PUT 那条路把请求原样交给 `fetch`，自己没有任何期限。

### 两臂读数（同一枚发布包、同一台一次性后端 `:8492`、面 `:8493`、390×844）
| 臂 | 注入 | 读数 |
|---|---|---|
| **读（正控）** | `page.route('**/experience**')` 永不回 | 12 秒时**应用自己**宣布：「没有回音」「**等了 12 秒**，这台服务器一个字也没回答」「…它只是没有说话。你的行程数据没有丢…」+ 三扇门（看已保存的只读副本 / 重试 / 归因详情）。同常数下的独立读数：`GET /experience` resource timing = **12,001 ms** |
| **写（被测）** | `page.route('**/agent/commands**')` 永不回 | **23 秒**：屏上「发出请求，等待模型返回 · **已等待 23 秒**」，`aborted_after_ms = null`，无终态；**61 秒**：计数 **60**，`aborted_after_ms = null`，仍无终态。屏上全程只有「后端不会中途汇报进度，所以这里只有真实等待时间，没有百分比，也没有猜。」+「取消 / 取消并关闭 / 规划中…」 |

**⇒ 你要的三问**：① **客户端期限是否存在**：**写腿没有**（读腿有，12 秒）；② **屏上计时文字**：写腿是「发出请求，等待模型返回 · 已等待 N 秒」，一路真数到 60；③ **多少秒后进入什么终态**：**到 61 秒（我的观察上限）没有任何自动终态**，唯一出路是用户自己按「取消 / 取消并关闭」。

**这对 ORD-0273 的含义（只报事实，不替 D 设计）**：写腿上**不存在第二只独立等待钟**可作为"到期"依据 —— 也就是说，0273 第①格若要"随该读结算进入具名可见状态"，在写腿这一侧**没有现成的期限可挂**；要么由用户动作（取消）结算，要么得由产品自己给写腿一个期限。这正反两面我都把读数摆在这里，怎么用归 D。

### 我不藏的四条限制
1. 写腿我只观察到 **61 秒**，不是证明"永远不结束"。
2. 我的 `window.fetch` 包装在页面加载之后安装，**一次 `page.goto` 会把它冲掉**（这一轮我踩到过：控制臂的 `recs` 因此为空）。所以读腿那条正控的证据是**应用自己说的「等了 12 秒」**+ 更早那次 resource timing 的 **12,001 ms**，不是我包装器抓到的 abort 事件。
3. 两臂的故障都是**浏览器侧 route 注入**（明确标注），底层一次性后端是健康的 —— 这测的是客户端行为，不是服务端行为。
4. 我没有对 `PUT` 单独跑一臂；源码那条判断是 `r !== "GET" && r !== "HEAD"`，所以 PUT 与 POST 同类，但**"PUT 也如此"这句我只从源码读，没有运行时读数**。

### 复现配方（谁都能重放）
1. 候选 `3093eea`（按 40 位 sha 取包）起一次性后端 `:8492`，库按"只重放结构"建（92 语句 / 55 表 / 0 行），seed 我自己那 1 traveler + 1 journey；
2. 当前发布包 `index-ChOTTCvB.js` 起一次性面 `:8493`，`CITYNEXUS_BACKEND_PORT=8492`，先做归属双向证明（我的行程 200 / 外来 uuid 404）；
3. `page.goto('…/v8/hub')`（`/` 会落向导页，深链接才进 hub）→ 装 fetch 包装记 `signal`+`abort` → 分别挂 `**/experience**`（读）与 `**/agent/commands**`（写）；
4. 读屏上逐字与 `aborted_after_ms`；收尾按脚本断言。

### 收尾（脚本内断言，不是手工补）
`write_read_deadline_answer.py` 末尾：先用 `Win32_Process.CommandLine` 证明两条 listener 是我起的再杀（`:8492` 与 `:8493` 各一，2 条），删一次性库含 `-wal/-shm`，断言 **`listeners_left_8492_8493 = 0`、`db_exists_after_delete = False`、`assert_clean = True`**。
**纪律**：0 次 `demo/reset`、0 次读写 `_live.db`/`_preview.db`、0 次改产品字节、凭据 0 打印、已发布路径 0 覆盖。
