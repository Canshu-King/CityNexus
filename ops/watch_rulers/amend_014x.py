import io
L = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
N192 = ("｜**边界钉死@01:4x（契约 64dc804b）**：B 是 **E2E runner / evidence owner，不是整条链的 implementation owner**；"
        "写域仍是 `integrations/discovery/**` + adapter 直绑测试，**不许为凑完 13 步悄悄扩大**；"
        "blocker 落在别人域 ⇒ **停在 blocker、交 owner**，owner 修完 B 从同一 stage 复跑；"
        "跨 owner blocker receipt 至少 8 项：`case/stage/input/observed/expected/evidence/owning_lane/handoff_status`。"
        "冻结句：「Owning the E2E run means owning the evidence, not every implementation layer it traverses.」")
N195 = ("｜**两处按仲裁 5764442687 收紧@01:4x**："
        "(a) 唤醒条件不是「B 拿到 Photon MATCH」，而是 **`P7_RESOLVER_INTEGRATED=true`** 七条同时成立："
        "未预录原文走正常 application path / C 确实消费 B typed result / exact raw 与 normalized 分栏 / MATCH 写入服务端所有 canonical / "
        "未解析三类 canonical=null / 作业可持久化可重放且幂等 / pending·raw key 不冒充产品身份 —— **Provider-only MATCH 不算解锁**；"
        "一旦成立就机械唤醒 Harness + P1-P4，**UI 走不通也叫醒**（走不通本身就是 finding）。"
        "(b) 晨报里最终候选那一次全量只能写 `FINAL_CANDIDATE_FULL_SUITE_OBSERVATION` + `stability_claim=NONE`，"
        "**不得写「新基线」或「基线缩小」**；可与旧 stable core 14 / 轮换残差对照，一次变少只记 observation。")
t = io.open(L, encoding="utf-8", newline="").read()
for oid, note in (("ORD-0192", N192), ("ORD-0195", N195)):
    if note[:16] in t:
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
print("bytes", len(rb.encode()), "| 0192:", N192[:16] in rb, "| 0195:", N195[:16] in rb)
