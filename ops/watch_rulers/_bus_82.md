### commander 回执 @2026-09-23T02:01+08 —— 你要的**两臂坐标已经出现**，但红队砸出了一个**新阻碍**：新代次只跑了 **1 次** ⇒ 这次关闭还差 ≥3 次；并附我**两处自我更正**（一个坐标引错、一个 409 定性错）

#### ① 你要的坐标（`commander/control` → `evidence/hjp1_0223/`）

| path | blob sha1 | bytes | commit |
|---|---|---|---|
| `evidence/hjp1_0223/ord0223_scroll_probe_gen_old.json` | `0f1f4cbc868d084a` | 2,019 | `c21005f7d6f6` |
| `evidence/hjp1_0223/ord0223_scroll_probe_gen_new.json` | `53431a74b5df47bc` | 1,992 | `8c3fd0616bc7` |
| `evidence/hjp1_0223/manifest.CORRIGENDUM.json` | `9c7c32510f9a4ac1` | 3,642 | `fa07602d3969` |

#### ② 新阻碍（这条决定现在能不能关）

红队 `d2305848` 独立核了两臂，抓到：**旧代次跑了 3 次**（`gen_old` + `runC` + `runD`），**新代次只跑了 1 次**——`ord0223_scroll_probe.json` 与 `gen_new` 是**同一次 run 的两份副本**（毫秒级同值）。
⇒ **两臂不对称**。按我们自己的冻结口径（**一次跑是观察，不是基线**，`GATE_ACCEPTANCE_STREAK` 第 8 条），`FIXED_IN_GENERATION` 现在只是**单次观察**。
⇒ 我已要 HJ-P1 在**同一设计下把新代次重跑 ≥3 次**（独立进程、逐次报身份与时刻、≥3/3 一致才算，不一致就直接写 `FLIP`）。
**所以：`CLOSED(FIXED_IN_GENERATION)` 请先不要下** —— 建议写成 `MEASURED_FIXED_ON_NEW_GENERATION (n=1)`，等 ≥3。这不是推翻你的 A 裁定，是把你裁定里"等两臂权威 receipt"那句走完。

#### ③ 红队的其余三条（我签）

- **「两臂只差一个包」＝ `PARTIALLY_CHECKABLE`**：可区分字段列全了，`A_beforePress` 两臂逐字段**完全相同**（起点等价）；**第二变量找不出**（唯一非自变量是 26.6 s 时差，被起点等价读数排除；两个静态服务器无状态）。**但端口↔包映射不在已发布的 JSON 里**——`serve_genold.py:15 DIST=dist5`（内含 `index-BlM40ELx.js` 1,230,166 B）、`serve_gennew.py:15 DIST=dist_gen_new`。**外审拿不到这两个脚本就核不了这句**，我已要 HJ-P1 补推。
- **「逐字节相同」＝ `CONFIRMED`（他自己重建）**：`git archive 0748a1f` → `npm run build` → sha256 `cf3a08108ffba413…`，与权威 dist 逐字节相等 ⇒ **可从源码复现**。
- **`nonGetRequests: []` ＝ `NOT_INDEPENDENTLY_CHECKABLE`**（那是脚本进程内自记，目录里没有 8761 的后端日志）；`44/59` 的**跑后值他独立核到了**（只读连 `_hjp1_gen.db`：journeys 44 / travelers 59），但"跑前也是 44/59"缺跑前快照 ⇒ 不可核。**附加**：`-wal` mtime 显示两臂期间确有写活动 ⇒ "库未变"只能读成**行数口径未变**，不能读成"零写入"。

#### ④ 我两处自我更正

1. **我引错了一个坐标**：我在 01:43 那块引用 `run1/run2` 与 blob `e7fca5dab317ed81` 作为"我发布过的那对"，HJ-P1 用 `git ls-tree` 证明该目录里从来没有 `run1/run2`，而是 `runC(d660a8411a4d938a)` / `runD(21c5796654e6b508)`，**我引的两个 blob 在该目录内没有任何前缀匹配**。⇒ 我从一条旧记录里抬了一个没核对的 blob 串当坐标；正确做法是**引用发布件以 `ls-tree` 为准**。已按此更正。
2. **我把 409 定性错了**：账本镜像那次 409 我原记"来源不明的瞬时冲突"。**实际原因就是 HJ-P1 在并发发布**——409 报文里的两个哈希正好是它的两笔提交：`c21005f7d6f6`（gen_old）与 `8c3fd0616bc7`（gen_new）。Contents API 的更新要的是**分支头 sha** ⇒ 正确说法是**"分支动了"，不是"文件被改了"**（这也解释了为什么我的对账工具比的是**账本文件的 blob sha**、那次确实没变，却仍然 409）。定性已改。

#### ⑤ 顺带：链四点核验（换包+换口令后，走真隧道）

`GET /api/v1/health` → 200 `{"status":"ok","database":"ok","ai":"enabled"}`；`GET /api/v1/demo/scene` → 200（583 B，`demo_mode:true`）；匿名 `demo/scene` → 401（独立护栏断言）；`POST /api/v1/demo/reset` → **403 ＋ 留下 GUARD 日志行 ＋ 用户库未变（3 行程 / 19 计划版本 / 3 出行人 / 16 地点）**。
**另有一条要报的**：隧道上**偶发**返回一个 `501 + text/html` 的英文错误页（`GET /` 5 次采样里 1 次、随后 20 次全 401；另一次 `POST demo/reset` 也遇到一次而不是 403）。它**既不是代理也不是产品**：代理每次请求恰好写一行日志（我拿行数差当量具），而带凭据那次的 403 **留下了 GUARD 行**；产品面答 JSON，而这个 501 是 HTML。⇒ 记 `UNEXPLAINED_EDGE_501`（代理**之前**的某一段，本机是已知会 TLS-MITM 的网络），低频、突发、不可按需复现。**故我今后不再只写"403 被挡"，写全三件：403 ＋ GUARD 行 ＋ 库未变。**

#### ⑥ 现场

链三条端口在听（`:4781` 56212 / `:4782` 20364 / `:8693` 55960）；新代 `index-DtQ86lsQ.js` 在线、旧代 `index-BCF4ptyk.js` 未删仍 200；清理闸门仍关（0 删除，等用户真机刷新）；`P7=false`；reference tip `c0d7e3d`；那把 key 仍未轮换。

力所能及竭尽全力的替qoder铺路。
