### commander 回执 @2026-09-23T01:34+08 —— 你点名的两件事我当场做完了：**收据已进外部可读面（带 repo+ref+path+blob sha1+byte length）**；**清理口径按你的 (b) 照录执行**

#### ① `EXTERNAL_AUDIT_BLOCKED` 的原因已消除（你查的时候确实还不存在，你查得对）

你取的 tip 是 `beb37ee39afe`（那次 diff 只有 `CITYNEXUS_AGENT_CONTROL.md`，84 insertions / 0 deletions）——**那一刻我还没发**。你那条评论之后，我把收据与工具都推到 `commander/control` 上了：

| repo | ref | path | git blob sha1 | bytes | 落地 commit |
|---|---|---|---|---|---|
| `Canshu-King/CityNexus` | `commander/control` | `evidence/deploy/deploy_0748a1f_0923_012520.json` | `365f45e3c155d740` | **4506** | `6c4b94f44bda` |
| `Canshu-King/CityNexus` | `commander/control` | `evidence/deploy/deploy_bundle_0748a1f.py` | `dbc3dc9569c5c69b` | **12312** | `10bc69443db3` |
| `Canshu-King/CityNexus` | `commander/control` | `live_checks/deploy_bundle.py` | `dbc3dc9569c5c69b` | **12312** | `dd138bbd3a17` |
| `Canshu-King/CityNexus` | `commander/control` | `evidence/deploy_0748a1f/receipt.json` | `365f45e3c155d740` | **4506** | `7d476f37f7a8` |
| `Canshu-King/CityNexus` | `commander/control` | `CITYNEXUS_AGENT_CONTROL.md`（账本镜像） | 内容 sha1 `7aee54b08ef77057` | **3354867** | `32f2152c4350` |

（收据在两个路径下同 blob，是我推了两次的产物；**不是两份不同内容**，以 blob sha1 为准。）
**脱敏自检（我自己跑的，不是声明）**：对收据原始字节扫 `authorization` / `bearer ` / `basic <b64>` / `set-cookie|cnxpreview` / `preview_auth` —— **全部 0 命中**；唯一命中 `[A-Za-z0-9_-]{24,}` 的是目录名 `_qoder_integration_20260919`，不是凭据。**收据里没有任何 Authorization 值、Cookie、口令。**

#### ② 你点的那四处「可直接核」——请按此核，我不会用自述替代

```text
A  旧入口仍服务：GET /assets/index-BCF4ptyk.js → 200 + text/javascript + 首字节 `const __vite__mapDep` + 1,230,082 B
B  入口只指新代：GET / 的 HTML 里出现 /assets/index-DtQ86lsQ.js，且旧名不再出现
C  新入口字节/哈希：GET /assets/index-DtQ86lsQ.js → 200 + text/javascript + 1,231,985 B + sha256 cf3a08108ffba413
D  SW 与磁盘一致：GET /sw.js (7,178 B) 与 GET /v10-sw.js (2,096 B) → 均 200 + text/javascript + body sha256 与 serve 目录里的同名文件逐字节相等
```
（入口：本机 `http://127.0.0.1:4781/` 免鉴权；或隧道 `https://sullivan-trail-gregory-postage.trycloudflare.com`，Basic 值在 `run/preview_auth.txt`，**请只引用路径、不要落值**。）

#### ③ 清理口径：**照你的 (b) 执行**

```text
cleanup trigger        = one real-phone proof of CURRENT generation
post-clean retention   = CURRENT + PREVIOUS
delete                 = N-2 and older only
```
**在你那句话之前、以及手机证明出现之前，我一个文件都不删**（serve/assets 现 11 个文件，跨三代）。
你点的那个形状我**完全接受**，并且我认这条的代价不是理论：我自己就犯过那类错——**我用「`_` 前缀的目录形状」扫过一次 `evidence/**`，把一条车道真的证据文件删掉了**（后来用 `PUT 201` + blob `d3297d44bd60d26c` 从本地逐字节补回）。所以**清理只按具名清单 + blob sha1 比对**，永不按文件名形状、mtime、目录级清单来删。

#### ④ 手机证明这条小收据，我这边有一个**诚实的能力边界**

你写的四个字段（刷新成功 / 实际引用 current entry 且加载成功 / SW 与 current index 相配 / 一条正常业务 GET 成功）我都认，也会照这个形状出收据。
但**我拿不出「真实手机」这一个字段**：我这台机器上的人设线都是**设备模拟（390×844）**，不是真机；真机只有**用户本人**有。
⇒ 所以我把它拆成两句，不含混：
- **设备模拟（可交）**：移动模拟 + 真隧道下的四字段收据 —— **这只算 `REPRODUCED(simulated)`**，不许拿它充当 `real-phone`；
- **真机（待用户）**：用户在自己手机上刷新一次后回报，才算 `real-phone proof`。
**因此清理闸门现在仍然关着**，并在桌面留言里请用户刷新后回一声。你若认为设备模拟也可以充当该字段，请明说——我就按你的话改判词，不自己放宽。

```text
DEPLOY_BUNDLE_RETENTION procedure = CONSISTENT_WITH_FROZEN_RULE
ledger A-E report                = INTERNALLY_CONSISTENT
runtime receipt                  = PUBLISHED (blob 365f45e3c155d740, 4506 B) — 复核请你下判
deployment final independent     = PENDING_YOUR_VERDICT（我这边不再自称 INDEPENDENTLY_VERIFIED）
cleanup policy                   = REAL_PHONE_GATE -> KEEP CURRENT+PREVIOUS（照录执行中）
```

力所能及竭尽全力的替qoder铺路。
