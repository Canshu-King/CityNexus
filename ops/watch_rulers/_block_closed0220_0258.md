## commander 验收 + 关闭 @2026-09-23T02:58+08 —— **ORD-0220②③ 双双满足关闭条件**（HJ-P1 ③ 按收窄形状 3/3 无 FLIP ＋ 端口→产物映射已发布）；aad2d1f2 把 R-2 从"未验"变成 **STILL_STANDS 3/3 且机制具名**（新开 ORD-0237）

### ① HJ-P1 `1a986a24`：ORD-0220③ **3/3 PASS、无 FLIP**（形状完全照仲裁收窄版）

```text
同一前端代次 + 同一后端代码 + 同一视口与探针
3 个独立浏览器进程 + 每跑一份从同一 sealed 基线克隆的新副本
run   浏览器 pid   臂（base→静态→库）               scrollY / hintY / inView
ui3a  52760        :8781→:8771→_hjp1_ui3_1.db        652 / 572 / true
ui3b  51876        :8782→:8772→_hjp1_ui3_2.db        652 / 572 / true
ui3c  56868        :8783→:8773→_hjp1_ui3_3.db        652 / 572 / true
三份副本同源同哈希（backup() 自 _hjp1_gen.db，sha256 前缀 5417dd51c92f4b91，各 44/59/27）；三份收据 sha256 互不相同
② 按裁定不再当基线用，只是三次顺带都读到 ''
```
**它把红队那条 `-wal` 测清了**：每跑结束后自己那份副本的 `journeys/travelers/journey_operations_contexts` 仍是 **44/59/27** 且 `nonGetRequests=0`，但每份都有一个 **24,752 B 的 `-wal`** ⇒ 正确说法不是"零写"，而是**没有非 GET 请求、向导拥有的表行数不变；WAL 增长来自"读时写"的 GET 端点**。**这正是"每跑一份新副本"的理由。**
**端口→产物映射已发布**：`generation_server_map.json`（每条臂的 base / dist root / served index ref / entry bytes / sha256 / 产出提交 / 自己的库副本，全部 HTTP 实读或哈希实测）。
**事实校正（它提的）**：仲裁查到的 `serve_genold/new.py = NOT_FOUND` **早于它 02:2x 的推送**；现在 `ls-tree` 里两者都在 ⇒ **请按 `afad4de` 之后的引用复查**。
**发布 8 件、一次通过无 409、全部 BYTE-LEVEL MATCH**：`generation_server_map.json 63add3bb3712a69e`(5,833 B)｜`ui3a b0eabb67ebc7a0ba`、`ui3b f9677d9e1548ea38`、`ui3c c85caa2bcc129c43`(各 2,249 B)｜`manifest.CORRIGENDUM.json c3bd975b960a1c9f`(7,160 B，v3：**ui3a/b/c 才是权威复制件**，`genN*` 因共用一份副本只作旁证)｜`serve_ui3_1/2/3.py`(各 3,187 B)。
**它自曝一个汇总 bug**：上一条打印把"distinct bytes"算成**长度集合**（得 1），差点写成"三份不可区分"——**判可区分要比 sha256 不是比长度**，已重算并写进块。
**进程按监听 PID 收完**，自己这批端口 0 监听；`4781/4782/8693` 未碰；另有个 `:8788 PID=16012` **不是它的端口**，没动也没猜它是谁。

⇒ **按仲裁冻结的形状（`ORD-0220③ UI_GENERATION_REPLICATION`，3/3 ⇒ CLOSED）＋ 映射已给**：
```text
ORD-0220② = CLOSED(FIXED_IN_GENERATION)     旧代「还需要填写：总预算」→ 新代 ''（HJ-P1 三跑均读到空）
ORD-0220③ = CLOSED(FIXED_IN_GENERATION)     旧代 scrollY=0/inView=false → 新代 652/572/true，3/3 无 FLIP
```
**两个条件的证据都在外部可读面**（映射件 + 三份权威复制件 + 勘误 v3）。

### ② aad2d1f2 `aad2d1f2`：R-2 从"未验"变成 **STILL_STANDS 3/3**，且它**推翻了自己上轮的读数**

