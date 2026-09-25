【D e345b9d6 → 包工头 · ORD-0298 交：re-parent 到 `5c4608ce…` + 七枚臂在新代重跑（不签级）】

- 新候选 ref（本段唯一交付物）：`dc964086c9d412573ac19d70b24b30e6c3ee6168	refs/heads/review/0278-0253-on-90d29a17`
- 落地权威尖（外读）：`90d29a172e186aab6e6cb138ab4583ccf93bfa68	refs/heads/mirror/integration-frontend-apple-pass1`
- 被测树 = 候选尖本身：`tested_tree=dc964086c9d412573ac19d70b24b30e6c3ee6168`、`tooling_commit=dc964086c9d412573ac19d70b24b30e6c3ee6168`、`same_commit=true` ⇒ 这一段没有「脚本坐在另一枚尖上」的余地（跑臂时 `git status --porcelain -- frontend` = 0 行）
- 旧的两枚照你的令没动：`review/0278-0253-on-45b0a5e`（冻结在 `0671704546f9c9ea1d1b57627b059124c7800803`）与 `review/0292-arm-receipt-tooling` 都停止推送；新东西全在上面那枚新 ref

**re-parent 的字节对表（`frontend/**` 逐文件，三方：冻结树 `067170454…` / 落地尖 `90d29a172…` / 被测尖 `dc964086c…`）**
- tracked 文件数：冻结树 182 / 落地尖 182 / 被测尖 184；三方中有一方不同的 = **11 件**
- `frontend` 子树对象：冻结 `bcdd7d79e3da25341f968b3ed9ff28dcab59d49d` · 落地 `663b4516bd8d79eecb1ebc7991dd7d3a45fb90c0` · 被测 `a53c7303c6d1513010ff91ecf9c022591c3e513c`

| 文件 | =冻结树 | =落地尖 | 相对落地尖 ±行 | 相对冻结树 ±行 |
| --- | --- | --- | --- | --- |
| `frontend/e2e/qoder-continuation-owner.spec.ts` | true | false | `37/8` | `0/0` | 表出自 blob `457313365eda53e9` |
| `frontend/e2e/qoder-continuation-resume-carries-identity.spec.ts` | true | false | `344/0` | `0/0` | 表出自 blob `457313365eda53e9` |
| `frontend/e2e/qoder-ord0280-attribution-label-speaks-for-itself.spec.ts` | false | true | `0/0` | `294/0` | 表出自 blob `457313365eda53e9` |
| `frontend/e2e/qoder-sheet-legs-carry-idempotency-key.spec.ts` | true | false | `275/0` | `0/0` | 表出自 blob `457313365eda53e9` |
| `frontend/src/api/citynexus.ts` | false | true | `0/0` | `10/0` | 表出自 blob `457313365eda53e9` |
| `frontend/src/api/journeyContinuation.ts` | true | false | `67/0` | `0/0` | 表出自 blob `457313365eda53e9` |
| `frontend/src/app/V8Experience.tsx` | false | false | `77/10` | `10/0` | 表出自 blob `457313365eda53e9` |
| `frontend/src/features/planning/PlanWithAiSheet.tsx` | false | false | `25/2` | `71/16` | 表出自 blob `457313365eda53e9` |
| `frontend/src/i18n/LocaleContext.tsx` | true | false | `34/3` | `0/0` | 表出自 blob `457313365eda53e9` |
| `frontend/src/lib/inFlightWrites.ts` | false | true | `0/0` | `58/0` | 表出自 blob `457313365eda53e9` |
| `frontend/src/main.tsx` | false | true | `0/0` | `38/9` | 表出自 blob `457313365eda53e9` |

- 读数：**6 件与冻结树不同**，其中 4 件是落地线自己带进来的（`qoder-ord0280-attribution-label-speaks-for-itself.spec.ts, citynexus.ts, inFlightWrites.ts, main.tsx`），只有 `V8Experience.tsx, PlanWithAiSheet.tsx` 是两边都改过的那一枚 ⇒ 我就是在那一处手工并的（import 段并 `READ_DEADLINE_MS` + `beginNonIdempotentRequest`，并把 ORD-0269 交付时那个「点开 sheet 不自动发」的 MANUAL_RESUME 占位换成真续发调用）
- 我这一边的 7 件功能文件逐字节等于冻结树：5 件 `frontend/**` 命中（`git ls-tree -r` 的 blob 等式，不是 `git diff` 的观感）；`npm run typecheck` ⇒ rc=0

**绿轮（新代）**：`GREEN`，三元组 **14** 条全部 `exact_sha=dc964086c9d412573ac19d70b24b30e6c3ee6168`，problems 0；authoritative tip 由生成器外读 `90d29a172e186aab6e6cb138ab4583ccf93bfa68`
**7 枚臂（新代一轮拆）**：KILLED 7 · 同键前件 7 · 还原到被测树字节 7（`claimed_result` 自宣；`derived_result`/等级归红队）

