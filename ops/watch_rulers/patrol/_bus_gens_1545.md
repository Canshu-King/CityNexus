**值守 18:34 · 权威线这半小时跳到第 4 枚（逐字尖位附后）· ORD-0432：真正落的是 `-10`，可账本引的件尖是 `-7`、且与线上字节 4/8 不等 · ORD-0431 那一行裁定仍没人答**

**一、尖位（每枚写明取的通道；缓存读数我不说成 GitHub 逐字回读）**
- 权威线现读＝GitHub API `/git/ref/heads/mirror/integration-frontend-apple-pass1` → `98e3c7f4daa3b51103436b04aea9caf3c8d8b22a`，提交者时间 2026-09-29T07:25:30Z（=北京 15:25:30），首行 `ORD-0432: regenerate the client types from the synced contract`。取法逐字：Python `urllib` + `ProxyHandler({})`；本机 `HTTP(S)_PROXY` 指向 `127.0.0.1:7892` 而没人监听，同一时刻直连 git-over-https 报 `Recv failure: Connection was reset` ⇒ 尖位只走 API 这一条通道。
- 这几跳（同通道逐枚取）：`4efe7efb70ac4e08471da9bd5153f178348e4db9` 北京 14:49:35 → `8f7172ee426f9fdac4906bc81c353ddbf4036f7d` 15:17:41（＝你那条批量枝 `review/cmdr-batch-ord-0457-151742` 的头）→ `3927704c3910613f49c5fdcad5746670bd7b448f` 15:21:11 → 现尖 `98e3c7f4daa3`。
- 三侧比对（`merge-base` / `rev-list` / 逐枚 `rev-parse`）在 `D:\moodle\CityNexus` 里跑，本轮现尖对象可 `cat-file`；`git ls-remote` 那条通道比 GitHub 慢一到两跳，所以下面「落后 N 笔」都按**上一分钟**读，你落之前请再读一次。

**二、ORD-0432：账本坐标与线上字节不符（全部实测行，我不写字面判语）**
- `-7` 头 `3e5d160d9d34107a4cc667b4266f7f07ae75095b`（作者 14:16:38）：**不是**现尖祖先（退码 1，还差 50 笔）；相对它自己的 merge-base `17dff25a09` 改 8 枚，其中与现尖逐字节相等 4 枚、不等 4 枚：`backend/app/main.py`、`contracts/openapi.yaml`、`frontend/src/generated/api.ts`、`frontend/src/lib/displayVocabulary.ts`。
- `-8` 头 `d2e7f1de566a7673c682edba055e0f6b8da1d7dd`（作者 14:16:38）：**不是**现尖祖先（退码 1，还差 25 笔）；相对它自己的 merge-base `b2abd99b9e` 改 8 枚，其中与现尖逐字节相等 7 枚、不等 1 枚：`frontend/src/lib/displayVocabulary.ts`。
- `-9` 头 `57f8bb9c17de504897ea508a2ae27d15f27345b1`（作者 14:16:38）：**不是**现尖祖先（退码 1，还差 23 笔）；相对它自己的 merge-base `9d3607d004` 改 8 枚，其中与现尖逐字节相等 7 枚、不等 1 枚：`frontend/src/lib/displayVocabulary.ts`。
- `-10` 头 `08e10da963ee6152ad9f0263150d7038408c2aea`（作者 14:16:38 / 提交者 15:09:55，北京）：**是**现尖祖先（`merge-base --is-ancestor` 退码 0），它到现尖还差 10 笔。
- 集合差（逐字计数）：`-10` 那枚 40 位的前 8 位 `08e10da9` 在账本命中 **0**、在收件口（含 `_processed` 全部块）命中 **0**；枝名写法 `robust-blind-to-major-10` 在账本命中 **0**。⇒ 线上现在带着这代字节，账本里没有它的一块字。
- 而账本 `L17078` 给 ORD-0432 记的件尖是 `-7` 的 `3e5d160d9d`（上一行已量：8 枚里 4 枚与现尖不等）。以后谁按账本这行复切或审计，取到的是没落地的那代。修正只需一行（把件尖换成 `08e10da963ee6152ad9f0263150d7038408c2aea`）或让车道补一块申报，**都归你落笔，我 0 次代插**。
- 归属按你 09-28 钉的判据（块名在候选流水里 grep，不看枝名前缀）：`major-10` 在 `a6b95d59`（DSH，现测静默 169.1 分）流水命中 9 次，在 `904a042d`（Q，现测静默 335.6 分）流水命中 0 次。

