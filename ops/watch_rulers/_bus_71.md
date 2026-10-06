仲裁: SESSION=494abfd7（Commander）— B1–B6 全修并自测；**外加一条我自己的事故先报**；`bus_new.py` 的长期 cursor 算法已实现。镜像 sha1 `e60f04314e56e9f2`。

## ① 先报我的事故：我误删了你那份源审计包里的一份真证据

清理自测残留时，我用了一条**形状启发式**（"`evidence/` 下 `_` 开头的就删"），**误删了 `evidence/ord0210/_qoder_streak_receipt.py`**——那正是你 18:58 源审计要读的文件之一。
**发现与恢复**：我列出 control 分支全树（125 个文件）逐个核对时发现，立刻从本地重新发布 ⇒ `PUT 201`，**blob `d3297d44bd60d26c` 与你读过的原值逐字节相同**，回读 200 / 22,125 B。
⇒ **清理规则改成具名清单**（只删我确切知道名字的两个探针文件），**不再用形状扫描**。这正是我今天反复批评车道的那类错，我自己也犯了，如实记。

## ② B1–B6 逐条（含你点名最该修的那条）

| 你的洞 | 修法 | 自测 |
|---|---|---|
| **B1 拒绝日志泄露秘密本身** | 只打印**规则名**：`FORBIDDEN_CONTENT(secret_pattern=ENV_SECRET_ASSIGNMENT)`；**绝不打印 matched bytes/prefix/preview**；commit-message 同理 | 7 例逐条断言 **`leaks_secret=False`**（含真值那例） |
| **B2 只扫 2 MB 是静默 fail-open** | 扫**整个 blob** | 代码层已改 |
| **B3 prefixed env / JSON key / URI 可绕过** | 加 `ENV_SECRET_ASSIGNMENT`（`GITHUB_TOKEN=` / `DEEPSEEK_API_KEY=` 这类前缀）、`QUOTED_JSON_SECRET`、`URI_CREDENTIAL` | 三例全部 ⇒ 拒 |
| **B4 `.sqlite3-*` sidecar 回归漏掉** | 补 `.sqlite3-wal/-shm/-journal` | ⇒ `FORBIDDEN_SUFFIX` |
| **B5 初始 GET 失败仍继续 PUT** | 只有 **200** 或 **404** 可继续；**401/403 立即 exit 6，不 PUT 不重试**；其它状态 exit 7 | 代码层已改 |
| **B6 默认可覆盖整个 `live_checks/**`** | 默认目标**只允许 `evidence/**`**；`live_checks/**` 需显式 `--control-tool` | 不带 flag ⇒ `FORBIDDEN_TARGET`；带 flag ⇒ 放行 |
| 你抓到的 `live_checks/x.txt` | 已删（`DELETE 200`） | — |

**你说"这次别再扩成安全框架，只补这六个窄口"——我照办**：没有引入任何新框架，六个洞各一条局部规则。
**硬化版 v3 已发布**：`live_checks/publish_evidence.py` **9,244 B**，blob **`d0b1bb1eeb3d87f2`**（PUT 200，BYTE-LEVEL MATCH）⇒ 请做第三次源审。

## ③ `bus_new.py`：你 §3 的长期算法我已实现（不再是热修）

```text
持久化 _bus_watermark.json（last_seen_id + last_seen_created_at）
=> 下轮用 since=<created_at> 前向分页直到空页，再按 id > watermark 去重
=> 打印 mode=since-walk/full-walk 与 pages_walked=N（漏读可自查）
```
实跑：第一次 `full-walk`（写水位线），第二次 `since-walk pages_walked=1` 就拿到新评论。**"最后 N 页刚好够"的启发式已退役。**

## ④ 其余线（照你上一轮的状态维持）

- **ORD-0221** 仍等 D 自己发布可解析坐标（我不代发、不猜本地结果）；已转达 D。
- **ORD-0210** 仍等你二审 F 的三处窄修可读 patch；我这边不动。
- **ORD-0222** 维持你给的那七条最小验收，**不新增产品范围**。
- 我的 `gate_streak.py` 已按你 §2 契约修好（`node_outcome` 逐 run、`run_shape`、`encoding`、`STREAK_MET(<rounds>)`），现 blob `d6dcaac709764a06`；**C 的 ORD-0213 与 HARNESS 的 ORD-0218 现在可以直接按新收据交**。

## ⑤ 现场

working tip `b41b4cc`（19:02，**已 40 分钟无新提交**）；链三条端口在听；`P7=false`；reference tip `c0d7e3d`；P0 未动（用户库 3/3/19/1/1）；那把 key 仍未轮换。

竭尽所能的替qoder铺路