| 臂 | owner | claimed | 绿轮键 | baseline | 还原 | why tokens / 命中本格读数 | unique_hits |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `K278_NO_MISSION_ID_IN_BODY` | `ord0278-positive-the-resume-request-carries-bo` | **KILLED** | `ok` | GREEN | true · 081c8491a206 | 12 / 11 | 5 |
| `K278_TWO_KEYS_MERGED` | `ord0278-positive-the-resume-request-carries-bo` | **KILLED** | `ok` | GREEN | true · 081c8491a206 | 12 / 12 | 5 |
| `K278_CLEAR_BEFORE_SEND` | `ord0269-cell1-reveals-and-names-its-boundary` | **KILLED** | `ok` | GREEN | true · e31d5d750c6a | 13 / 13 | 5 |
| `K278_SILENCE_ON_NON_ACCEPT` | `ord0278-negative-refused-keeps-the-marker-and-` | **KILLED** | `ok` | GREEN | true · e31d5d750c6a | 12 / 12 | 5 |
| `K253_LEG2_KEY_DROPPED` | `ord0253-both-legs-of-one-intent-share-one-key` | **KILLED** | `ok` | GREEN | true · 57fb0b6048f4 | 12 / 11 | 5 |
| `K253_LEG1_KEY_DROPPED` | `ord0253-both-legs-of-one-intent-share-one-key` | **KILLED** | `ok` | GREEN | true · 57fb0b6048f4 | 12 / 11 | 5 |
| `K253_ONE_KEY_FOR_ALL_INTENTS` | `ord0253-each-intent-mints-a-fresh-key` | **KILLED** | `ok` | GREEN | true · 57fb0b6048f4 | 12 / 12 | 5 |

**Q38 r2 尺（我本机跑，尺的 blob `NOT_IN_OUTPUT`，只读你的正本）**：`Q38_GATE_GREEN` · 格数 7 · 硬 0 · 软 0 · rc 0
- 每格 `why` 现在自带本格具名值（锚点命中数 / 变异 sha12 / 两次 run 的 `_run<id>.db` 与端口 / 红集条数 / 还原后 sha12 与被测树 blob sha12），`derived_from` 点的是本性格拉才有的那枚 mutant sha12



**本段的可判读数（F1 形式，每条 200 字内带耐久坐标）**

- KILLED_ARMS = 7（共 7 枚，每臂 `claimed_result` 逐格派生自收据 `457313365eda53e9634ddf522839fe3714d0e86d` · `refs/heads/review/0278-0253-on-90d29a17`）
- GREEN_TRIPLES = 14（四枚门 14 条，`exact_sha` 全 = 被测尖 `dc964086c9d412573ac19d70b24b30e6c3ee6168` · 收据 `211c67f88b4360c63c1e4ed1c6284f36b3f354fd`）
- SPEC_RUNS = 14（一轮绿 + 一轮拆，run_id 逐臂写在 `457313365eda53e9634ddf522839fe3714d0e86d` 的 `triple.run_shape`）
- SOFT_FINDINGS = 0（上一代那 6 条已关掉；尺的原样输出发布在 `c419b0e8784dd222c4f5ef2816187925fb235d58`：硬 0 / 软 0 / 格数 7）
- RED_GATE_REATTRIBUTIONS = 0（那一轮 3 枚红改判为仪器红：厂商标志进程占了后端端口，逐端口探测与 PID 名单在 `e71838cbdbf574bd479747dc10e7a84f64165ce0`）

**外读证据（新目录，`commander/control`；PUT 前先证目录不存在，逐件独立 GET 字节级回读）**
- `evidence/ord0298d-on-90d29a17/ord0298d-gate-round-dc96408.json` — blob `211c67f88b4360c63c1e4ed1c6284f36b3f354fd`，36722 B
- `evidence/ord0298d-on-90d29a17/ord0278-0253-arms-0298d-on-dc96408.json` — blob `457313365eda53e9634ddf522839fe3714d0e86d`，53650 B
- `evidence/ord0298d-on-90d29a17/q38-arms-0298d.json` — blob `c419b0e8784dd222c4f5ef2816187925fb235d58`，10708 B
- `evidence/ord0298d-on-90d29a17/batch-on-90d29a17.json` — blob `e71838cbdbf574bd479747dc10e7a84f64165ce0`，3528 B

- 口径：`MANUAL_RESUME / NOT-EXACTLY-ONCE` 未升格；R-SCHEMA-01 仍 `SCHEMA_SOURCE_METHOD_CORRECTED`；`treeUnchangedByThisRun=true`；`demo/reset` 0 次、`_live/_preview` 0 写、凭据 0 打印、已发布路径 0 覆盖 0 删、权威线 0 次移动（权威线只由包工头在 `refs/heads/mirror/integration-frontend-apple-pass1` 上移动，我只读 ls-remote）。
- 队列：ORD-0288 产码继续按住（与 B 同一枚文件），ORD-0266 `db6ac1d` 仍 DELIVERED/NOT-LANDED 等窗口。
竭尽所能的替qoder铺路
