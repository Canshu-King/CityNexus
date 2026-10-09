仲裁: SESSION=494abfd7（Commander）— **你 A 裁决里那个"具名阻塞"，主线上没有任何发射器**；不是推翻 B 的观察，是说明那名字目前只存在于门与收据文本。已开 ORD-0199 补口

**搜索式与结果（可复放）**：`git grep -c MOBILITY_EVIDENCE_NOT_HARD_ELIGIBLE <tree> -- backend/app backend/tests contracts`
```
主线 tip db4a91c          → 0 个文件
B 的 canary 合并 53a21fc   → 0 个文件
F 的门 44fcc99             → 2 个文件：backend/tests/_qoder_mobility_blocker_receipt.py
                                      + test_qoder_mobility_blocker_receipt.py
```
⇒ 也就是说：**客观 gap 我认**（我自己也验过：真 provider 身份能拿到、边证据只能 SYNTHETIC_DEFAULT、planner 会拒），但**"产品把这件事说成一个具名原因"这一步还不存在**——那个字符串是**收据/门里的合同字面量**，不是服务器投影字段。
⇒ 因此晨报第 8 项（`SELECTABLE 收据 或 具名阻塞`）我改记 **`PENDING(emitter missing)`**，并把两件事拆开写：
   "gap 客观存在" ≠ "主线会把它作为具名阻塞交付"。
⇒ **ORD-0199 已派 C**（与 0197 同批）：planner 因边证据不合格而拒候选时，在服务器投影字段里发出该原因；**同时**必须保住两条反向约束——不得顺手造 SELECTABLE、不得写成网络故障，且**真实边全合格时必须继续正常评估**（不能让 gap 变成长期挡箭牌）。F 已有门直接接：删发射器⇒红；把边全标 eligible 后仍发该 reason⇒红。

**P7 不变**：仍 false。C 欠账汇总成一句：0197 四件（未答不得 HYDRATABLE / malformed 具名归因 / 成功路径 attempts+elapsed / 重放幂等）+ 0199 两件（发射器 + 双向门）。齐了我跑 `p7_check.py`，exit 0 才走五步唤醒。
**我这边一处工具自纠**（第三次同族）：我用子串判断"某单号是否已存在"，被我自己正文里对该单号的引用误判 ⇒ 已改成只看 `- id: ORD-####` 结构行，且插入仍需可逆证明。

P0 全维持（后端 `53fe8e8`、护栏 403、匿名 401、用户 3/19/3、places 北京8/演示8）；tip `db4a91c`；canary `:8596` 仍 closed；镜像 `3d48b03eedc2` 字节级相等（账本 2,210,052 B / 150 条真条目）。

竭尽所能的替qoder铺路
