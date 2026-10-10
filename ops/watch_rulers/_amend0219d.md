  note@494abfd7@2026-09-22T22:57+08: 仲裁第二个产品决定（`5778570154`，第七十三次敲门回执）：**补演示库的无障碍证据生产者，不接受"只在合成夹具里可演示"**；范围只做 demo-owned、可追溯、非 LIVE 的最小证据链。
  **冻结边界**：只限 sealed/demo-owned places；由确定性 demo fixtures 在服务端生产；provenance 必须显式 DEMO/SYNTHETIC_DEMO（或现有等价非-LIVE source kind）；**绝不标 LIVE_CAPTURE / provider truth**；不得泄进 normal-city/provider 路径；**与真实消费者同一 Place/evidence schema**（feasibility 走正常读取路径，不在 feasibility 里硬编码 demo 特例）。
  **最小目标（只服务本单两码）**：STROLLER 至少 1 个 place `stroller_accessible=true` ＋ 1 个 `=false`；LARGE_LUGGAGE 同理（`luggage_accessible`）。必须能演示两向：证据满足时不误挡、冲突时给 `STROLLER_ACCESS_UNAVAILABLE` / `LUGGAGE_ACCESS_UNAVAILABLE`。`None/UNKNOWN` 仍按现有 unknown 语义，**禁止把缺证据默认成 accessible**。
  **实现顺序（仲裁给 C 的五步，照录）**：① 先补 parser severity；② 再补 demo evidence producer/seed fixture；③ 走正常 `Place -> evidence -> feasibility` 消费链；④ 交一条 sealed-demo E2E（真实 demo journey 读这些 demo evidence，分别证明 pass/block 两向）；⑤ mutation：删掉/翻转 demo evidence 字段后门必须红。
  **四个 SOFT_PREFERENCE 码维持上一裁定**：不跟本次 demo evidence producer 一起扩范围；severity + evaluator 必须同批落。
  ⇒ **本单现在按 "parser + demo evidence producer + normal feasibility E2E" 推进，不必再等。**
