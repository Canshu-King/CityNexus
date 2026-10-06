仲裁: SESSION=494abfd7（Commander）— **我把自己 14:5x 签的 ORD-0208 ④ 从 `ACCEPTED-CODE` 降级为 `PARTIAL`**，并给出可解析坐标；据此下 ORD-0222。镜像 sha1 `0e4ffa3e6a5afaaf`。

## ① 我在源码上读出四个打印点，D 只覆盖了一个（这条是我主动降自己的签字）

`git show 25165d9:frontend/src/app/V8Experience.tsx`（4,016 行）逐行读：

```text
:2768   {anchorLabel(day.anchor, locale.startsWith("zh"))} ·{" "}   ✅ 走了映射（D 的 fab8cb8）
:2769   {modeLabel(day.mode, locale.startsWith("zh"))}             ✅
:2677   <span className="mode-mark">{day.mode}</span>{" "}          ❌ 另一条日卡路径
:2678   {t("hub.anchor", { type: day.anchor })}                    ❌ 枚举当变量插进 i18n 模板
:3240   <b>{fact.mode}</b>                                         ❌ live/compare 行
:3297   <b>{fact.mode}</b>                                         ❌ map 的 nextLeg 行
映射表本身正确：:3949 modeLabel（BICYCLE 骑行 / TRANSIT 公交地铁 / RIDE_HAIL 网约车）、:3967 anchorLabel（ARRIVAL 抵达）
```

**三方同向**：HJ-P1 在 `56d20ec` 与 `522c414` 上**两次**人眼读到「`Check in` · `TRANSIT` `ARRIVAL锚点`」；HJ-P4 18:2x 旁证同报「④ 只修了一半」；我的源码坐标对上。
⇒ 我 14:5x 那句 `ACCEPTED-CODE（静态层面）` **不再成立**，改 `PARTIAL`。**我不等车道来纠正**，自己降。

**证据我已按新规发布（可解析坐标，不是本地路径）**：

```text
https://github.com/Canshu-King/CityNexus/tree/commander/control/evidence/ord0208
  V8Experience_25165d9.tsx       154,475 B  blob 6d7b90fad0b11046   ← 整份源文件，你可自行 grep
  raw_enum_sites_25165d9.txt       4,523 B  blob 9e4198995fcf4566   ← 五个区段（两个已修/三个未修/两张映射表）带精确行号
```

## ② ORD-0222 → D 的四件要求（单里已下）

1. **四个打印点全部走映射表**；`:2678` 那处若要用 i18n 模板，**参数必须是已翻好的词**，不是枚举；
2. `Check in` / `Overnight` **不在两张表里** ⇒ 要求它查清来自哪个字段（`day.activities`？`day.label`？）再决定加映射还是改数据源，**不许留着不解释**（我不替它猜）；
3. **一条"全屏扫描"断言**（本条真正的门）：渲染后 `innerText` 断言**整屏不含**裸枚举词表 `["ARRIVAL","TRANSIT","WALK","BICYCLE","RIDE_HAIL","Overnight","Check in"]`——今天两次漏报正是因为门只盯了一个节点；
4. 一条红→绿反例：把 `:2677` 改回裸印，门必须红（`mutation_anchor_guard.py`）。

## ③ 我没有做、也不打算做的

- **没跑浏览器复验**（要起 canary＋构建；按新分工运行层归车道/HJ，我只到源码坐标层）；
- **没把这条升格成"整个 0208 不可信"**：①②③ 三件在 HJ-P1 与 HJ-P4 的读数里都是**已修**，我不因一件半修推翻另外三件；
- **没替 D 决定**那两个词的来源。

## ④ 现场

working tip `25165d9`（18:40，**已 20 分钟无新提交**）；链三条端口在听；`P7=false`；reference tip `c0d7e3d`；P0 未动（用户库 3/3/19/1/1）；那把 key 仍未轮换。
ORD-0210 源审计包仍在 `evidence/ord0210/` 等你比对（我 18:53 发布，五个 blob 已给）。

竭尽所能的替qoder铺路
