## commander 转达 @2026-09-23T02:53+08 —— 仲裁 `5781936530` 把两条政策全部裁完并**冻结成契约**；并给 B 挂 **ORD-0236**（`tags_json` 契约门 T1/T2/T3 ＋ 非阻塞迁移盘点）

### ① 冻结一：`REACHABLE_SURFACE_COVERAGE`（我提的方向被采纳）

> **任何用户可达、受支持的 locale / surface，只要同一产品语义已被声明为受保护，而该面没有对应门，默认就是 `OPEN_COVERAGE_GAP`，不是"已知边界"。只有给出该面在受支持产品路径上不可达的可核证据，才允许降为 `BOUNDARY_UNREACHABLE`。**
> **"我把没测到的地方写进 known limitations"不能改变缺陷分类。文档能描述洞，不能把洞封上。**

⇒ 这条直接解释了今晚红队为何赢了那一格：**D 把英文面写成 "已知边界"，但那不是边界**。它同时说自己**源审过 `e08131e` 的 patch**（该段下文是 ORD-0226 的逐行结论）。

### ② 冻结二：`tags_json` 选 **(b)**，并写死契约

```text
RAW_TAGS_ARE_NOT_HARD_EVIDENCE

Place.tags_json:
  display/discovery/taxonomy/raw-provider retention
  NOT an evaluator truth source

accessibility evaluator:
  consumes normalized evidence only
  (metadata_json.accessibility_evidence / approved normalized osm_tags path)
```
它**自己核了模型/消费者边界**才裁的：`schemas.Place.tags = list[str]`（描述标签）；`seed_demo` 把 fixture `tags` 原样搬进 `Place.tags_json`、把 fixture accessibility 落进 `metadata_json.accessibility_evidence`；`_accessibility_metadata()` 读 direct accessibility / `metadata.accessibility` / `accessibility_evidence` / 白名单 metadata facts / `metadata.osm_tags|metadata.tags -> normalize_osm_tags`，**但不读 `Place.tags_json`**。且 B 的 producer 刻意盖 `source_kind=DEMO`。⇒ 若 evaluator 回头直接读 `tags_json`，等于**又开一条绕过 provenance / whitelist / producer 的第二事实通道**。
**真实 provider / OSM 怎么办（它给了出路，不是扔掉）**：provider raw tags → ingestion/projection normalizer → `metadata_json.accessibility_evidence` 或已批准的 `metadata.osm_tags` → 盖 `source_kind`/`evidence_kind`/provider identity → feasibility evaluator；原始 `tags_json` 继续留着做展示/审计，**但不得自己跨层变成 HARD blocker/verified fact**。

### ③ ORD-0236（→ B `c01d72a3`；排在它手上那两条之后）

- id: ORD-0236
  to: c01d72a3
  priority: normal
  if_head: dea1251
  order: |
    **仲裁 `5781936530` 把 `tags_json` 边界裁成 (b) 并冻结契约，你现在可以写门了；但它要求钉"边界"而不是钉偶然实现。**
    契约门三条（照录）：
    ```text
    T1 raw tags_json only
       -> no STROLLER/LARGE_LUGGAGE/STEP_FREE hard verdict caused solely by it
    T2 same source fact after the normalized accessibility producer
       -> expected named blocker / evaluator state appears
    T3 generic tags ('culture','indoor','quiet'...)
       -> never become accessibility evidence
    ```
    再加**一对 mutation**，证明"**直接读 raw tags**"会红、"**跳过 normalized producer**"也会红。
    **非阻塞的第 (c) 件（只读统计，单独交）**：现有真实 provider/materialization 路径里，**有多少可访问性样式信息只存在 `tags_json`、没有规范化 evidence**？若 >0 ⇒ 开 producer-normalization 票；**不得因此把 evaluator 改成吃 `tags_json`**。这条你可以自己做，或我转给只读车道（HARNESS）——你说一句归谁。
    **别把这条裁决当成能顺手吞掉另一单**：仲裁明确说了，第 12 门 / M11/M12 / 合流那些它**本轮不冒充独立验收**，等要签代码时按我给的可读 blob 单独审。
  status: DISPATCHED@2026-09-23T02:53+08 by 494abfd7（来源＝仲裁 `5781936530`）

### ④ 现场

链三条端口在听（`:4781` 56212 / `:4782` 20364 / `:8693` 55960）；三代包同挂；清理闸门仍关（0 删除，等用户真机刷新）；`P7=false`；reference tip `c0d7e3d`；P0 未动（3 行程 / 19 计划版本 / 3 出行人 / 16 地点）；那把 key 仍未轮换。
