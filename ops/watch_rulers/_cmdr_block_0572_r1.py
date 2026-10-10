import io, os, time

LIVE = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
STAMP = time.strftime("%H%M")
OUT = os.path.join(r"D:\moodle\_qoder_ledger_inbox", "6efab655_" + STAMP + ".md")

NEW = "aac1142e1d25aab0a5bb4fbaa204f3a90668bd0f"
OLD = "b2fccfdf2728bbb025c3c09db36ce5ed9401ee4c"
PF = "402af67d754dea2613a87cd97e85504254c88ebe"
RB = "fc9aa71609ac510c5a35c29f087b8066bcb3d464"
RULER = "d3f66ce9fecd0790981a4fcdeb5e36b1c0fd10f2"
SPEC = "941a8bd1331d0ac6c17c22b65f8be2a775d4ff02"
V8 = "62aa8b83c35a5d408170bc2ad4470ae70e78a136"

body = u"""### 6efab655 · 号令者实例 A · ORD-0572 落地并在真屏验收过了（底栏现在会说出你在哪一屏）；应用重启把手机链静态口也杀了，已按幂等件恢复

**一、落地（权威线由我经门移动，一次快进）**

- 现读现尖 `@@OLD@@` → 落完 `@@NEW@@`；落的是车道 8ac89982 的 `refs/heads/review/8ac89982-ord0572-bottom-bar-says-where-you-are-r1`，门内 `ff_possible: true`、`line_only_commits: 0`、`candidate_only_commits: 1`、`intersection` 为空，十七枚文件逐枚 `candidate_blob` 与 `export_blob` 相同（含产品件 `frontend/src/app/V8Experience.tsx` 那枚 blob `@@V8@@` 与新 e2e 件 blob `@@SPEC@@`）。
- 门内两臂：污点尺（blob `@@RULER@@`）视野内一枚文件、落前后同为六格零增长；builder 与 vite 退出码同为 `0`，产物入口 `index-CiyY-Q-V.js`。后端整套收集 `collected` 为一七三六条、`collect_exit` 零、未中断（读数在回执件 blob `@@PF@@` 的 `gate_run.whole_suite` 段）。
- 具名：**用例我没执行**（`test_exit` 为 null）⇒ `NOT_EXECUTED_BY_CMDR`；车道自己那套读数与反件（`review/ord0572/counter_example_r1.txt`、`typecheck_r1.txt`）随枝一起入账，我复核的是屏上结果，不是它的日志。

**二、我在真屏上重跑的验收（新代次，私有栈 api `:8813` 与静态 `:49813`）**

- 被读的那一代：入口 `index-CiyY-Q-V.js`，服务字节与磁盘字节同为 1624199 字节、sha256 头十六位 `64233121de97379e`（件 blob `@@RB@@`，9871 字节）。
- 中文臂四屏全中、英文臂四屏全中：每一屏恰好一枚按钮带 `aria-current="page"`，且带的那一枚就是当前屏；其余三枚一律没有该属性；四枚可见文字逐字仍是 今天／行程／地图／我的 与 Today／Trips／Map／Me（正对照，未改文案）；空分母零屏、页面异常零次（两臂读数逐字在件 blob `@@RB@@`）。
- 别名那一支也量了：`/v8/live` 上带 `aria-current` 的是 `map` 那枚，与它既有的 `data-contrast-role="state"` 同一支判定（件 `@@RB@@` 的 `alias_and_other_screens` 段）。
- **顺手量出一格缺口（不是本次回归）**：`/v8/trash` 与 `/v8/stay` 上四枚按钮无人带 `aria-current`，同时也没有任何一枚带 `data-contrast-role="state"`——也就是底栏在"四枚主路由之外"的屏上仍然不回答"你在哪"。这是既有谓词的形状，车道只是照它对齐，所以我不算 ORD-0572 的失败；另立 **ORD-0577 → 车道 8ac89982**：让底栏在其余各屏也能说出所在（要么把该屏归到最近的一枚主路由并具名规则，要么明确画一枚"不在主路由上"的状态），验收要两臂逐屏读数、且不许改动可见文字。

**三、应用重启的现场处置（一件用户能感觉到的）**

- 本轮开工现读：我那四枚监听（api `:8813` 之前的 `:8811`、静态 `:49811` 与 `:49812`、以及手机链静态口 `:4783`）在重启后全为零个 LISTENING。
- `:4783` 是人用的那扇，我按幂等起复件 `_cmdr_lan_4783_restore_r1.py` 重新拉起：启动前 `listeners_before` 为空（不是我杀的），起后五枚路径全回 http_status=200，入口 `index-BcQ9VAso.js` 服务字节与磁盘字节同为 1622092 字节；那扇仍服务 day33 那一代（`0293e5c1cf9be4ea4e7d14005e14c508cb3f528b` 重出的产物），换代仍是人类的决定，我没动。
- 自报一处仪器错并修掉：起复件与起栈件的退出码把"零秒就绪"当失败（`ready_after_s` 初值为零、循环第一次就命中时仍是假值），所以上一轮那份 rc=1 的读数说谎。`cmdr_stack_launch_r3.py` 已把初值改成 null 并按 `is not None` 判，本轮这份 receipt 的 rc 与读数一致。

**四、没改善的部分（具名）**

- 用户此刻在手机上看不到本轮这笔（手机仍停 day33 那一代），要等一次具名换代。
- ORD-0577 是我本轮刚开的，零字节；ORD-0573、ORD-0574、ORD-0575、ORD-0576 仍未交件。
- 花费面那句在真屏仍 `NOT_REACHED_BY_CMDR`；闭合查找尺接进落地门仍 `NOT_IN_GATE_YET_BY_CMDR`；机词普查白名单仍缺 `JSON` 一枚。
- 我本轮没执行任何用例（只收集），所以"这套改动跑过全套测试"这句话我不能说。
"""

for k, v in (("@@OLD@@", OLD), ("@@NEW@@", NEW), ("@@PF@@", PF), ("@@RB@@", RB),
             ("@@RULER@@", RULER), ("@@SPEC@@", SPEC), ("@@V8@@", V8)):
    body = body.replace(k, v)
assert "@@" not in body
closing = io.open(os.path.join(LIVE, "CLOSING_LINE.txt"), encoding="utf-8", newline="").read().strip()
text = body.rstrip() + "\n\n" + closing + "\n"
io.open(OUT, "w", encoding="utf-8", newline="").write(text)
print("wrote", OUT, len(text.encode("utf-8")), "B")
