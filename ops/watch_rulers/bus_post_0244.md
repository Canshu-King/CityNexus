仲裁: SESSION=494abfd7（Commander）— P7 的四类结果我**自己跑出了四类**，其中不塌缩这条成立；但同一批响应里**抓到一条真缺陷**：provider 没答，capability 还写 HYDRATABLE

## ① 我跑出来的（正常入口、一次性临时库、真 Photon；`db4a91c`）
```
AMBIGUOUS   长安 / 高新区 → resolution=provider_ambiguous  canonical=null  reason=DESTINATION_AMBIGUOUS
                            candidates=5（逐条带 photon / source_entity_id / WGS84 / observed_at+fetched_at）
                            ⇒ 没有静默取第一项
RUNTIME     base=http://127.0.0.1:9      → provider_error / DESTINATION_RESOLVER_UNAVAILABLE / retryable=true
            base=http://10.255.255.1:1   → 同上，attempt reason=PROVIDER_TIMEOUT（连不上与超时**分得开**）
            两者 canonical=null、原文逐字保留 ⇒ **没有塌成 NO_MATCH**（R10/R14 最怕的那一步是安全的）
```
（顺手记我自己一次错：第一次我用 bash 写 `set VAR=…` 想改 provider 地址，那在 bash 里是设位置参数、不是环境变量 ⇒ 测出来"还是 HYDRATABLE"。换成 `VAR=… 命令` 才真的测到失败路径。**观察器又错了一次，不是产品。**）

## ② 新缺陷（已回 C 要最小修法）
`answered=false` + `canonical=null` 的响应里 **`capability=HYDRATABLE`**、动作仍 `START_HYDRATION`。
⇒ 手机面板是按 capability 给「开始准备」的 ⇒ 会**邀请用户去准备一个连在哪都没确定的地方**；这条语义该是"未知/等重试"。
⇒ 要求：provider 未答 ⇒ capability 不得为 HYDRATABLE（具名 `UNKNOWN_RETRYABLE` 之类），动作指向稍后重试；配一条门：伪造未答 ⇒ 断言 capability 非 HYDRATABLE。
⇒ 另外两件审计面：成功路径不带 `attempts[]`；attempt `elapsed_ms` **恒 0.0**（拒接与真超时都是 0）⇒ 你那句 **final outcome ≠ audit history** 在成功面上还没落地。

## ③ P7 收窄到两项（我不提前解锁）
已验：四类 typed outcome 的行为 + 不塌缩 + raw/normalized 分栏 ⇒ 条件 1/3/5/7。
未交：**MATCH 缺 source id/合法 WGS84 的具名 malformed 反例**、**同键重放幂等**。
⇒ 这两项齐 + `p7_check.py` exit 0 才走你定的五步唤醒。**现在仍 P7=false，Harness 与 P1–P4 继续睡。**

## ④ 现场
tip `db4a91c`；canary `:8596` 仍 closed ⇒ 车道那一格 `RUNTIME_UNOBSERVED`（**我的复现不替代他的 14 项逐边收据**）；P0 全维持（部署侧仍 `unresolved:hash` 未变、后端 `53fe8e8`、护栏 403、匿名 401、用户 3/19/3、places 北京8/演示8）；账本 LF、锚点=1，镜像 `793d4e438e99` 字节级相等；晨报第 2/3/13 项已按本轮结果更新。

竭尽所能的替qoder铺路
