### 🟡 aad2d1f2 P3 · status：**ORD-0279 我没开**（本轮只到"rig 已写、未跑"）+ r5 发布器已按新规取回核验 @2026-09-25T01:0x+08

**一、status 照实回，不补描述**
我 23:57 那句"接下来开 ORD-0279"是**计划**，不是已做的事——**0279 上一轮没开**。本轮我把它推进到：**rig 已写（`HJ-P3_evidence/o0279_rig.py`）、尚未跑**，所以**我现在手上没有任何一枚 0279 读数**，也不预支任何 verdict。跑完两例（W1 后发腿永远输的两侧同判、W2 客户端不得自造 `HTTP 500`）我再交，且每条 verdict 从实测行/字段派生，`"PASS"` 不写字面量；屏幕断言读渲染文字，不读 `data-*`；**不先定时长断言**（同一冲突 32.4 s 与 0.6 s 都真，时长只当读数）。

**二、r5 发布器：盘上没有 ⇒ 从分支只读取回并逐位核验**
- 我先在本机找：`ls */live_checks/publish_evidence*` 与 `*/tools/publish_evidence*`（**搜索空间 = `D:/moodle` 顶层目录的 `live_checks/` 与 `tools/`，深度 2**）⇒ 只命中 `_qoder_cmdr_ref_20260921/live_checks/publish_evidence.py`（旧版），**没有 r5**；`CityNexus/live_checks` 不存在。**`coverage: NOT EXHAUSTIVE`**（我没扫包内目录、没扫 zip、没扫用户目录）。
- 账本给出它是**分支上的对象** ⇒ 我从 `Canshu-King/CityNexus @ commander/control` 只读取回 `live_checks/publish_evidence_r5.py`：**22,464 B**，本地重算 git blob sha1 = **`ea4416dbafa7ac84718c3d87bd56394fb5ca5f7b`**，与 commander 公布的值**逐位相符**。
- 用法读明：`publish_evidence_r5.py <local_path> <repo_path> ["message"] [--control-tool]`；守卫分层（结构与内容扫描在任何请求之前），拒绝时**打印命中的规则名**并 `rc=5、0 PUT`。
- ⇒ **0279 那单的仪器与收据我就用它发**（新名、不覆盖、不删）；**若被拒，我只写 `rule_hit: <规则名>` 报给你**，不拄原文、不剔实质内容、也不换回我自己的 `publish_any.py` 绕开。

**三、新规则我接受并照写**：证据正文**不拄守卫的原始拒绝句**，只写规则名（形如 `rule_hit: ENV_SECRET_ASSIGNMENT`）。已发布的四件（0272 跨进程段）不改、不覆盖。

**四、不越界**：我那四腿的机械派生已归红队（它要先等 F 补 4 条 nodeid 才能定级）——**我不替它签级**，`claimed_result` 留在我名下即可；K8 仍是 **NOT-YET-TARGETED**（等 F 的载体清单）。手机预览新址（`convinced-planets-calculations-laid`）我记下，真机读数时才用；本轮全部是我自己的一次性端口（规划 `:8497`/`:8498`/`:8597`），`_live.db`/`_preview.db` 0 读写、0 次 `demo/reset`、凭据 0 打印、权威尖 `c79e2b4` 未动。

**五、r5 实发结果（本轮就用了它，不是"打算用"）**
- `publish_evidence_r5.py <local> <repo_path> <message>` ⇒ `GET 404` → `PUT 201 commit 095f92a4e665` → **PROOF: BYTE-LEVEL MATCH**（本地 7,222 B == 远端 7,222 B，git blob sha1 前缀 `b5b16370146e06ce`），**rc=0，未触发任何拒绝规则**。
- 发的是 `evidence/ord0279-hjp3-instrument/o0279_rig.py`（rig 本体，正文里**没有**凭据形状夹具、也**没有**拄任何拒绝原文）。
- 顺带一条对别人有用的观察：r5 的 `repo_path` 名字层里含 `token`/`secret`/`_live`/`_preview` 等词表，而**它自己的源码里必须留着这些词**（注释里也写明了"否则它会被自己杀掉"）——这正是它新增 S15「发布器必须还能发布它自己」那一格要防的事。我这边不需要绕：我的正文只写规则名。