- **取消按钮一直都在，从 `已等待 0 秒` 就在**（4/4 次提交都在 1.2 秒内可见）。**我给的两种解释都被否证**：三代包的 `取消并关闭/已等待/plan-ai-cancel/plan-ai-live` 字面量计数**完全相同**；源码 `PlanWithAiSheet.tsx:750 {busy && …}`、`:861` 无阈值。**上轮"从没看到"是因为它只在 run 落定后才读屏**——它把这条记在自己头上。
- **3/3 在飞取消**（点击时刻 4 s / 23 s / 23 s，墙钟由**页内定时臂**保证）：`855ed7ce` COMPLETED（3,766 字符产出，**7 步全在点击后**）；`d819c925` FAILED_EXTERNAL（**17 步里 14 步在点击后**，点击→终态 +27 s）；`118db007` COMPLETED（3,424 字符，**4/5 步在点击后**）。三笔对 `plan_versions` 贡献 **0**；硬刷新 + 翻 `/v8/agent` 都没有任何出口 ⇒ **按钮说谎 ＋ 结果静默丢弃**，机制指到 `:851-860`（只做 `abort()` + `onClose()`）。
- **前置按我要求补齐**：`Connection.backup()`（`mode=ro`）出 3,710,976 B 副本，`CN-BEIJING` = **8 places / 5 city_services**；归属双向证明（副本专属 id 200、旧库专属 id 404）；走真 UI 建了 `3dadf0c1…`。
- **两条它坚持挂在分母上的**：① 它用的 `DEEPSEEK_API_KEY` 就是账本里那**待吊销的泄露 key**（只记名字/长度/前 12 位），6 趟里 3 趟 `FAILED_EXTERNAL` ⇒ 新代这条 AI 腿是**半通半断**；② 本轮在**隐藏面板**里跑，"已等待 N 秒"被 `setInterval` 节流冻在 5/6/9 秒（墙钟 21–37 s）⇒ **只记观察、不定级**，要可见标签页或真机复测。
- 顺带三格：**FIXED**——上轮"行程被删静默落到新建"现在会明说「这台服务器上没有这一趟行程了…这不是网络问题」并给两个出口；**POLISH**——中文界面吃英文场所名（chips `我想去Houhai Lake Bar…`）；另记一次未定级的"兴趣 小吃+人文 → 确认页只剩 人文"。
- 它**保留 lane（`:8424`/`:8464`）不 release**，因为地图新手势那一格还欠验。

### ③ ORD-0237（→ D `e345b9d6`，排在其手上队列之后）

- id: ORD-0237
  to: e345b9d6
  priority: high
  if_head: e08131e
  order: |
    **「取消并关闭」按钮说谎：点了它，那一趟 run 照样跑完，产出静默丢弃。**（`aad2d1f2` 在新代上 3/3 实测）
    证据：点击时刻 4 s / 23 s / 23 s；`855ed7ce` COMPLETED（7 步全在点击后）、`d819c925` FAILED_EXTERNAL（14/17 步在点击后）、`118db007` COMPLETED（4/5 步在点击后）；**三笔对 `plan_versions` 贡献 0**、硬刷新与 `/v8/agent` 都无出口；机制指到 `PlanWithAiSheet.tsx:851-860`（只做 `abort()` + `onClose()`）。
    **二选一，不许第三种**：**(A) 让它真取消**（用户点了就真的终止那趟 run，或明确"已停止"）；**(B) 明写它只关界面**（按钮文案/提示改成不承诺取消）。
    验收：①(A) 则"点击后在飞 run 必须终止"要有可核终态（不是"没有新步骤落库"这种弱读）；②(B) 则屏上文案与 `abort()` 行为一致，且两个方向各有一条门；③无论选哪条，**都要给出"点击后屏上发生什么"的两向读数**（before/after），不许只交代码。
    另附两格低优先级：**中文界面吃英文场所名**（chips `我想去Houhai Lake Bar…`）与"兴趣 小吃+人文 → 确认页只剩 人文"（后者未定级，先量再改）。
  status: DISPATCHED@2026-09-23T02:58+08 by 494abfd7（来源＝`aad2d1f2` 新代 R-2 3/3 ＋ 源码行号）

### ④ 现场

链三条端口在听（`:4781` 56212 / `:4782` 20364 / `:8693` 55960）；三代包同挂；清理闸门仍关（0 删除，等用户真机刷新）；`P7=false`；reference tip `c0d7e3d`；P0 未动（HARNESS 第二把尺）；那把 key **仍未轮换，且今夜仍有车道在用**（见 ②）。
