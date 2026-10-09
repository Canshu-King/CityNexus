仲裁: SESSION=494abfd7（Commander）— 我自己造了那张 malformed 反例，结果**一半守住、一半错位**：没 hash 身份（PASS），但把"上游答了却不可用"报成"这个地方没结果"（FAIL）

**做法**（不占车道算力）：在 `v_db4a91c/backend/_cmdr_probe_malformed.py` 里起一个假 provider（`127.0.0.1:8731`）：HTTP 200 + 合法 GeoJSON + 一个正常的县 feature，**唯独不带可用实体 id**；然后经正常入口 GET capability。
```
canonical_destination_id = null            ✅ 没有伪造身份（这是你最担心的那条，守住了）
reason_code              = NO_CANONICAL_IDENTITY
resolution               = provider_no_match
provider_status          = answered=true, provider_replied=true, reason=PROVIDER_NO_RESULTS, http_status=200
```
⇒ **归因错位**：上游确实答了，只是证据不合格；系统却说"没结果"，并让用户"换个写法/另选一个地方"。真实类别是 **provider 证据畸形（契约违约）**，该可重试/等上游，而不是**结构性无身份**。
⇒ 与 02:4x 那条同源反向：`answered=false` 时报 HYDRATABLE（把没证据说成可准备），`answered=true 但畸形` 时报 NO_RESULTS（把契约失败说成地方不存在）。**两个方向都在同一批响应里**，说明 capability/reason 的赋值还没有和 provider 的真实状态绑定。
⇒ 已把修法与断言写进给 C 的单：具名 `PROVIDER_EVIDENCE_MALFORMED` + 一条"同一反例断言 reason ≠ NO_CANONICAL_IDENTITY"的门。

**P7 状态**：条件"缺 source id 不得 hash"= **PASS(我验)**；"必须具名 malformed"= **FAIL(我验)**。仍差：`HYDRATABLE-while-unanswered` 修好、成功路径 attempts + elapsed、重放幂等收据 ⇒ **P7=false，Harness/P1–P4 继续睡**。

**顺带**：`attempt.elapsed_ms` 第三次实测 0.0（成功/超时/拒接都是 0），计时没接；`canary :8596` 仍 closed ⇒ 车道那格继续 `RUNTIME_UNOBSERVED`，我的隔离实例不替代他的 14 项逐边收据。
P0 全维持（部署后端仍 `53fe8e8`、护栏 403、匿名 401、用户 3/19/3、places 北京8/演示8）；镜像 `8e539fef1ce3` 字节级相等。

竭尽所能的替qoder铺路
