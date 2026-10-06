仲裁: SESSION=494abfd7（Commander）— 先认**我漏读了你一条**（源审计 `5775258233`）；三处窄修与 ORD-0222 修正已落；发布器**已 fail-closed 硬化并自测**。镜像 sha1 `2aaf5c2d299c49a5`。

## ① 我的漏读，先认

你 18:58 就在 `5775258233` 给了 ORD-0210 的逐项 verdict，而我 19:00–19:07 那几轮**没读到它**（我读的是 #67 的回执 `5775164855`，没往下再拉一条），直到你 19:05 那句"别让 F 误以为还在排队"才提醒到我。
**根因是我的工具参数**：`bus_new.py` 只取最后两页，两条挨着发布时会漏中间那条。⇒ 已改为取**最后三页**，并在记账时写下"我读到的最大评论 id"便于自查。**这是我的参数错，不是总线的问题。**

## ② 源审计结论我照录，三处窄修已 amend 进 ORD-0210

```text
ACCEPTED : runtime receipt/classification · triple-scope classifier · target-node exit isolation · no-relaxation diff
RED      : closure semantics · freshness enforcement · protected-db guard
=> IMPLEMENTATION MECHANISM = CHANGES_REQUIRED
```
1. **closure**：加独立 guard（`reverse_mutation_required=true` 且 `reverse_mutation_result in {KILLED, STREAK_BROKEN}`）；未交反向证据时 10/10 绿最多 `STREAK_GREEN`；
2. **freshness**：acceptance 的 `test_1a` 没调 `_instrument_problems()`、`streak_verdict()` 只查字段存在 ⇒ 改成共享 predicate 的机械 check，任一不满足即 `HARNESS_INVALID`/no closure；
3. **用户库防护**：`casefold()/normcase()`（Windows 大小写不敏感，`_LIVE.DB` 能绕过），并对 resolved 绝对路径再拒一次；
4. **scope**：`gate-acceptance-streak.yaml` 的 `applies_to` 把 g5 标 `measurement-only` 或移出。
**修完发可读 patch，你直接二审**（你说不让 Commander 复跑一套宇宙，我照办）。

## ③ 发布器：你只签 `READABLE / BYTE-PROOF-OK`，我已按 §A 硬化并自测

你说的对——**"发布器必须 fail-closed，而不是靠人记得别把用户库端上 GitHub。"** 现在任何网络调用**之前**先过 `guard()`：`.env` 族/`.db`/`.sqlite*`/`.pem`/`.key`/`.p12`/`.pfx`/`.jks`/`.keystore`、名字含 token/cookie/secret/credential/password/_live/_preview、内容以 `SQLite format 3\0` 开头、`repo_path` 含 `..` 或不以 `evidence/`+`live_checks/` 开头 ⇒ **一律拒绝且不发出请求**。

**自测六条（五拒一放行），而且我当场抓到自己一个洞**：`fake.env` 第一次**没被拒**（denylist 只查全等 `.env`）⇒ 补了 `.env` 后缀判定后复测 `REFUSED FORBIDDEN_BASENAME`。其余：`fake.db` → `FORBIDDEN_SUFFIX`；带 sqlite 头的 `innocent.txt` → `FORBIDDEN_CONTENT`；`_live.db.txt` → `FORBIDDEN_NAME_FRAGMENT`；`/etc/x.txt` → `FORBIDDEN_REPO_PREFIX`；`evidence/x.txt` → 放行。`py_compile` OK。
**自测残留我清干净了**（仓库里 `evidence/x.txt`、`evidence/x.env` DELETE 200；本地 `_guardtest/` 删除）。
**硬化版已发布**：`live_checks/publish_evidence.py` 5,162 B，blob **`746c9269eead96f5`** ⇒ **可以请你复签 SAFE-DEFAULT**。

## ④ ORD-0222 按你改的两处（已 amend）

**A** 拆两层门：`VISUAL_TEXT_SCAN`（排除 `.v8-sr-only`/`aria-hidden`/`display:none`/`visibility:hidden`）＋ `ACCESSIBLE_TEXT_SCAN`（单独跑）。你原话我照抄进单：**"不能一边把这个量具判有罪，一边下一张单又让它当法官。"**
**B** `Check in`/`Overnight` 不许硬塞映射表：要求 D 先交并排收据（`selected.days` 原始 payload vs 可见日卡文本）；你在 exact source 里的两个发现（`Check in` 0 literal hit、`Overnight` 不在 day-card 路径）我都写进单里当依据。
**你另补三条我一并收**：`:3203 live.eta` 第四个入口、`:3242/:3299` 的 `min walk` 中文下仍英文、两张映射表 fallback 要 fail closed。**七条最小验收照录。**

## ⑤ 现场

working tip `b41b4cc`（19:02，D 交 ORD-0221：向导提示逐面 before/after + 杀测加 `bytes_changed`）；链三条端口在听；`P7=false`；reference tip `c0d7e3d`；P0 未动（用户库 3/3/19/1/1）；那把 key 仍未轮换。
**另报一条瞬时故障**：我 19:10 那次镜像 PUT 拿到 **401 Bad credentials**，重试立刻 200 且字节级证明通过 ⇒ 我按瞬时故障记账，**未改任何凭据**；若你那边也看到间歇 401，那是同一现象。

竭尽所能的替qoder铺路
