## commander 收口 @2026-09-23T01:51+08 —— **发布器 SAFE-DEFAULT 落地并已双向驱动过**（401 读回 = `PUBLISHED_UNPROVEN`，不再被误报成"哈希不符"）；这是仲裁一直挂着没签的那一格

### ① 原来错在哪

`publish_evidence.py` 的 POST-PUT 复核循环里，任何一次读回**不是目标 sha** 都会被落到循环末尾那句 `MISMATCH after retries`，**包括 401/403**。后果：一次**认证/传输异常**被报成**哈希不符**——"没验成"与"验错了"共用一句话，而这两件事的处置完全相反（前者重跑取证明，后者说明上传的内容不对）。

### ② 现在的形状

```text
读回 GET 得 401/403   → 打 AUTH_ANOMALY_TAIL_READ(<st>)（含 endpoint），继续重试
三次都 401/403 且没拿到任何 dict  → PUBLISHED_UNPROVEN：PUT 已 2xx（给 commit），件**已在分支上**，
                                   但**字节级证明未取到**；这是**读路径**的认证异常，
                                   NOT a hash mismatch，NOT a credential failure —— **不许动/轮换 token**，
                                   重跑本发布即可取证明。退出码 7。
读回 200 但 sha 不等    → 仍是 MISMATCH，退出码 4（真正的失败）
```
（对齐仲裁 `5775473121` §2，与 `mirror_v2.py` 同一口径，不再两把尺。）

### ③ 两向驱动（不是读代码得出的，是**把桩塞进去跑出来的**）

那个 401 分支**没法用真 token 到达**（坏 token 会先在 B5 的初始 GET 上 fail-closed，根本走不到 PUT）⇒ 用替换 `call` 的桩把两条尾路径都驱动起来：
```text
case auth401   （首次 GET 404 通过 → PUT 201 → 读回 401×3）  expect 7  got 7   OK
case mismatch  （首次 GET 404 通过 → PUT 201 → 读回 200 但 sha 不同）  expect 4  got 4   OK
```
**一条自曝**：这个桩的第一版**自己写错了**——它让所有 GET 都返回 401，于是工具在**初始 GET 上 fail-closed 退出 6**、根本到不了尾部，跑出 `expect 7 got 6 BAD`。**那不是工具的缺陷，恰恰证明 B5 的 fail-closed 在按设计工作**；把桩改成"只有读回 GET 才 401"之后两向皆过。控制臂自己出错也要报，否则这一格就是自证。

### ④ 坐标（外部可读）

| ref | path | blob sha1 | bytes | commit |
|---|---|---|---|---|
| `commander/control` | `live_checks/publish_evidence.py` | `01f563e87795842f` | 10540 | `1b097e1d9e19` |
| `commander/control` | `evidence/deploy/publisher_safedefault_selftest.py` | `b878abedb53b71d8` | 2306 | （见上表同批 PUT） |
| `commander/control` | `evidence/deploy/publisher_safedefault_selftest_0923_015051.txt` | `3b347250c9e02af5` | 1344 | 同上 |

### ⑤ 现场

链三条端口在听（`:4781` 56212 / `:4782` 20364 / `:8693` 55960）；新代 `index-DtQ86lsQ.js` 在线、旧代 `index-BCF4ptyk.js` 未删仍 200；清理闸门仍关（0 删除，等用户真机刷新）；`P7=false`；reference tip `c0d7e3d`；P0 未动（3 行程 / 19 计划版本 / 3 出行人 / 16 地点，01:28 只读复核）；那把 key 仍未轮换。
