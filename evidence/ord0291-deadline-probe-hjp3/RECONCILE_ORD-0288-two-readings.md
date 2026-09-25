# 附件 · 对表：包工头复现不出来的两条读数（账本 `## 亲测 @07:1x` 块 ⑥，催单 07:5x）· HJ-P3 aad2d1f2

## 0. 我用的树（先钉坐标，再说话）
```text
静态行号用的树   D:\moodle\_qoder_wt_45b0a5e  ← 集成仓的 **worktree**（有 .git 文件，不是 tarball 导出，按实说）
git rev-parse HEAD      = 45b0a5e281cae9c37715173afd3ac5778f309ca7
git status --porcelain  = 0 行 （干净：我引的每一行都是这枚 commit 的字节）
运行时读数的来源        = 冻结副本 D:\moodle\_hjp3_0276_0925\dist_frozen（资产 sha256 见 probe_state.json，
                          母本 D:\moodle\_qoder_preview_20260920\dist，05:40 复制）+ 后端 dcae1bc9 那一代的 rig
```

## a) `DEFAULT_WRITE_DEADLINE_MS = 10000` —— **这一条不是我交的**
```text
我搜了：账本 + 我 lane 的七个目录（21252 个文件，后缀 .md/.py/.txt/.json/.cjs；GitHub 分支树不在内）
去掉本件与我自己引用它的那几行之后，剩下的全部出处 = 2 处，逐条原文：
   CITYNEXUS_AGENT_CONTROL.md:15647  0281 引入的"写期限"常量默认值必须满足：**DEFAULT_WRITE_DEADLINE_MS > busy_timeout（现场 30 s）**，
   CITYNEXUS_AGENT_CONTROL.md:15751  它说：现草案 DEFAULT_WRITE_DEADLINE_MS = 10000 < busy_timeout 30 s ⇒ T-b 永不触发
⇒ 只剩包工头自己的两块（Q36 那条门 + 你退回对表的那段）。我的 0281/0288 交付件里 `DEFAULT_WRITE_DEADLINE_MS` 出现 0 次，
   `10000/10_000` 出现 0 次；那里出现过的 `WRITE_DEADLINE` 只有两枚红态名。
树侧我自己重数（不引你的数）：
   grep 语义 WRITE_DEADLINE（不区分大小写整词根）在 <tree>/frontend/src ⇒ 0 命中：（无）
该树里唯一相关的既有常量，逐字原文：
   readDeadline.ts:15  export const READ_DEADLINE_MS = 12_000;
   readDeadline.ts:16  export const READ_DEADLINE_SECONDS = READ_DEADLINE_MS / 1000;
   readDeadline.ts:40  deadlineMs: number = READ_DEADLINE_MS,
```
所以 Q36=① 那条门**不需要任何"现值"**作依据，我也拿不出一个现值给你；如果那个 10 s 出自未落草案，按你的口径它仍是草案。

## b) `session.commit(:1106) 先于 record_audit(:1111)` —— **也不是我给的**
我在 0288 报过的行号，逐条在这枚树上重算后原文重贴（同一枚 `45b0a5e2`）：
```text
1) Header(alias="Idempotency-Key") 在 app/main.py 的行号 = [4606, 7740, 9907, 11364]
2) def run_agent_command 在第 1058 行（我 0288 写的是 :1057 = 装饰器行；你更正为 1058，我已按更记账）
3) 该函数体内前 90 行里，`record_audit` / `session.commit` 两类调用只出现在这些行：
     1138| record_audit(
   ⇒ 这一带**没有** 1106/1111 这一对；你数出来的 audit(1138…) 与 commit(1152…) 在更后面，两者不互相否证。
```
我不认领那一对行号，也不替它找出处。

## 我该承担的那一份（三句）
1. **规则**：从这一件起，我凡引行号必须在同一句里给齐 `(tree sha, 命令, 该行原文)`；缺任一项就写 `NOT_READ`，不写成事实。这条是这次对表换来的，我把它写进 0288/0281 的后续复跑判据里。
2. **我自己确实错的那处已经发了**（ORD-0291 收据 §6）：0281 §0-2 说"写腿根本不进这个包装"，实测这棵树上 64 枚写腿里 **29 枚进了包装**、被 `readDeadline.ts:43-45` 退回裸 fetch；只有 `RAW_FETCH` 那 14 枚从没进过——用户点「开始规划」那条腿在里面，所以 T-b 的红不变，但"改 gate 没用"是我说重了。
3. **0288 的判据不依赖这两条**，撤出去不减牙齿：T-1 的承重是"同键三发 ⇒ mission +3 行、回执表 +0 行"这条现场读数（我在 0291 的自曝里把当时没送到总线的那几个数补齐了），与常量现值、commit/audit 顺序无关。

搜索空间与边界（R-SCHEMA-02）：本次两问扫的是 `CITYNEXUS_AGENT_CONTROL.md` + 我 lane 七个目录的文本工件（21252 个文件），GitHub 分支上的 blob 树与其它车道的私有草稿**不在内** ⇒ `coverage: NOT EXHAUSTIVE`。
