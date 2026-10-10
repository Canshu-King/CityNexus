import io
P = r"D:\moodle\MORNING_ANYWHERE_SUNRISE_REPORT.md"
t = io.open(P, encoding="utf-8", newline="").read()

old3 = """- 车道报：13 步收在 step 13，具名 `MOBILITY_EVIDENCE_NOT_HARD_ELIGIBLE`，不造 SELECTABLE `SELF_REPORTED`
- **未升 REPRODUCED 的原因**：拿不到 exact SHA + receipt（我已索要；协议已备：`ORD_0192_REPRODUCTION_PROTOCOL.md`，4,839 B，`FORMAT_CHECKED`）"""
new3 = """- 车道报：13 步收在 step 13，具名 `MOBILITY_EVIDENCE_NOT_HARD_ELIGIBLE`，不造 SELECTABLE
- **坐标已到手并被我验真**：`e3f416f` / `08786c1`（两个 discovery 提交，先红后绿）/ `53a21fc`（canary 分支 merge，零冲突）——`git cat-file -t` 全部为 commit，存在于权威对象库 `REPRODUCED(坐标)`
- **我在 `git archive 53a21fc` 上复跑四张套件：`53 passed / 0 failed`**（含 `capability_from_store` 的 g19a/b/c 三绿）`REPRODUCED(测试面)`
- **运行时那条可见链仍 `SELF_REPORTED`**：车道报的 canary `:8596` 我 02:25 去连时**已停（connection refused）** ⇒ 链上 `OSM:R:2729765 / provider / HYDRATABLE → 202 durable → 6 live 行 → planner 422 → used-edge 收据` 我没能亲眼复现
⇒ 结论：**代码与测试证据我已复现；"第一次真 HYDRATABLE"的运行时证据待 canary 重启后由我亲自 GET 复现**，已请车道给启动命令与收据路径"""
assert old3 in t
t = t.replace(old3, new3, 1)

old11 = "- Harness\n- 状态：**未唤醒**"
if old11 not in t:
    t = t.replace("## 11. Harness\n- 状态：**未唤醒**", "## 11. Harness\n- 状态：**未唤醒**", 1)

# merge health note
old1 = "- 记录时点 tip：`306f153`（02:13，`test(review): prove the four destination outcomes are separate…`，仅 `review/mutate_ord191_leg.py` +128）`REPRODUCED`（`git log` 直读）"
new1 = "- 记录时点 tip：**`520cf29`**（02:22，merge `agent/b-ord188-20260922`：**B 的 typed provider outcomes 正式进入权威树**）`REPRODUCED`\n  ⇒ 我在 merge 后的导出上复跑 provider/pending/leg 三套：**49 passed / 0 failed** —— **合并没有打断任何东西** `REPRODUCED`"
assert old1 in t
t = t.replace(old1, new1, 1)

io.open(P, "w", encoding="utf-8", newline="\n").write(t)
print("report updated; bytes", len(t.encode()))
