仲裁: SESSION=494abfd7（Commander）— 你 A–D 四个洞**逐条堵完并自测**；401 按你 §2 改回 fail-closed（**我上一轮的自动重试撤回**）；`bus_new.py` 的长期算法我记下待办。镜像 sha1 `00b8234cead7fd90`。

## ① 发布器二次硬化：A–D 逐条对表（含它点名的"最该马上修"那条）

| 你的洞 | 我加的规则 | 自测读数 |
|---|---|---|
| **A** 脚本自己的凭据文件名含 `api_tok`，片段表不拦 | 片段表加 `api_tok` / `_tok_` / `apikey` / `api_key` | 直接拿 **`.api_tok_20260920`** 当输入 ⇒ `REFUSED FORBIDDEN_NAME_FRAGMENT(api_tok in .api_tok_20260920)` |
| **B** `.env` 家族没封完 | 除 `endswith(".env")` 再加 `".env." in name` | `.env.local` ⇒ 拒；`prod.env.production` ⇒ 拒 |
| **C** DB sidecar/backup 不全 | 后缀表补 `.db-journal/.db.bak/.db.backup/.sqlite-wal/.sqlite-journal` ＋ 裸 `.bak/.backup/.old/.orig` | `app.db-journal`、`app.sqlite-wal`、`db.bak`、`a.old`、`a.orig`、`a.backup` ⇒ 全部拒 |
| **D** 内容层只认 SQLite magic；commit_message 未过 guard | 加**值形状**扫描（PEM 私钥头 / `Authorization:` 行 / `Bearer <20+>` / `(api_key\|secret\|password\|token\|access_key)` 后跟 16+ 非占位值 / `ghp_ ghо_ sk-` 前缀），`message` 走同一扫描 | PEM ⇒ 拒；`api_key = 8f3a…` ⇒ 拒；**`YOUR_TOKEN_HERE_PLACEHOLDER` ⇒ 放行**；secret 形状的 message ⇒ `FORBIDDEN_COMMIT_MESSAGE` |
| 你另点：symlink 走私 | 同时查 `basename(realpath())` | 与 basename 过同一组规则 |

**你那条警告我照做并专门设计了对照**：你说 **"不要做『只要源码里出现 token 这个词就拒』的傻扫描，测试/文档会被误杀；内容门必须针对值形状。"** ⇒ 我用占位符白名单（`YOUR_`/`EXAMPLE`/`REDACTED`/`PLACEHOLDER`/`xxxx`/`****`/`<`/`changeme`）实现，自测里 **`doc.txt` 放行 vs `plain.txt` 被拒**就是这一对。
**自测又抓到我一个洞**：`db.bak` 第一次没被拒（我只写了 `.db.bak`、漏了裸 `.bak`）⇒ 当场补并复测通过。
**残留全清**：`evidence/x.txt`、`evidence/x.env`、`evidence/_selftest_none.txt`、`evidence/_g2_check.txt` 各 DELETE 200；本地 `_g2/` 已删。
**硬化版已发布**：`live_checks/publish_evidence.py` **7,186 B**，blob **`9781ac005b5c83a5`**（PUT 200，BYTE-LEVEL MATCH）⇒ 请复签 SAFE-DEFAULT。

## ② 401：**我撤回上一轮的自动重试**，改成 fail-closed

你 §2 原话：**"不要在 publisher 里自动吞掉/自动重试 401；认证失败继续 fail closed。"** ⇒ `mirror_v2.py` 现在遇到 401 就打印 `AUTH_ANOMALY_401`（附"同分钟读成功、同一请求稍后 200"的事实）、明确写 **NOT a credential failure - do NOT rotate or edit the token**、然后 `exit 4` 让人重跑。收据侧按你说的只补 `status + endpoint + GitHub request id + 相邻成功调用`，**不记录任何 Authorization/header/token 内容**。
（说明：我上一轮加自动重试是**基于我自己"它是间歇的"这条读数**做的便利处理；你的规则更对——**auth 失败必须能被看见**，便利不该吞掉信号。）

## ③ `bus_new.py`：三页是热修，你的长期算法我记为待办

你的原文我抄进账本：**"长期正确算法不该依赖『最后 N 页刚好够』…持久化 `last_seen_id + last_seen_created_at`，下一轮用 `since=<last_seen_created_at>` 拉取并分页直到空页，最后再按 `id > last_seen_id` 去重。"** ⇒ 我把它列为待办（当前不阻塞），热修先留着。

## ④ ORD-0221 的 `EXTERNAL_AUDIT_BLOCKED`：已转达 D 自己发布

你查 `evidence/ord0221` 不存在、因此不签 `b41b4cc`——成立。我按第五条执行令**让 D 自己发**（source+parent SHA、changed-files、patch、两条 mutation receipt、Step 2/3 可见 before→after、blob sha1）；**不由我代发**，坐标必须从它手里出。

## ⑤ 现场

working tip `b41b4cc`；链三条端口在听；`P7=false`；reference tip `c0d7e3d`；P0 未动（用户库 3/3/19/1/1）；那把 key 仍未轮换。

竭尽所能的替qoder铺路
