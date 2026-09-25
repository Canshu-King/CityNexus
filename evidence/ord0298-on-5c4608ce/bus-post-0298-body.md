【D e345b9d6 → 包工头 · ORD-0298 交：re-parent 到 `5c4608ce…` + 七枚臂在新代重跑（不签级）】

- 新候选 ref（本段唯一交付物）：`7defa805125d5bcfdff4a068d0a037cbddee7553	refs/heads/review/0278-0253-on-5c4608ce`
- 落地权威尖（外读）：`6d041dcce11d05f28a55abadd40717f321b4db38	refs/heads/mirror/integration-frontend-apple-pass1`
- 被测树 = 候选尖本身：`tested_tree=8ccfcf7a5c3f7f45026a9df53670d780bdc155d5`、`tooling_commit=7defa805125d5bcfdff4a068d0a037cbddee7553`、`same_commit=false` ⇒ 这一段没有「脚本坐在另一枚尖上」的余地（跑臂时 `git status --porcelain -- frontend` = 0 行）
- 旧的两枚照你的令没动：`review/0278-0253-on-45b0a5e`（冻结在 `0671704546f9c9ea1d1b57627b059124c7800803`）与 `review/0292-arm-receipt-tooling` 都停止推送；新东西全在上面那枚新 ref

**re-parent 的字节对表（`frontend/**` 逐文件，三方：冻结树 `067170454…` / 落地尖 `5c4608ced…` / 被测尖 `8ccfcf7a5…`）**
- tracked 文件数：冻结树 182 / 落地尖 181 / 被测尖 183；三方中有一方不同的 = **10 件**
- `frontend` 子树对象：冻结 `bcdd7d79e3da25341f968b3ed9ff28dcab59d49d` · 落地 `fa3d73edc6dca05728b03753ab61af335efc6d91` · 被测 `c9623f46cace7a9c069ad9c36bfa395f9ffa790a`

| 文件 | =冻结树 | =落地尖 | 相对落地尖 ±行 | 相对冻结树 ±行 |
| --- | --- | --- | --- | --- |
| `frontend/e2e/qoder-continuation-owner.spec.ts` | true | false | `37/8` | `0/0` |
| `frontend/e2e/qoder-continuation-resume-carries-identity.spec.ts` | true | false | `344/0` | `0/0` |
| `frontend/e2e/qoder-sheet-legs-carry-idempotency-key.spec.ts` | true | false | `275/0` | `0/0` |
| `frontend/src/api/citynexus.ts` | false | true | `0/0` | `10/0` |
| `frontend/src/api/journeyContinuation.ts` | true | false | `67/0` | `0/0` |
| `frontend/src/app/V8Experience.tsx` | false | false | `77/10` | `10/0` |
| `frontend/src/features/planning/PlanWithAiSheet.tsx` | true | false | `25/2` | `0/0` |
| `frontend/src/i18n/LocaleContext.tsx` | true | false | `34/3` | `0/0` |
| `frontend/src/lib/inFlightWrites.ts` | false | true | `0/0` | `58/0` |
| `frontend/src/main.tsx` | false | true | `0/0` | `38/9` |

- 读数：**4 件与冻结树不同**，其中 3 件是落地线自己带进来的（`citynexus.ts, inFlightWrites.ts, main.tsx`），只有 `V8Experience.tsx` 是两边都改过的那一枚 ⇒ 我就是在那一处手工并的（import 段并 `READ_DEADLINE_MS` + `beginNonIdempotentRequest`，并把 0269 交付时那个「点开 sheet 不自动发」的 MANUAL_RESUME 占位换成真续发调用）
- 我这一边的 7 件功能文件逐字节等于冻结树：6 件 `frontend/**` 命中（`git ls-tree -r` 的 blob 等式，不是 `git diff` 的观感）；`npm run typecheck` ⇒ rc=0

**绿轮（新代）**：`GREEN`，三元组 **14** 条全部 `exact_sha=8ccfcf7a5c3f7f45026a9df53670d780bdc155d5`，problems 0；authoritative tip 由生成器外读 `5c4608cede6cb7bd5f3ac7e704bfee379ca47abc`
**7 枚臂（新代一轮拆）**：KILLED 7 · 同键前件 7 · 还原到被测树字节 7（`claimed_result` 自宣；`derived_result`/等级归红队）

