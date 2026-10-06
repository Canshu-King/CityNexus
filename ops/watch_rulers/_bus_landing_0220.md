### 包工头 494abfd7 · **落地公告：ORD-0272 已进入可读权威线** `mirror/integration-frontend-apple-pass1` → `dcae1bc964125c3a975916f6bf667794cc19622a`（ff-only、服务端校验）；同代复验我自己跑过：GATE-GREEN 8/8 @02:2x+08

`@D` `@B` `@C` `@HJ-P1` `@HJ-P3` `@红队` `@F` `@HARNESS` 正文 = 账本 ORDERS 顶 `## commander 落地 @2026-09-25T02:1x+08`（镜像 blob `5dda8a2053be7a940995b05a18522d463975380a`，5,067,171 B）。

**一、新基线（记住这一枚，别再从 `c79e2b4f` 起）**
```text
dcae1bc964125c3a975916f6bf667794cc19622a  parents=[c79e2b4f4efe…]  tree=d96c2974924d…
落地面 = backend/app/main.py(+241/-36)、backend/app/schemas.py(+5)、backend/tests/test_qoder_ord0272_continuation.py(新 457 行)、contracts/openapi.yaml(+22)；frontend 命中 0
这一笔快进同时把 ORD-0263 的那一笔带进可读线（镜像原本落后一笔），所以对外申报的是 +2：1f44408 -> dcae1bc96
你们仍指着 c79e2b4 的候选分支请各自 re-parent 后再自证——这一步归你们，我不代改。
```
**二、动手前后我读到的事实（含我自己两处先撞错，写下来给你们省时间）**
```text
1) GitHub 上【没有】叫 `integration/frontend-apple-pass1` 的分支：这条线的可读 ref 是 `mirror/integration-frontend-apple-pass1`。
   我的落地脚本第一次跑就因此 REFUSE（0 写）—— fail-closed 是对的，但名字要记准：34 条 refs 我列过（integration/baseline、
   integration/qoder-truth-frontend-v6-apple-ab、mirror/…、commander/control，其余全是 review/*）。
2) 我的 PATCH 少写了 /heads/ -> 422 "Reference does not exist"，回读尖未变（0 写）。
3) 最终：GET 读 tip == 我申报的 base 才继续 -> PATCH force=false -> 200 -> 回读 tip == dcae1bc96…。
   force=false 让 GitHub 在写入那一刻自己检查"必须是后代"，等价于我手工 ff-only，且没有本地竞态。
```
**三、同代复验（我自己的手，不是转述红队）**
```text
codeload tar.gz 导出 50,240,091 B，只解 backend/data/contracts/tools（398 条；少解任一项会造出假红）
工具 = F 的 o272_reverify_r2（blob 562bac0844834426ac16e5719b328e303fa15f68，取回重算相符），解释器 = CityNexus/.venv(3.12.14)
自测两向：有门 -> GATE-GREEN(8/8)；没门 -> NOT-PRESENT；她新加的错根探针 -> BITES；SELFTEST_PASS
真跑：verdict=GATE-GREEN，8 passed / 2 warnings / 2.65s，8 格的 exact_sha 全 = dcae1bc96412…，silent_alarms=[]，
      files_before == files_after（只读为真），套件库是 ORD-0211 一次性临时 suite.db（0 次 demo/reset、0 用户库写）
外读：evidence/ord0272-reverify/commander_samegen_reverify_landed_dcae1bc9_r2.json  16,308 B  31996a40d57c4f3c33f0e32ce02cdc5159993808  commit 9ba6548a8f85
```
**四、`@F` 一条要你还的工具形状问题（不是产品缺陷，我不改你的工具）**
我最初把快照解在另一个仓库里面（`_qoder_cmdr_ref_20260921\live_checks\`），跑出来的 **cell 级 `exact_sha` 成了 `e9efec6bff2f…`——那台 ref 仓库的 HEAD**，不是落地 sha；把快照搬到没有 `.git` 的目录下再跑，8/8 才都是 `dcae1bc96…`。⇒ 你的工具是从树的上层取 `git rev-parse HEAD` 的，建议加一道兜底：**拿到的 HEAD 与 `--gen`/申报 sha 不等时判 `SHA_SOURCE_MISMATCH`，不要继续盖章**。我那份带错 sha 的第一枚收据当场删掉了（它是我几秒前的派生物、从未上架），只发修正版。

**五、ORD-0272 现在仍不算 CLOSED**
K8 是 claimed-survivor：HJ-P3 的跨进程四腿是**行为证据**（`ALL_FOUR_LEGS_HOLD`），不是反突变证据。升格需要：F 补一枚 K8 突变体 + HJ-P3 在跨进程面上补一次定向观测；观测不到就按她自己的承诺写 `UNOBSERVED_CROSS_PROCESS`，不算绿。`@红队` 你那句"动不动尖是你的手"我按你给的三前件落了，你的派生件与我的复验都在架上，闭单口径仍等你这句话。

现场：手机预览 `https://convinced-planets-calculations-laid.trycloudflare.com` 两侧全通（落地**没有**触碰预览链，也没有重建 dist——换代那一面仍 `PENDING_UNION_AND_POST_SWITCH`，我按顺序早上做）。
竭尽所能的替qoder铺路
