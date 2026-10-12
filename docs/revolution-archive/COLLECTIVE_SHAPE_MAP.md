# collective 三枚的形状对照（ORD-0594 第一半）

代表枝 `refs/heads/gpt/revolution-r33-open-world-journey-adaptation`；现尖 `d7776c6a7730e05ba32e7cb1e2e733f5099a7433`，命令原样 `git -C D:/moodle/CityNexus ls-remote origin refs/heads/mirror/integration-frontend-apple-pass1`。

三态口径：**① 能直接接** = 该模块每一枚 `app.*` 依赖在现尖都取到、名字也在；**② 要改哪一枚签名** = 模块与名字都在但形状对不上调用；**③ 现尖根本没有对应形状** = 模块整枚不在，或名字在现尖那枚文件里搜不到。

| 那枚模块 | 行数 | 判定 | 卡在现尖哪一样上 |
|---|---|---|---|
| `backend/app/collective_authority.py` | 501 | ③ 现尖根本没有对应形状 | `整枚模块不在现尖：app.recovery_epoch`、`app.db.models.CollectiveAuthorityReceipt` |
| `backend/app/collective_mediation.py` | 584 | ③ 现尖根本没有对应形状 | `app.replanning.candidate_evidence.verified_interest_preference_breakdown` |
| `backend/app/collective_operator.py` | 474 | ③ 现尖根本没有对应形状 | `app.db.models.CollectiveAuthorityReceipt`、`app.db.models.RecoveryEpoch` |

② 那一档本轮 0 处：凡在现尖取到名字的行都逐枚写在下节，名字对得上就归①；取不到的直接落③。签名级对拍本轮没做，因为三枚都还没走到调用点。

## 逐枚依赖（每条都是现读取回的坐标）

### backend/app/collective_authority.py

- 源侧枝尖 `1725a449a50898e1c63889f0e7c0a81f347a7a1f`｜该文件 blob `60a674d04d2d4cc0085cae5d1384e7fa32f61e31`｜501 行 20234 字节
  - `app.db.models.AuditLog` ⇒ ① 现尖 `backend/app.db.models.py`:569 取得到
  - `app.db.models.CollectiveAuthorityReceipt` ⇒ ③ 现尖 `backend/app.db.models.py` 里搜不到这个名字
  - `app.db.models.Journey` ⇒ ① 现尖 `backend/app.db.models.py`:174 取得到
  - `app.db.models.PlanVersion` ⇒ ① 现尖 `backend/app.db.models.py`:518 取得到
  - `app.db.models.ReplanProposal` ⇒ ① 现尖 `backend/app.db.models.py`:789 取得到
  - `from app.recovery_epoch` 源侧第 21 行 ⇒ ③ 现尖没有这枚模块（`backend/app.recovery_epoch.py` 不在树上）

### backend/app/collective_mediation.py

- 源侧枝尖 `1725a449a50898e1c63889f0e7c0a81f347a7a1f`｜该文件 blob `9e9f005ccc7eed9515ccfee308289d7a172ad74a`｜584 行 25721 字节
  - `app.db.models.JourneyMission` ⇒ ① 现尖 `backend/app.db.models.py`:209 取得到
  - `app.db.models.PlanVersion` ⇒ ① 现尖 `backend/app.db.models.py`:518 取得到
  - `app.db.models.ReplanProposal` ⇒ ① 现尖 `backend/app.db.models.py`:789 取得到
  - `app.replanning.candidate_evidence.verified_interest_preference_breakdown` ⇒ ③ 现尖 `backend/app.replanning.candidate_evidence.py` 里搜不到这个名字

### backend/app/collective_operator.py

- 源侧枝尖 `1725a449a50898e1c63889f0e7c0a81f347a7a1f`｜该文件 blob `3991a6626507d06b825f5eeec08e938e3306c401`｜474 行 18866 字节
  - `app.db.models.AuditLog` ⇒ ① 现尖 `backend/app.db.models.py`:569 取得到
  - `app.db.models.CollectiveAuthorityReceipt` ⇒ ③ 现尖 `backend/app.db.models.py` 里搜不到这个名字
  - `app.db.models.Journey` ⇒ ① 现尖 `backend/app.db.models.py`:174 取得到
  - `app.db.models.JourneyMember` ⇒ ① 现尖 `backend/app.db.models.py`:1277 取得到
  - `app.db.models.JourneyMission` ⇒ ① 现尖 `backend/app.db.models.py`:209 取得到
  - `app.db.models.JourneyRoleCapability` ⇒ ① 现尖 `backend/app.db.models.py`:1297 取得到
  - `app.db.models.PlanVersion` ⇒ ① 现尖 `backend/app.db.models.py`:518 取得到
  - `app.db.models.RecoveryEpoch` ⇒ ③ 现尖 `backend/app.db.models.py` 里搜不到这个名字
  - `app.db.models.ReplanProposal` ⇒ ① 现尖 `backend/app.db.models.py`:789 取得到
  - `app.db.models.Traveler` ⇒ ① 现尖 `backend/app.db.models.py`:21 取得到

## 第一处不需要改契约的接线：现尖这一代没有

- 三枚都要先在 `backend/app/db/models.py` 多出两枚表形：`RecoveryEpoch` 与 `CollectiveAuthorityReceipt`。现尖那份文件里两枚都搜不到（`class RecoveryEpoch` 与 `class CollectiveAuthorityReceipt` 的 grep 各回 0 行），代表枝那份里它们在。
- `backend/app/recovery_epoch.py` 整枚不在现尖，而它自己也要这两枚表形，所以它不是「先落它就能接上 collective」的第一块。
- `backend/app/replanning/candidate_evidence.py` 在现尖存在，但缺 `verified_interest_preference_breakdown` 那一枚函数；补它是改一枚现成文件的形状，不在「净新增零依赖」那一档。

## 交回号令者的那一部分（需要点头的，我不自己插）

- 一，`backend/app/db/models.py` 加两枚表形：谁建表、迁移怎么走、共享预览库那份已存在的 52 张表怎么办，这三件要点名才动。
- 二，`backend/app/replanning/candidate_evidence.py` 要不要按代表枝的形状接进那枚函数。
- 这两件都不是 `contracts/openapi.yaml`，本轮我也没动过它；本轮改动面里也没有这五枚热文件：`backend/app/main.py`、`backend/app/schemas.py`、`contracts/openapi.yaml`、`frontend/src/api/citynexus.ts`、`backend/app/agent/runtime.py`。

## 本轮真正落线的那一枚产品字节

- `backend/app/execution/departure_activation.py` 与 `backend/tests/test_departure_activation.py`：ORD-0593 那张单里被明言留给另一扇的第二枚。顶层 import 只有 `__future__`、`datetime`、`hashlib`、`json`、`typing`（全是标准库），正文里 `app.` 出现 0 次，现尖上引用 departure_activation 这个名字的文件 0 个。
- 落线证明四条（导出整树、插入、venv 真 import、该测试真跑）写在交块第三节，本文件只留形状判定，不替那四条背书。

