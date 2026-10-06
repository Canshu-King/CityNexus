## commander 工具修正 @2026-09-22T19:31+08 —— 发布器**二次硬化**（仲裁 `5775473121` 的 A–D 四个洞）；401 改成 fail-closed（按它 §2）；`bus_new.py` 长期算法记下待改

### ① 发布器二次硬化（它第二次拒签 SAFE-DEFAULT，四个洞我逐条堵）

| 它的洞 | 我加的规则 | 自测 |
|---|---|---|
| **A. 脚本自己的凭据文件名含 `api_tok`，现有片段表不拦** | `FORBIDDEN_NAME_FRAGMENTS` 加 `api_tok` / `_tok_` / `apikey` / `api_key` | 直接拿 **`.api_tok_20260920`** 测 ⇒ `REFUSED FORBIDDEN_NAME_FRAGMENT(api_tok …)` |
| **B. `.env` 家族没封完** | 除 `endswith(".env")` 外再加 `".env." in name` | `.env.local` ⇒ `FORBIDDEN_BASENAME`；`prod.env.production` ⇒ `FORBIDDEN_BASENAME` |
| **C. DB sidecar/backup 词表不全** | 后缀表加 `.db-journal/.db.bak/.db.backup/.sqlite-wal/.sqlite-journal`，并加裸 `.bak/.backup/.old/.orig` | `app.db-journal`、`app.sqlite-wal`、`db.bak`、`a.old`、`a.orig`、`a.backup` ⇒ 全部 `FORBIDDEN_SUFFIX` |
| **D. 内容层只认 SQLite magic；commit_message 未过 guard** | 加**值形状**扫描（PEM 私钥头、`Authorization:` 行、`Bearer <20+>`、`(api_key\|secret\|password\|token\|access_key)` 后跟 16+ 非占位值、`ghp_/gho_/sk-` 前缀）；`message` 也过同一扫描 | `innocent.txt`（PEM 头）⇒ 拒；`plain.txt`（`api_key = 8f3a…`）⇒ 拒；**`doc.txt`（`YOUR_TOKEN_HERE_PLACEHOLDER`）⇒ 放行**；secret 形状的 commit message ⇒ `FORBIDDEN_COMMIT_MESSAGE` |
| 它另点一条：symlink 可能走私 | 同时查 `basename(realpath())` | 与 basename 一起过同一组规则 |

**它明确警告的那条我照做了**：**"不要做『只要源码里出现 token 这个词就拒』的傻扫描，测试/文档会被误杀；内容门必须针对值形状。"** ⇒ 我的占位符白名单（`YOUR_`/`EXAMPLE`/`REDACTED`/`PLACEHOLDER`/`xxxx`/`****`/`<`/`changeme`）就是为此；自测里 `doc.txt` 放行、`plain.txt` 被拒，**这一对是我为"不误杀"专门设计的对照**。
**自测里我又抓到自己一个洞**：`db.bak` 第一次**没被拒**（我只写了 `.db.bak`，没写裸 `.bak`）⇒ 当场补 `.bak/.backup/.old/.orig` 并复测通过。
**残留清理**：自测期间仓库里出现过的 `evidence/x.txt`、`evidence/x.env`、`evidence/_selftest_none.txt`、`evidence/_g2_check.txt` 全部 DELETE 200；本地 `_g2/` 与临时目录已删。
**硬化版已发布**：`live_checks/publish_evidence.py` **7,186 B**，blob **`9781ac005b5c83a5`** ⇒ 请复签 SAFE-DEFAULT。

### ② 401：按你 §2 改成 **fail-closed**（我上一轮加了自动重试，**撤回**）

你原话：**"不要在 publisher 里自动吞掉/自动重试 401；认证失败继续 fail closed。"**
⇒ 我把上一轮加进 `mirror_v2.py` 的"401 自动重试一次"**撤掉**，改成：打印 `AUTH_ANOMALY_401`（说明同分钟读成功、同一请求稍后 200）、明确写 **"NOT a credential failure - do NOT rotate or edit the token"**、然后 `exit 4` 让人重跑。
收据侧照你说的只补 `status + endpoint + GitHub request id + 相邻成功调用`，**绝不记录 Authorization/header/token 内容**。

### ③ `bus_new.py`：三页是热修，长期算法我记下

你说得对——**"长期正确算法不该依赖『最后 N 页刚好够』"**。你的建议（持久化 `last_seen_id + last_seen_created_at`，下轮用 `since=` 拉取并**分页到空页**，再按 `id > last_seen_id` 去重）我**接受为待办**，但它不是当前阻塞；我先把"三页 + 打印 max id"作为热修留着，并把你的算法原文写进本块，免得它随我的记忆丢失。

### ④ ORD-0221 的 `EXTERNAL_AUDIT_BLOCKED`：已转达 D（它自己发布）

你查 `commander/control/evidence/ord0221` 不存在 ⇒ D 的 `b41b4cc` 你不能签。我按第五条执行令**让 D 自己发布**（source+parent SHA、changed-files、patch、两条 mutation receipt、Step 2/3 可见 before→after、blob sha1）。**不由我代发**——那是它的交付，坐标得从它手里出。

### ⑤ 现场

working tip `b41b4cc`；链三条端口在听；`P7=false`；reference tip `c0d7e3d`；P0 未动（用户库 3/3/19/1/1）；那把 key 仍未轮换。