**三、争用队列刷新（同一条尺 r2，18:34 那跑）**
- 小结：活枝 52 枚，其中**预测复切会 ABORT**（至少一枚文件两侧都改过）14 枚。
- 尺自己读到的尖：现尖 98e3c7f4daa3；review/* 368 枚；**落后 <=60 笔的活枝 52 枚**（逐枚对它自己动过的每一枚文件算三侧）
- 仍预测复切会 ABORT 的（按两侧都改过的枚数排）：newlane2-ord0463-screenshot-shell            -r1  头 c4551d67 落后 56 笔  动 48 枚｜单侧改过 43 枚｜**两侧都改过 5 枚** ← b；Q-ord0432-robust-blind-to-major-7            -r1  头 3e5d160d 落后 50 笔  动  8 枚｜单侧改过 4 枚｜**两侧都改过 4 枚** ← ba；Q-ord0432-robust-blind-to-major-3            -r1  头 be98c7d9 落后 58 笔  动  7 枚｜单侧改过 3 枚｜**两侧都改过 4 枚** ← ba；R-ord0437-link-import                        -r9  头 b2f5a296 落后 14 笔  动 52 枚｜单侧改过 49 枚｜**两侧都改过 3 枚** ← b；qoder-0461-member-write-doors                -r1  头 105549bc 落后 14 笔  动 11 枚｜单侧改过 8 枚｜**两侧都改过 3 枚** ← ba；Q-ord0432-robust-blind-to-major-4            -r1  头 4c7caed5 落后 58 笔  动  7 枚｜单侧改过 4 枚｜**两侧都改过 3 枚** ← ba
- 已收敛到「两侧都改过 0 枚」的：N3-ord0457-named-failure-exits               -r4  头 c02c45ab 落后 14 笔  动 90 枚｜单；N3-ord0440-exposure-cells                    -r2  头 ab171b0c 落后 58 笔  动 30 枚｜单；S4-ord0424-multiline-fallback-1441           -r1  头 196f8e1d 落后 25 笔  动 13 枚｜单；S4-ord0454-state-pair-face-1303              -r1  头 cd64bbc3 落后 56 笔  动  9 枚｜单；newlane-ord0444-collections                  -r5  头 f5aa54be 落后  0 笔  动  9 枚｜单；R-ord0417-tap-names-stop                     -r8  头 74d4392b 落后 58 笔  动  7 枚｜单

**四、一条还卡着的裁定（第四次报，我不动手）**
- 车道 `904a042d` 自 12:57 停在 ORD-0431 的甲/乙/丙三选一，现测静默 336 分。甲那枝 `review/qoder-0431-theme-chip-nowrap-r1` 现读仍在原位＝`34d416c90577c0e84d58e20eaa00237d24fd1f40`（提交者 12:21:14，北京），它已量过四档折行归零、右边界 303/343/373/397 不变、代价零，并自报建议甲。裁定权归你，我不代裁，也没催它拆枝拆证据。
- 名册另一条：`9759f1ac`（N2）现测静默 317 分、手上确无单——它 ORD-0456 的交件里自记三处 `NOT_DONE`/`NOT_MEASURED`（最硬那件＝临时枝把上限 20 改 24、同屏证文字与控件同动）。接不接归你。

**五、我自曝两条**：① 15:09 我那把「无人接」尺报 `ORD-0467` 无人接，而你在 15:11 已亲手敲进 `2d2d7428` 的窗口（它流水里该单号命中 17 次）——这张尺滞后实测 2–4 分，读它请当上一分钟；那次读数只进我本地流水、没上过总线，所以这条是口径说明不是勘误。② 我 15:34 起的第一稿把 `-8/-9/-10` 写成「三代零申报 ⇒ 进不了队列」，`merge-base --is-ancestor` 一判就证明最新那代已经在线上，那句后果说反了；这一稿是本帖正文替你把它改对了，第一稿从没发出去过。

边界：只读（GitHub API 尖位与提交时间、`D:/moodle/CityNexus` 内的 merge-base / rev-list / rev-parse / ls-remote 只读预测、账本与收件口逐字 grep、车道流水 mtime）。0 次写账本、0 次代插、0 次移动权威线、0 次落地、0 次改别人的枝、0 次点别人的批准、0 次重启任何进程；没碰 `_preview.db`，没调 `demo/reset`，`:8000 :4781 :4782 :8693` 一个没动。
竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
