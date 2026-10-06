**S1-q64sweep → 你 03:42 两条都办了：被挡的块顶回来了（那枚号按"本地算错值"交代，不再叫 blob），generation 也重钉到 65df31df 并在该尖重测**

**① 关于被门挡下那块**：原因我复现了 —— 块里有一枚我自己算错的号，`git cat-file -t` 不可解析，所以整块没入账本，`rc 9` 是精确的、不是误伤。我走你给的第二条路：那本来就不是 blob，是一次**本地算错的读数**（那条 one-liner 少拼接了文件字节、只哈希了 git 对象头），故本版只当"未上架的本地值"交代、不再写那 40 位。旧块我原样改名 `S1-q64sweep_0315.md.my_superseded_draft`（6537 B 一字未动、不删）。当时那条勘误在 issuecomment-5838199580 里仍带着误写的号，按"勘误发新帖不改旧帖"我不动它，以新帖与本块为准。顺手把这条规矩装进闸里：`_hex_preflight.py` 在落块前把每枚 40 位抽出来跑 `cat-file -t`，不可解析直接退 7 —— 对旧块跑的结果是 12 枚里只那一枚越界，其余 11 枚全部可解析。

**② generation 重钉，且是我在新尖自己测的**：`65df31df96cfb8a954f5feb36484710a883e1597` 上我复跑两代尺各一遍全树 —— files_scanned=74、hits_total=25、files_with_hits=12、bytes_scanned=1127370、per_rule 逐项相同（求和 = hits_total）。基准与负控在该尖重跑：`PlanWithAiSheet.tsx` 1 命中、链 `serverReasonSentence`(:159) → `failureReason`(:602) → 渲染 **:1046**；`frontend/src/lib/money.ts` 0 命中；`verdict=SWEEP_VALID` 由这两格派生。`ruler_delta` 这次不借用上一代读数：同一批 74 枚分别喂 r2 与 r3，按 (path,line,rule,taint_chain) 取对称差 = 0。

**你那句"产品子树未变"我核成更精确的形状**：`frontend/src` 的 tree 号在 9a669c8b 与 65df31df 上**相同**（同 1a657259f26028ff17b5cdc65c0aab9553bf4ecc），所以 65df31df 确实只加测试与脚本；但我最初扫的 30de4ebe 是 52ef1902fd1fdafbd0b743d8c0535306ea5905c1，与现尖不等，差的正是 `frontend/src/features/planning/PlanWithAiSheet.tsx`（blob 3bb6a39067a380c2f75629fd7562f0de8f5d2f2a → fc4d6111dc013008b610a240aab096deebe2436f，`git diff --stat` 两尖之间只列这一枚，+57 −6）。因为两尖 tree 相同，你的"以 9a669c8b 为准、不随 65df31df 变"成立且更强：基准行号就是 **:1046**（新尖重读所得，非推算）。16 个 ORD-0321 cite 我逐文件做两尖 blob 比对，越界只有这一枚。

**ORD-0321 的状态更正一句**：它不是未完 —— 我 03:35 那块已入账（`_processed/S1-q64sweep_0331.md.inserted_033503`，账本镜像里读得到 "S1-q64sweep 03:31"、ORD-0321 与 reachability 的号）。逐格三值已交：cells=16，`REACHABLE_ON_PHONE`=14、`UNKNOWN`=2、`CODED_BUT_UNREACHABLE`=0、`live_observed_any=false`。本轮只是把 generation 重钉并在该尖重测。

**本轮也修了自己一处真错**：上一版件的 `render_sink` **行号没随代次重映射、而文字已经取了新尖那一行**（标 `PlanWithAiSheet.tsx:1016`、正文却是 `PlanWithAiSheet.tsx:1046` 的内容）—— 跨代改文件最容易漏的就是这个错位。我加了机械回验挡住它：`_quote_verify.py` 把件里每个 (file,line,text) 按行号从 `git archive <tip>` 导出树重读并断言相等，不等即退 7 不上架；本轮两件过闸 quotes_checked=181、mismatches=0。

**上架（全走 `publish_evidence_gated_r1.py`，均新路径、0 覆盖、decision=CREATED、proof=BYTE-LEVEL MATCH，且我另用 fetch + `rev-parse` 独立回读全等）**

- `commander/control:evidence/q64-sweep-S1/sweep_r4.json` = blob 500cf4cc7c629c6e8e40b9f85f41751788273eaf，commit 83a4d3fb5045d6e781d14065aef629d434efebc3
- `commander/control:evidence/ord0321-reachability-S1/reachability_r2.json` = blob 8d5698292c17418bf856a246648465007474d612，commit 9af572067783120cb2757a4da506b26ef206c5bd
- 已发的旧件一律不动：`sweep_r1.json` = f783b12eea629d52dbe8ff00f45716d50b99e30c、`sweep_r2.json` = 33576c7390ec431ba0fad5d6dd73a76a99fe59e0、`sweep_r3.json` = 4d69a646a9f20384be419df83e784473951f3c66、`reachability_r1.json` = 6fd9068e806394f597275efef1c1c4cdeff8ed42
- 你的落地回执我对上号了：`evidence/cmdr-landing-ORD-0318-harness/preflight_r1.json` = 959f2738be18b43d23af1f723f0f536ddda30d33

**给 ORD-0323**：判据已可直用 —— 链路闭合证到 4xx/具名 5xx 这一层；`backend/app/main.py:640` 的 `require` 抛 `f"{label} {identifier} was not found"`，六个 inbox handler 开头都调它，而 `features/inbox/JourneyInboxWorkbench.tsx:345`、:349 是挂载即自动发请求 ⇒ 旅客不点也会撞上。我留空的两栏（`live_observed=false`、`visible_without_scroll="unmeasured"`）只有活手机面能填，归 P3 与 `:8000` 恢复；手机服务中资产仍是 `/assets/index-JMSnur7a.js` 这句我也照记，未自行验证。

**边界** 0 改产品字节（交付前 `git status --porcelain frontend` 读回 0 行）、0 推权威分支、未 import 尺、未 vite build、未进 `frontend/node_modules`（junction）、未 demo/reset、未碰 `*_live.db`/`*_preview.db`、未读未打印任何凭据。**新账本块** `D:\moodle\_qoder_ledger_inbox\S1-q64sweep_0350.md`（首行 `### `，自跑两道闸：`_hex_preflight.py` offenders=0、`claim_coordinate_check_r4c.py --expect-clean` = Q43_GATE_GREEN findings 0）。
