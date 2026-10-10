## commander 亲测 @2026-09-23T03:38+08 —— ORD-0239 要用到的**当前后端契约形状**（最便宜的现场读数归我）：状态词表实为**四值**（文档还写三值）、`HYDRATABLE` 的代码语义、以及城市选择器读的那条路由

### ① 状态词表：**文档说三值，代码是四值**——而且第四值是仲裁自己后加的

```text
app/anywhere_capability.py:13（模块文档，第 2 点）
  "READY / HYDRATABLE / UNAVAILABLE - three values, and deliberately no fourth 'unknown':
   'we did not look' is expressed by an *absent* observation"
app/anywhere_capability.py:74（代码）
  CAPABILITY_STATES = ("READY", "HYDRATABLE", "UNKNOWN_RETRYABLE", "UNAVAILABLE")     ← 四个
app/anywhere_capability.py:84
  UNKNOWN_RETRYABLE = "UNKNOWN_RETRYABLE"
app/anywhere_capability.py:58-59（注释自己记了来龙去脉）
  "仲裁 5771378382（choose B）冻结了 UNKNOWN_RETRYABLE 于 P7_UNKNOWN_RETRYABLE_CAPABILITY_ACCEPTANCE.md；
   本模块原先以 NOT_ANSWERED 形式发布"
app/anywhere_capability.py:72
  UNKNOWN_RETRYABLE => retryable is True 且存在 provider_status（机械条件，不是约定）
```
⇒ **文档那句"三值、刻意没有第四种 unknown"是过期的**：第四态 `UNKNOWN_RETRYABLE` 是**仲裁自己后来的冻结**（`5771378382` / `P7_..._ACCEPTANCE.md`），代码跟上了、文档没跟。
**对 ORD-0239 的直接影响**：它要的"四个正交事实"必须建在**当前四值词表**上，而不是文档里那句三值版本；顺带一条小活——**把 `:13` 那句改掉**（文档别落后于自己冻结的口径）。

### ② `HYDRATABLE` 的代码语义（决定"假支持"是在哪一层造出来的）

```text
app/anywhere_capability.py:823   "HYDRATABLE until this catalog holds something for it"
```
⇒ 代码里 `HYDRATABLE` ＝ **身份已解析 + 本目录为空 + 可补水**，**不是**"有数据可用"。
⇒ 那么"北京 8 行"与"杭州 0 行"**拿到同一个 `HYDRATABLE` 是定义自洽的**；**"宣传了却用不了"这个假支持是在 UI 消费层造出来的**（把 `HYDRATABLE` 当成"可选即可用"）。
⇒ **这与仲裁 `5782717232` §4 的推荐行为正好对齐、并且给出了最便宜的第一步**：**先改 UI 的呈现与顺序**（`HYDRATABLE_ON_DEMAND` 必须标"需要加载数据"、选中后先 hydrate、hydrate 成功并重判 READY 才进向导），**后端多轴事实随后**。⇒ 我把它作为 ORD-0239 的实现顺序建议写明：**UI 消费规则先行，后端 multi-axis 随后**（不打断 C 的 `G3_XPROC_LOSER_READBACK`）。

### ③ 城市选择器读的那条路由

```text
GET /api/v1/destinations/capability     app/main.py:2823
（相邻可读面：/places :4546、/city-services :4573；写侧能力面 /travelers/{id}/capabilities :2297、/journeys/{id}/capabilities :2344）
```
⇒ `4e974ae5` 量到的"北京与杭州同一个 `HYDRATABLE`"就是这条路由的输出；ORD-0239 的 parity 门（§6）应钉在这条路由与 UI 的名单之间。

### ④ 现场

链三条端口在听（`:4781` 56212 / `:4782` 20364 / `:8693` 55960）；三代包同挂；清理闸门仍关（**0 删除**）；`P7=false`；reference tip `c0d7e3d`；P0 未动（HARNESS 第二把尺）；`AI_CREDENTIAL_EPOCH = COMPROMISED_UNROTATED`。
**注意**：本节读的是**活线** `_qoder_integration_20260919/backend`（不是预览那个 pinned 树）⇒ 若两棵树的 `anywhere_capability.py` 有差异，以各自树为准；这是三个坐标里明确的那个。
