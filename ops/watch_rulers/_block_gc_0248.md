## commander 执行 @2026-09-23T02:48+08 —— 按仲裁的 legacy GC 流程做完**只读前三步**（一个文件都没删），成果已发布可读

### ① 盘到的数（只读）

```text
候选集（age > 6h）：852 个目录
  EPHEMERAL_CANDIDATE（名字在账本与已发布证据面里都查不到）：835 个 / 471.4 MB
  HOLD（名字在账本或证据面里被点名过）：17 个 / 12.1 MB   ← 删了会破坏复放
合计 483.5 MB（>6h 这一档）；最老 11.8 h；单个最大 5.2 MB
owner 一栏全部 = UNKNOWN_OWNER
```
**按仲裁的口径 ⇒ 现在可删 = 0**："782/852 个只是候选集合，不是删除集合"，而 `%TEMP%` 目录**不带 owner metadata**，所以**没有任何一个在"owner 已释放"之前可动**。**我一个都没删。**

### ② 冻结的两条（照录，供所有车道）

```text
TEMP_PATH_ALLOWED_AS_PROVENANCE       收据可以且应该记 %TEMP%\cnx_pytest_*\...（fresh-DB 门正需要记录 app 真正解析到的临时绝对路径）
TEMP_PATH_FORBIDDEN_AS_SOLE_REPLAY_ARTIFACT   若复放需要那只 DB/日志/fixture ⇒ 清理前必须复制到 lane 的 lab/<order>/<run>/ 或发布到 evidence/，并记 bytes/hash
```

### ③ 车道侧的新规矩（仲裁要求，从我这边开始执行）

每个 lane 每次批量测试结束后、**在它完成证据发布/登记之后**立即清自己的 temp dirs，并在 receipt/cleanup manifest 里记：
```text
owner/lane · exact temp dir(s) · created_by run/order · evidence disposition(EPHEMERAL|MATERIALIZED|HOLD) · cleanup_allowed
```
**Commander 只按这些 manifest 汇总删除，不凭"名字像、够老、占空间"推断所有权。** ⇒ 我在后续每一轮联系车道时都要带上这条；车道报"已清自己的"时也要给出具名清单。

### ④ 可读坐标

`evidence/temp_gc/candidates_0923_0247.json`（blob `0173fbcad7228315`，250,053 B）：含 `counts` / `bytes` / 逐条的 `dir · basename · age_hours · bytes · named_in_ledger · named_in_evidence · disposition · owner`，文件头写明"candidate != delete set"与仲裁条号。

### ⑤ 另：D 盘的只读 Top-N 仍在后台跑

`du -sm /d/moodle/* | sort -rn | head -25` 已放后台（300 GB 量级，预计数分钟）；结果入下一块。**D 盘被定为 `USER_ATTENTION_REQUIRED`，只盘点、不自动删。**

### ⑥ 现场

链三条端口在听（`:4781` 56212 / `:4782` 20364 / `:8693` 55960）；三代包同挂；清理闸门仍关（0 删除，等用户真机刷新）；`P7=false`；reference tip `c0d7e3d`；P0 未动（3 行程 / 19 计划版本 / 3 出行人 / 16 地点）；那把 key 仍未轮换。
