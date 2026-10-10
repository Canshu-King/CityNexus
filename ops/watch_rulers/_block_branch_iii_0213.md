## commander 转达 @2026-09-23T02:13+08 —— 仲裁裁 **分支政策选 (iii) composite**；并**源审出我适配器还有一处口径没对上**（observation 那个例外必须删），我已照改

### ① 分支政策：选 (iii)

```text
composite：产品候选保持干净；尺作为显式依赖；“真正跑 closure 的那棵树有自己的 SHA”
```
**它否掉另两个的理由（照录）**：(i) corrected g3 还没出生，为了跑未来的门先污染主线，**收益很低**；(ii) 把产品门修正与审计基础设施绑成一次变更，出了问题**反而更难归因**。
**压轴那句请所有人照此执行**：**「closure 跑在具名、可推送、可审的 composite commit；跑绿属于 composite，不属于 mainline。主线想要 GREEN，就拿主线自己的 exact SHA 再跑。」**
⇒ 已要求 F 把三条落进它的退出码表：**(a)** 先打印 composite 树自己的 SHA 与尺的 sha256 前缀；**(b)** composite **必须可推送**（否则不可审）；**(c)** 收据里必须写"绿属于谁"，**不允许**写成主线绿。

### ② 它对我的 `gate_streak.py` 的源审（我又错了一处，已改）

它指出：我上一轮说"只有 `CLOSED` 才返 0"**还不成立**——`observation_only + STREAK_MET` 仍会 exit 0。**它的口径**：`0` 只给 `CLOSED`；**observation 成功也返非零**，但 receipt 里写 `OBSERVATION_MET`。理由：若从现在起把"进程 exit 0"定义成 closure 级成功，这个例外必须删，否则**只看 rc 的调用方会把 observation 当 CLOSED**。
**已照改并发布**：`live_checks/gate_streak.py` blob **`b06267dfce07d9de`**（12,696 B）：
```text
closure_grade == CLOSED      -> rc 0
observation 且 STREAK_MET     -> rc 2，且 receipt.observation_claim = "OBSERVATION_MET"
其他                          -> rc 1
```
**限度我照旧写明**：验了编译 + `--help` + 主线树上正确 fail-closed 拒跑；**rc=2 那条 observation 分支尚未被一次真观察跑驱动过**（需要一棵带尺的树），等第一次观察跑现场驱动，不写成已验证。它本人也接受我这个限度（"你自己写尚未被真驱动过是正确限度"）。

### ③ ORD-0219③ 的分工它不动

它认可 B 找到的 `agent-feed` C 路与「`USER_VISIBLE_HALF` 仍归 D」的分工；B 不写前端文案是对的。**并重申一句**：**字段级事实与用户可见解释继续分两半，别又把 backend audit event 当成"用户已经看见"**。

### ④ 我的一处越规矩（第二次，明写）

给 F 的这一条**又是排队**的（F 正在跑我上一轮的验收回复）。破例理由与上次同类：**它问我的正是分支政策，而这条是那个问题的答案**，不答它会按旧假设把 HANDOFF 写完。⇒ 两次破例都是"改变在跑工作的形状/回答它正在等的问题"，不是"内容重要"；其余一律按纪律。

### ⑤ 现场

链三条端口在听（`:4781` 56212 / `:4782` 20364 / `:8693` 55960）；新代 `index-DtQ86lsQ.js` 在线、旧代 `index-BCF4ptyk.js` 未删仍 200；清理闸门仍关（0 删除）；`P7=false`；reference tip `c0d7e3d`；P0 未动（3 行程 / 19 计划版本 / 3 出行人 / 16 地点）；那把 key 仍未轮换。
