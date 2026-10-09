## commander 记账 @2026-09-22T22:37+08 —— HJ-P1 **二度改口且证据更强**（③ 回到"未修"，真仪器坑是"非置前标签页冻结平滑滚动"）；HARNESS 追加：**演示库里无障碍证据 0/16**（ORD-0219 范围再收窄）

### ① HJ-P1 的二度改口（这条比它第一版更值钱）

它的独立可复放脚本（`ord0223_scroll_probe.cjs`，全新上下文、0 次非 GET 请求）**推翻了它自己 19:46 的结论**：smooth 滚动在独立 Chromium 里**能推进**。真正的坑是：

```text
非置前标签页：手动 smooth → scrollY 采样 0,0,0,0,0    但 visibilityState="visible"、hasFocus()=true
置前后      ：手动 smooth → scrollY 采样 0,531,648,650,650（两个标志位仍旧 visible/true）
```
⇒ **平滑滚动只在标签页真正置前时推进，而 `visibilityState` 与 `hasFocus()` 都不反映这件事。**
它的规矩（我立为常驻）：**断言前 `page.bringToFront()`，或直接测瞬时滚动/几何存在性，别测动画**——比"移动模拟"那版危险得多，因为共享浏览器里谁的标签页不在最前，谁就会假红。

**于是 ③ 的判定回到"未修"，证据比之前任何一次都强**：同一次会话里**已置前**（刚证明此时 smooth 能推进）后走产品自己的路径——8 次采样 scrollY 全 0、hint y 全 1221、inView=false。⇒ 手动 smooth 能滚、产品那条路径滚不动，条件相同 ⇒ 不是仪器、不是 id 缺失、不是没调用（同块前一行 `speak()` 的产物拿到了句子）。它**不下结论**，只给一个可查假设（`speak()` 60ms 后的 `setSpokenReason` 触发重渲染可能取消了刚起步的平滑滚动），并给 D 两个一行可试的修法。分类回 `HUMAN_BLOCKER`，复现 **5/5**。
**它还把 ② 独立复证了**（脚本输出 `visibleHintRecomputedAfterFix: true` + `liveRegionStillStaleAfterFix: true`，累计 4/4）。

### ② HARNESS 的 EXP-008 追加：**演示库里无障碍证据 0/16**（ORD-0219 范围再收窄）

```text
seed_demo 的 16 个地点里带任何无障碍证据的 = 0/16
地点 metadata 顶层只有 duration_min / cost_minor 两个键；accessibility_evidence 与 osm_tags 各 0 次
（营业时间反而 16/16 有）⇒ 门补上也没证据可读
```
⇒ **对 ORD-0219 的含义（我照它的口径写进单）**：`STROLLER`/`LARGE_LUGGAGE` 若要求**端到端可演示**，除解析器 severity 之外还得有**证据生产者**（否则门永远读到 None，既不挡也不放）；四个 SOFT 码是**三层都缺**；且**六码不要混成一次改 `_CAPABILITY_GATE_CODES`**。
它自己记了两次假阴性（先 grep `data/`、再想 grep `app/`），最后改成问存储——又是"先打印实际键再下结论"的实例。blob `2584e29ed52612df`（1,486 B，可读）。

### ③ 我的处置

- ORD-0220 ③ 维持 **`HUMAN_BLOCKER`，5/5**，等 D 用它给的两个一行修法之一（`behavior:"auto"` 或把滚动排到 `spokenReason` 落地之后）；
- ORD-0222 ② 维持 **4/4**；
- ORD-0219 的 amend 我再补一层：**"端到端可演示"必须有证据生产者**，否则这两个码修完也只在合成夹具里能演示——范围问题我交仲裁（产品决定：演示库要不要补无障碍证据，还是接受"仅合成夹具可演示"）；
- 它要发布的 `evidence/hjp1_0223/` 三样（本块文本 + probe 脚本 + JSON）我照旧代发。

### ④ 现场

working tip `dfdc5d5`（19:37，**已 60 分钟无新提交**——D 在等它给的两个修法落码）；链三条端口在听；`P7=false`；reference tip `c0d7e3d`；P0 未动（用户库 3/3/19/1/1）；那把 key 仍未轮换。
