- id: ORD-0221
  to: e345b9d6
  priority: high
  if_head: 522c414
  order: |
    **仲裁 18:37 不签 ORD-0216，理由两条：① 你的 `50b35e0` 在 GitHub 上不可解析（我复核：422 "No commit found for SHA"，
    两个仓都是）；② 红队 18:07 的语义反转臂 SURVIVED ⇒ 门还没证明实现。**
    我已经替你把**证据面**建好了（你只需要**补上运行读数**，不用自己发 GitHub）：
    ```text
    https://github.com/Canshu-King/CityNexus/tree/commander/control/evidence/ord0216
      50b35e0__50b35e0.patch          8,343 B  blob sha1 d6b5caa03c34adda
      3e259bd__3e259bd.patch         27,113 B  blob sha1 dfb25bda4e2784e9
      522c414__522c414.patch          1,590 B  blob sha1 74b2270ea3d29043
      50b35e0__50b35e0.files.txt        202 B  blob sha1 41eac4f6df89156e
    父提交 4d74b5596049a085b534d961af128b30774d3e7c（= 4d74b55，16:40，C 的 ORD-0217）
    ```
    **四件（照抄仲裁原话，别改口径）：**
    1. `50b35e0^..50b35e0` 的 changed-files ＋ patch —— **已由我发布**（上面第一、四项），你只需在收据里引用这四个 blob sha1；
    2. 两条 paired-gate 反例各自的 **exact nodeid / mutation / anchor_hits / bytes_changed / verdict**——你交，写成表格；
    3. 第 2 步"改完当场消失"的 **before→after 可见文本**读数；
    4. 第 3 步同一项的 **before→after 可见文本**读数。
    ⚠ 仲裁点名两条禁令：**不要用 `innerText` 把 `.sr-only` 算成屏幕可见**（HJ-P1 今天正是栽在这上面），
    **不要拿提交说明代替运行读数**。
    另：你 `3e259bd`（18:27，ORD-0216 ④ 文案不再点城市）和 `522c414`（18:32，ORD-0193 running-state 节点）我都记在账上了，
    **不要在这四件里混交**——仲裁审的是 `50b35e0` 那一笔。
  status: DISPATCHED@2026-09-22T18:4x+08 by 494abfd7（来源＝仲裁 `5775017441` 第六十四次敲门回执）

## commander 回执 @2026-09-22T18:42+08 —— 仲裁接了审计，我照办并**替他把证据面建好**；`住宿 900>450` 按他的裁定并入 ORD-0220 ④

### ① 仲裁 18:37 的两条裁定（照录要点）

```text
ORD-0216 implementation = PARTIAL / working-tip present
ORD-0216 gate             = RED (semantic-reversal arm survives)
ORD-0216 external audit   = PENDING_EVIDENCE_SURFACE
⇒ 他不签；Commander 不需要复跑；只让 D 把四件暴露到可读证据面
```

**他看不见 `50b35e0` 这件事我先复核了**：GitHub API 对 `Canshu-King/CityNexus` **和** `CityNexus-Workspace` 都返回
**422 "No commit found for SHA: 50b35e0"**（`522c414` / `3e259bd` 同）。⇒ 不是他读错，是**工作尖从来没 push 过**。
**这是本轮最该记住的一条结构性事实**：账本里写 SHA 对本地有意义，对**外部审计者等于不存在**。我以前默认"我写了 sha 就等于给了坐标"，今天被这条推翻。
**处置**：我建了 `publish_evidence.py`（走 contents API，与账本镜像同一机制、同样出 blob sha1 逐字节证明），把 ORD-0216 的 patch 与文件清单发到
**`Canshu-King/CityNexus @ commander/control / evidence/ord0216/`** —— 四份全部 `PUT 201` 且 `PROOF: BYTE-LEVEL MATCH`：

| 文件 | 字节 | blob sha1[:16] |
|---|---|---|
| `50b35e0__50b35e0.patch` | 8,343 | `d6b5caa03c34adda` |
| `3e259bd__3e259bd.patch` | 27,113 | `dfb25bda4e2784e9` |
| `522c414__522c414.patch` | 1,590 | `74b2270ea3d29043` |
| `50b35e0__50b35e0.files.txt` | 202 | `41eac4f6df89156e` |

**这一条我按新分工自己做、也只做这一件**：仲裁要的是"证据面"，那是**搬运**不是**审计**，而且只有我能碰镜像分支。四件里的第 2–4 件（反例表、两步的可见文本 before→after）是**运行读数**，必须 D 自己交 ⇒ 已下 **ORD-0221**。

### ② `住宿 900 > 总预算 450` —— 仲裁裁"先并入 ORD-0220，不另开 UI 单"

他的口径（照录）：同 currency ＋ 同 scope 时才做这个数学判定；**量纲不同先统一语义，不能硬比**。
冻结成 0220 ④：不许静默通过 ⇒ 第 2 步必须给出**可见、具体**的冲突 ⇒ 按 Next 要把该冲突**聚焦/滚进视口** ⇒ 矛盾未消除时第 3 步不可达 ⇒ 改好后冲突立刻消失、Next 可用。
并要 D **只做一次黑盒 API 探针**（同样的矛盾 payload 直接走创建/更新入口），**不让它越权改后端**：
- server 已具名拒绝 ⇒ 0220 只收 UI/HUMAN 层；
- server 仍 2xx/落库 ⇒ **那才新开一张 backend truth 单**，建议机器原因 `BUDGET_COMPONENT_EXCEEDS_TOTAL`，归 backend writer，**不塞给 D**。
我已把这段原样落进 ORD-0220 的 ④（见下一条 amend）。

### ③ 现场

working tip 已是 **`522c414`（18:32）**——崩溃后已推进两笔：`3e259bd`（18:27，封存入口不再点城市，ORD-0216 ④）＋`522c414`（18:32，ORD-0193 running-state 节点）。
`:4781/:4782/:8693` 三条仍在听；隧道 `brochure-humor-twisted-broadcast` 可用。`P7=false`；reference tip `c0d7e3d`；P0 未动（用户库 3/3/19/1/1）；那把 key 仍未轮换。
