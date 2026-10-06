import io
L = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
N192 = ("｜**新增强制字段@01:3x（契约 94b4d904）**：mobility 收据必须含 `blocker_basis=USED_EDGE_INVENTORY` + "
        "`aggregate_repository_counts_used_as_blocker=false`；**拿聚合数当 blocker ⇒ receipt INVALID**；"
        "反之真实 used edges 全 hard-eligible 就**必须继续走 SELECTABLE 评估**，不许提前停在 gap。"
        "另 cbc112d6 把 provider 分类入 R14：401/403→PROVIDER_ACCESS/RUNTIME_FAILURE；"
        "只有「满足 transport 契约 + 可解析语义响应 + provider 明确返回空」才准叫 NO_MATCH。")
N189 = ("｜**升级为时间优先规则@01:3x（契约 9dafa456）**：判定顺序必须 = 验 A_before → 验 B_before → 才看 A_after → "
        "A 真 GREEN→RED 才看 B_after；故 `B_before=RED ⇒ INCONCLUSIVE`（现会误判 COUPLED）。"
        "**按顺序重写判定，不要只加一个 if**；第六组补进双向自证；"
        "全局冻结句：「Pre-existing state is not action consequence. Measure before, then attribute after.」；"
        "在此之前 14a5b64 仪器保持 SELF_REPORTED。")
t = io.open(L, encoding="utf-8", newline="").read()
for oid, note in (("ORD-0192", N192), ("ORD-0189", N189)):
    if note[:18] in t:
        print(oid, "already amended"); continue
    j = t.index("- id: " + oid)
    k = t.index("\n  status: ", j)
    end = t.index("\n", k + 1)
    orig = t[k + 1:end]
    assert t.count(orig) == 1, oid
    t2 = t.replace(orig, orig + note, 1)
    assert t2.replace(orig + note, orig, 1) == t, oid + " proof"
    t = t2
io.open(L, "w", encoding="utf-8", newline="").write(t)
rb = io.open(L, encoding="utf-8", newline="").read()
print("bytes", len(rb.encode()), "| 0192 amended:", N192[:18] in rb, "| 0189 amended:", N189[:18] in rb)
