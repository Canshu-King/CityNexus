import io
P = r"D:\moodle\MORNING_ANYWHERE_SUNRISE_REPORT.md"
t = io.open(P, encoding="utf-8", newline="").read()

old7 = "- 权威树快照：`explicit 144 / synthetic_default 184 / unknown 91 / frozen_snapshot_live 24`（20:3x 我实测）`REPRODUCED(当时)`；快照会变，引用需重采"
new7 = ("- **聚合数一律降级为背景信息，不作 blocker 依据**（仲裁 `94b4d904`/`5765348482` 的规则）："
        "20:3x 我实测的 `explicit 144 / synthetic_default 184 / unknown 91 / frozen_snapshot_live 24` 只算风险提示；"
        "**02:3x 我尝试在 `520cf29` 上重采时没能确定同一来源**"
        "（搜过 `data/mock/mobility_facts.json` → 不存在；`data/mock/mobility_matrix.json` 有 71 行但**无 `fact_quality` 列**；"
        "带 `fact_quality` 的只有 `data/replay/tianjin_v135_journey_snapshot.json`，那是天津单程快照，不是全仓矩阵）"
        " ⇒ 该格记 `NOT-RESAMPLED(source ambiguity)`，**不用它下任何结论**")
assert old7 in t; t = t.replace(old7, new7, 1)

old8 = "- 现在：`PENDING`（等 SHA + receipt）"
new8 = ("- 现在：坐标与测试面到手（`e3f416f`/`08786c1`/`53a21fc`，我 `git archive` 复跑 **53/53**）；"
        "**运行时那一格记 `RUNTIME_UNOBSERVED`**（仲裁 02:29 的第三个状态名：既不是产品 FAIL，也不是 REPRODUCED——"
        "我两次连 `:8596` 都是 connection refused）\n"
        "- 升 REPRODUCED 需要仲裁定的**三层同一身份**：① 进程身份（exact SHA + build id + pid/启动时间 + 绑定端口 + 一次性库副本 id + user-unreachable/无活库写）"
        "② 我自己从该端口先做 health/root + capability 最小 GET ③ **同一进程上**跑完整链")
assert old8 in t; t = t.replace(old8, new8, 1)

t = t.replace("⇒ 结论：**代码与测试证据我已复现；\"第一次真 HYDRATABLE\"的运行时证据待 canary 重启后由我亲自 GET 复现**，已请车道给启动命令与收据路径。",
              "⇒ 结论：**代码与测试证据我已复现；\"第一次真 HYDRATABLE\" 的运行时证据 = `RUNTIME_UNOBSERVED`**（等三层身份齐 + 我自己 GET 才升档）。", 1)

io.open(P, "w", encoding="utf-8", newline="\n").write(t)
print("report updated:", "RUNTIME_UNOBSERVED" in t and "NOT-RESAMPLED" in t)
