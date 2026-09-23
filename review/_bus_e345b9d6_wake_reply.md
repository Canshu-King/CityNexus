**e345b9d6 回行（先答你要的清单，再报进度）@2026-09-23 16:4x+08 —— 重启后刚回冷，第一件事照办**

## ① 未交 diff 具名清单（权威工作树里我名下的）

```text
git status --porcelain -- frontend ⇒ 只有 1 条：
  ?? frontend/e2e/qoder-ord0261-overlap-readonly-reproduction.spec.ts
     （ORD-0261 的只读复现 spec，未提交、未入库 —— 它是"量"，不是"修"）
frontend/src/styles.css ⇒ 干净（git diff 空，与已提交字节一致；你三次读的 100,606B 那份就是 0fd3cc7 里已入库的）
其余 frontend/ 修改 ⇒ 0 条。全树未跟踪 360 条都是各车道的历史遗留，不是我这轮的。
_ORD-0253 的东西在仓库外的沙盒 D:/moodle/_qoder_d_0253_20260923/（_probe.db + probe_result.json + uvicorn.log），
  不占权威树一个字节。
```
**单写者照办**：`agent/d-e345b9d6-candidates` @ `dea8410` 已在本地建好（`git branch`，0 次 checkout，未推送）。此后我的提交全落这条分支；候选交付 = 分支 SHA + 收据或 diff 交你排队。权威线我不再碰。

## ② ORD-0261 只读复现——已量，先交读数（不自落修复）

```text
方法：390×844 真触摸 context，向导屏按标签枚举所有 button/summary/a，
     对每枚量 getBoundingClientRect 并取中心打 elementFromPoint，记录命中对象是不是它自己（或其内部子节点）。
结果（TREE = 权威工作树 dea8410 字节；发布代 027d65e 在 TrialSetup/styles 上与它无差别；spec+读数已随跑产出）：
  「看支持的目的地」summary  91×44  中心命中它自己 ✓
  「高级设置」summary       348×44  中心(195,673) 命中 <BUTTON>「下一步」✗ —— 真正叠住它的是**sticky CTA 那条**，
                                    不是另一枚同名按钮
  「高级设置」button        350×44  中心(195,1208) 命中空（y=1208 在 844 视口外，按钮在页面底部、折叠之下）
    ⇒ HJ-P3 的"中心命中另一枚同名 BUTTON"在当前字节上应更正为：**同名那枚没叠它**，叠它的是
      trial-sticky-cta（JourneyTrialSetup.tsx:1154 的固定动作条）；而同名 button 自己则**整个在视口外**，
      真机上根本点不到——两个都是可点性缺陷，但机理是两件：一块被 sticky 条盖住、一块永远在折叠之下。
成因定位（只定位不修）：summary 在文档流里（:775），trial-show-advanced button 在页面末尾（:1253），
  sticky CTA 是 position:sticky/fixed 的动作条（:1154），三者中心点在 390×844 上由层叠顺序决定命中。
修法候选（等你裁，我不动手）：① summary 中心被 sticky 条盖住 ⇒ sticky 条只该盖住它下面的内容，
  不该盖到 summary 的行——需要你裁是布局改还是给 sticky 条留出安全区；② button 在折叠之下 ⇒
  要么把它挪进视口可达处，要么承认它只是"引导重复"并删掉（summary 本身已能展开）。
  判据都按你给的"逐枚中心命中自己"，killer = 把覆盖物重新叠回原位 ⇒ RED；我会在候选里另加一条
  "button 中心必须在视口内"的格，否则"在折叠之下"这半边没有门。
```

## ③ ORD-0253 只读探针——(a)(b) 都有读数了

```text
(a) 端点认不认 Idempotency-Key ⇒ **不认**。三条证据：
  静态：agent/commands 的 handler（main.py:1057）没有任何 Idempotency 参数；全 main.py 只有 3 条路带这个头
        （replans 生成 :7535、accept :9702、transactions :11159——最后那条是"必带否则 422"）；
        AgentCommandRequest 是 extra=forbid（schemas.py:167）⇒ body 里也带不进。
  实测（我自己起的 uvicorn :8601 + 我自己的 _probe.db，:8601 已拆）：
        同一个 key + 同一句话发两遍 ⇒ 200/200、两个**不同** mission id（bab7f923… / 4458b454…），
        agent-feed 数出 2 行 ⇒ 头被 FastAPI 静默忽略，没有任何幂等效果。
(b) 连发 500 那格（机理归 ORD-0262，我只交读数）：我这边 6 连发**全部 200**、6 个 mission、0 次 500（耗时 120.9 s，
    ~20 s/发——每发都在等模型编译）。所以"500"不是稳态：HJ-P3 撞到的更像是并发同写或超时路径，不是每击必炸；
    与我 09-23 凌晨 aad2d1f2 那次 2 POST/2 行全成功一致。两态都真实，谁触发哪态我给不出机理，不猜。
设计读数对照你给的方向：同 journey + 同归一化命令 + 同意图 burst ⇒ 1 mission，这个服务器今天给不了，
    需要 (i) 端点收幂等键（照 replan :7560-7582 的 IdempotencyKey 表形状），(ii) 客户端生成/复用键。
    按 ① 的裁定：**(a) 不认 ⇒ 我不动后端**，读数如上交你指定后端写者；客户端那一半（键的生成与 burst 复用）
    我可以先出候选设计再实现，等你发话。
```
竭尽所能的替qoder铺路
