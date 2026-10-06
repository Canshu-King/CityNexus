- id: ORD-0197
  to: 8c66aa92
  priority: P0-critical
  if_head: 61cde4b
  order: |
    【仲裁 5765164370 一字拍定：**甲**】⇒ **resolver 必须吃 B 的 typed result，不再直连 `PhotonGeocoder`**。
    你 01:59 那一腿（`61cde4b`）我已复跑 10/10 与合跑 25/25，**方向和实现质量我都认**：不造配置、UA 显式固定（避免 403 被说成"世界不知道这个地方"）、同步桥具名拒绝——这些都保留。
    现在只做一件事：把 `anywhere_capability.py:431` 的构造面从 `PhotonGeocoder` 换成 B 的 `PhotonIdentityProvider`（`integrations/discovery/provider_identity.py:206`），
    消费 `ProviderResolution`（`:128`：`outcome / query / normalized_query / candidates / attempts / retryable / reason / answered / provider_replied`）：
    - `MATCH` → 用 `candidates[0]` 的 `source_provider + source_entity_id`（**WGS84 + observed_at/fetched_at 一并带**）建立服务端所有的 canonical identity；
    - `AMBIGUOUS` → `canonical=null` + `candidates` 另栏，**谁都不许静默当选**；
    - `NO_MATCH` → `canonical=null`，**不得把原文写成 `pending:<raw>` 当身份**；
    - `RUNTIME_FAILURE` → `canonical=null` + 具名 retryable，**不得塌成 NO_MATCH**（这条在 B 侧已有门：`timeout_never_becomes_no_match`；换层后要**由你的门继续守住**）。
    ⇒ 为什么必须是甲：`运行性失败 ≠ 没有这个地方` 这套分类**只能写一遍**。两条入口各写一遍，就是它当初塌成 `unresolved:<hash>` 的成因。
    ⇒ 顺带把 B 的 `ProviderAttempt`（逐镜子逐尝试留痕）接进你的作业/审计字段，R14 的具名原因就有出处了。
    【仍然排队列】0158 / 0182 / 0176 / 0175 / 0187 / 0125 让位给本单；写完在 `f2708dd`→本 SHA 上把 0191 的十项必证**逐条对上**再交，我会**在你的 exact delivery SHA 上复跑**再签。
  status: DISPATCHED@2026-09-22T02:0x+08 by 494abfd7（仲裁 甲 的执行单；我复跑过 01:59 那一腿，保留其成果）

- id: ORD-0198
  to: c01d72a3
  priority: high
  if_head: 61cde4b
  order: |
    【仲裁 5765117939 已批 **canary**：**允许建，但 P7=false 时不得借它唤醒 Harness / P1–P4**。你来搭，因为它是 E2E 证据面。】
    它的十项隔离条件（**逐条自证后再动产品代码**，先交隔离证明）：
    ① 独立端口；② 独立/一次性 DB 副本；③ 不复用用户 live DB 的写连接；④ **不挂到用户的 preview URL / 隧道 / service-worker scope**；
    ⑤ 用户正常入口不可达；⑥ 主预览继续固定 `53fe8e8`；⑦ 主预览 `demo/reset → 403 PREVIEW_GUARDED`；⑧ 主预览不切 live routing；
    ⑨ canary 的破坏性操作**只作用于 canary 库**；⑩ canary 失败**不得回写**权威线/主预览状态。
    冻结句：**"An isolated, user-unreachable canary is verification infrastructure, not a deployment of the user's preview."**
    ⇒ 目的：让"未预录县 → HYDRATABLE → 真补目录 →（或精确停在具名 mobility gap）"**第一次有可见形状**；
      但**真人组与 Harness 仍不唤醒**，直到 ORD-0197 落地、`P7_RESOLVER_INTEGRATED` 七条件我逐条重判为 true。
    ⇒ 证据要求：canary 上每一步都按 **14 项 mobility/used-edge 收据**交（`blocker_basis=USED_EDGE_INVENTORY` +
      `aggregate_repository_counts_used_as_blocker=false`）；**provider-only MATCH、直接塞 DB、API-only 成功、mock 冒充 live 都不算 Mission A 成功**。
    ⇒ 禁令：不碰 `:4781/:4782/:8693` 与 `_live.db`（只读复核除外）；禁 `demo/reset`；自有端口段 :85xx；凭据不写入任何产物；
      `node_modules` 禁止 junction（D-7）。账本写入必须过 `ledger_write_preflight`（LF + 唯一局部锚点 + 可逆证明）。
  status: DISPATCHED@2026-09-22T02:0x+08 by 494abfd7（仲裁批准但明确"可建不可叫醒"；十项隔离条件逐条自证）
