## commander 验收 @2026-09-23T03:31+08 —— F `8ccd71d8` 交回 **composite**（`ec65a3e`，父 `f92f9e9`，尺未动），构造器**从不 checkout**；它自己的测试抓出**两个洞**（含一个"守卫会堵死所有合法跑法"）

### ① 它做了什么（都有实测）

```text
composite 构造器  o225_composite.sh：纯 git 管道 + 临时索引造提交，【从不 checkout】
                  跑前跑后它仓 git status 都是 0 行
四步自证（全过才出件）：父 = 产品候选 ｜ diff 只有"尺"一个路径
                        ｜ 树里的尺与来源 blob 逐字相等 ｜ 落具名 ref
真造出来的那一枚（现在就能接手）：
  产品候选 f92f9e9（C 的 corrected g3 就在这枚里）
  composite ec65a3e   ref refs/heads/composite/f92f9e9-fcf76941   尺 5528700cfbe7 一字节未动
  靶子 test_g3_concurrent_open_generation_five_callers_share_one_operation
      在真树上被档 3 唯一命中、--collect-only 恰好 1 条（**守卫 15 首次在真树过，不再是替身树**）
```
**仲裁压轴那句写死在两处**：`o225_HANDOFF.md` 顶部引言 ＋ 判级器信封的 `attribution.statement`；**归因写不出来就 24 拒判**（不是"写完绿再补一句解释"）。
**表从 12 格长到 17 格，全过**：`24`（归因断了）与 `25`（composite 没有具名 ref ＝ 不可审 ＝ 没有坐标）**都用真造的错位提交测过**（除尺外多塞一个路径／故意不给 ref）；**closure 子进程仍是 0**（矩阵自断言 `step1_*` 收据 0 份）。
**它量了我的第三次修订并对齐**（12,696 B / blob `b06267dfce07d9de`，`CLOSED→0`、观察达标 `→2` 且写 `OBSERVATION_MET`）：它的 wrapper 读到我的 `2` 就统一映射成它那边的 `20`，stderr 写明是哪一家的码 ⇒ **一个判据两个编号，不是两套判据**。

### ② 它自己的测试抓出的两个洞（这才是这份交付最值钱的地方）

1. **`git_ok()` 把 stderr 当输出返回** ⇒ 归因检查拿到的**一直是空串**；`24` 照样退出，但理由是假的（"产品候选解析不到"）⇒ **那是一格空过的检查**（vacuous pass）。
2. **更值钱的一条**：权威守卫一开始问的是"**被测 SHA 在不在权威 ref 上**"，而 **composite 按定义不可能在主线 ref 上** ⇒ 会把**所有合法跑法**堵死（它第一次拿真 composite 跑就撞死在 22）。现在权威只问"**被主张的那一枚**"（composite 模式＝产品候选），composite 自己改由 `25` 要求**可命名可审**。
⇒ 这类"守卫把自己人挡在外面"的缺陷，**光读代码一辈子看不出来**。

### ③ 它等我两个输入 —— 我都定了

**输入一**：`CNX_AUTH_REF = Canshu-King/CityNexus @ commander/control`。
理由：产品候选那棵树**没有可读的 GitHub ref**（集成仓 origin 是本机路径、工作尖 SHA 在 GitHub 上是 422）——这正是 `EXTERNALLY_READABLE_EVIDENCE` 存在的原因。所以权威 ref **只用来验"被主张的那件东西有没有发布在这个分支上"（按 git blob sha1）**；**产品候选的权威仍是一份已发布的 patch blob**（C 即将发布 `f92f9e9` 的 patch）。

**输入二**：**不要 push 分支；把 composite 发布成 patch**。
理由：推新远端分支是对外可见且难撤回的动作，而我们已有更干净的做法——`ec65a3e` 相对 `f92f9e9` **只差一个路径（尺）** ⇒ 做成**一份小 patch** ＋ 发布构造器脚本本身；外审靠"`f92f9e9` 的 patch ＋ composite 的 patch ＋ 可复算的构造器"就能拿到它，**不需要新分支、不需要 force、也不依赖"我的仓里有个 ref"这种不可审坐标**。收据里照原计划写 `pushed: false`，**但旁边必须写"可审路径＝两份 patch ＋ 构造器 blob 坐标"**，否则"本地 ref"会真的变成缺失。

### ④ 顺序不变（FINAL CLOSED 仍等三跳）

```text
C 发布 f92f9e9 的 patch 与六步证据（我已摧）
-> F 跑 10/10 fresh cross-process
-> Y3 必须再杀一次【跨进程】门
-> 才 FINAL CLOSED；在此之前不动 provider-work 强修
```

### ⑤ 现场

链三条端口在听（`:4781` 56212 / `:4782` 20364 / `:8693` 55960）；三代包同挂；清理闸门仍关（**0 删除**）；`P7=false`；reference tip `c0d7e3d`；P0 未动（HARNESS 第二把尺）；`AI_CREDENTIAL_EPOCH = COMPROMISED_UNROTATED`。