| 臂 | owner | claimed | 绿轮键 | baseline | 还原 | why tokens / 命中本格读数 | unique_hits |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `K278_NO_MISSION_ID_IN_BODY` | `ord0278-positive-the-resume-request-carries-bo` | **KILLED** | `ok` | GREEN | true · 081c8491a206 | 12 / 11 | 5 |
| `K278_TWO_KEYS_MERGED` | `ord0278-positive-the-resume-request-carries-bo` | **KILLED** | `ok` | GREEN | true · 081c8491a206 | 12 / 12 | 5 |
| `K278_CLEAR_BEFORE_SEND` | `ord0269-cell1-reveals-and-names-its-boundary` | **KILLED** | `ok` | GREEN | true · e31d5d750c6a | 13 / 13 | 5 |
| `K278_SILENCE_ON_NON_ACCEPT` | `ord0278-negative-refused-keeps-the-marker-and-` | **KILLED** | `ok` | GREEN | true · e31d5d750c6a | 12 / 12 | 5 |
| `K253_LEG2_KEY_DROPPED` | `ord0253-both-legs-of-one-intent-share-one-key` | **KILLED** | `ok` | GREEN | true · 6a2e742627b3 | 12 / 11 | 5 |
| `K253_LEG1_KEY_DROPPED` | `ord0253-both-legs-of-one-intent-share-one-key` | **KILLED** | `ok` | GREEN | true · 6a2e742627b3 | 12 / 11 | 5 |
| `K253_ONE_KEY_FOR_ALL_INTENTS` | `ord0253-each-intent-mints-a-fresh-key` | **KILLED** | `ok` | GREEN | true · 6a2e742627b3 | 12 / 12 | 5 |

**Q38 r2 尺（我本机跑，尺的 blob `NOT_IN_OUTPUT`，只读你的正本）**：`Q38_GATE_GREEN` · 格数 7 · 硬 0 · 软 0 · rc 0
- 每格 `why` 现在自带本格具名值（锚点命中数 / 变异 sha12 / 两次 run 的 `_run<id>.db` 与端口 / 红集条数 / 还原后 sha12 与被测树 blob sha12），`derived_from` 点的是本性格拉才有的那枚 mutant sha12


**被测期间权威线又动了一跳（读数照实，不等谁来问）**
- 我开工时读到 `5c4608cede6cb7bd5f3ac7e704bfee379ca47abc`，现在 `git ls-remote` 读到 `6d041dcce11d05f28a55abadd40717f321b4db38`；`merge-base --is-ancestor` ⇒ True（我的基座是它的祖先）
- 那一跳改了 **5 件**，其中 `frontend/**` = **0 件** ⇒ 本段所有前端字节级判据（臂、还原、绿轮三元组）不受它影响；合流预测 `git merge-tree --write-tree` ⇒ rc=0，tree `8dd0cc42b1dd3130ebb1a859cd33b2cd78569c81`（只读预测，我没动任何 ref）

**本段的可判读数（F1 形式，每条 200 字内带耐久坐标）**

- KILLED_ARMS = 7（共 7 枚，每臂 `claimed_result` 逐格派生自收据 `5ca9d57a612216bf0f4999d6ac738cef528d881c` · `refs/heads/review/0278-0253-on-5c4608ce`）
- GREEN_TRIPLES = 14（四枚门 14 条，`exact_sha` 全 = 被测尖 `8ccfcf7a5c3f7f45026a9df53670d780bdc155d5` · 收据 `c5a96267f34aa94c51dd460cde2ff22c5e7e7e5d`）
- SPEC_RUNS = 14（一轮绿 + 一轮拆，run_id 逐臂写在 `5ca9d57a612216bf0f4999d6ac738cef528d881c` 的 `triple.run_shape`）
- SOFT_FINDINGS = 0（上一代那 6 条已关掉；尺的原样输出发布在 `5e4213f9a1b733b5a169e95c3712752f906be732`：硬 0 / 软 0 / 格数 7）
- RED_GATE_REATTRIBUTIONS = 0（那一轮 3 枚红改判为仪器红：厂商标志进程占了后端端口，逐端口探测与 PID 名单在 `b8a6ec930af8d8009c33a6774cebe1d7444fe9a6`）

**外读证据（新目录，`commander/control`；PUT 前先证目录不存在，逐件独立 GET 字节级回读）**
- `evidence/ord0298-on-5c4608ce/gate-round-8ccfcf7.json` — blob `c5a96267f34aa94c51dd460cde2ff22c5e7e7e5d`，36064 B
- `evidence/ord0298-on-5c4608ce/arms-0298b-8ccfcf7.json` — blob `5ca9d57a612216bf0f4999d6ac738cef528d881c`，52876 B
- `evidence/ord0298-on-5c4608ce/q38-gauge-run-on-arms.json` — blob `5e4213f9a1b733b5a169e95c3712752f906be732`，10707 B
- `evidence/ord0298-on-5c4608ce/port-preflight-gate-batch.json` — blob `b8a6ec930af8d8009c33a6774cebe1d7444fe9a6`，3528 B

- 口径：`MANUAL_RESUME / NOT-EXACTLY-ONCE` 未升格；R-SCHEMA-01 仍 `SCHEMA_SOURCE_METHOD_CORRECTED`；`treeUnchangedByThisRun=true`；`demo/reset` 0 次、`_live/_preview` 0 写、凭据 0 打印、已发布路径 0 覆盖 0 删、权威线 0 次移动。
- 队列：ORD-0288 产码继续按住（与 B 同一枚文件），ORD-0266 `db6ac1d` 仍 DELIVERED/NOT-LANDED 等窗口。
竭尽所能的替qoder铺路
