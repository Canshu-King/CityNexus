"""Append sections 5 and 6 to the session-recovery note: a self-correction, then the finding that replaces it.

The earlier sections drew a conclusion from a reading that turns out not to discriminate -- the same
address bounced the stranger AND the owner.  The old text is left exactly as it was shipped; the
correction is appended, with the receipts that carry the discriminating pair.
"""
import io
import sys

PATH = r"D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261029_SESSION_RECOVERY_IS_BY_DESIGN.md"
text = io.open(PATH, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in text else "\n"
if "## 四、本班顺手量到的两枚仪表缺陷" not in text:
    sys.exit("ABORT section 4 is not where this append expects it")
if "## 五、" in text:
    sys.exit("ABORT sections 5/6 already appended")
lines = [
    "",
    "## 五、更正：§一 里那条推论不成立（正对照失败了）",
    "",
    "§一 末句写的是「所以『前端加一个回到旧行程的按钮』这条路是假的：按下去读不到东西（:8 就是证据）」。",
    "证据本身没读错，但它不判别。臂 bs140 把两半都跑了一遍 —— 同一身份**自己刚建**的那趟，和**上一身份**建的",
    "那趟（`trial/results/20261026_gozero/bs140-ownership-discriminated-390.txt:7` 现读 `different_owner=true`）：",
    "",
    "    A_OWN_JOURNEY            shape=REDIRECTED_TO_CREATE            （:8）",
    "    B_OTHER_SESSION_JOURNEY  shape=REDIRECTED_TO_CREATE            （:9）",
    "    VERDICT ROUTE_BOUNCES_EVERYONE_control_failed_…                （:11）",
    "",
    "也就是说：拿自己刚建的行程做正对照，也被送回新建向导。既然 owner 自己也读不到，「陌生人读不到」这件事",
    "就**不能**归因到归属或权限上 —— §一 那句推论降级为未证。r139 的 `:6-9` 是同一形状的另一次读数，",
    "它的 `VERDICT CONTROL_FAILED` 已经把警报报出来了，是我当时没有把它当成对前一条推论的反驳。",
    "",
    "## 六、换掉它的新事实：Revolution 根本没有「能用地址打开某趟行程」这扇门",
    "",
    "`frontend/src/main.tsx:52` 只把 `/revolution` 前缀交给 Revolution，其余路径一律落到 V8 壳",
    "（`:55-59`）。而 Revolution 这一侧（`frontend/src/trial/**`）出现的十四处 `/journeys/` 全部是",
    "`/api/v1/...` 的取数地址，**没有一处是页面地址** —— 现读法：`grep -rn \"/journeys/\" frontend/src/trial/`。",
    "所以 `/journeys/<id>` 从来就不在 Revolution 的路由里：它由 V8 壳渲染，V8 壳认的是另一套会话，看不见",
    "Revolution 建的行程，于是显示它自己的新建向导 —— 这与 bs140 两半都 REDIRECTED 完全吻合，",
    "也跟归属无关。旁证：`main.tsx:64-71` 那段补丁专门处理「粘贴链接带星号」的情况，注释原话就是不想",
    "「silently showing the unrelated V8 \"New Journey\" wizard」，说明这面墙早就被人撞见过一次。",
    "",
    "于是 #332 的完整根因是两件事叠在一起，缺一条都回不去：",
    "",
    "一、凭据只在这次浏览的会话里（`frontend/src/lib/travelerSession.ts:17`、`:40-41`，注释 `:10-13`、`:59-62`）；",
    "二、Revolution 没有可分享、可回访的行程地址（`frontend/src/main.tsx:52` 与上面那十四处的形制）。",
    "",
    "因此裁语清单要在 §三 的甲/乙/丙之外加一条 **丁**：先给 Revolution 一条真能打开某趟行程的地址",
    "（例如 `/revolution/journey/<id>`，并把 `/journeys/:id` 在持有 traveler bearer 时导进 Revolution 而不是 V8）。",
    "丁不解决身份持久化，但没有丁，甲/乙做完旅客仍然只能靠 tab 与卡片找路。这条与 #404（深链接要落到那一屏）",
    "同族 —— #404 闭在 V8 线上，Revolution 这一线没被它罩住。**我没有动 `main.tsx`，也没有动任何路由**：",
    "把 `/journeys/:id` 改道会直接改变 V8 现有行为，属跨树口径，要点名。",
    "",
    "补一句仪表账：撞车尺在 r139 上架那一刻就咬住了它复用 r137 profile 这件事（`PROFILE_CLASH "
    "_chrome_gozero_bp136b` ⇒ `COLLISIONS 1`），已给它独立 profile 并在文件头声明不再重跑；判别读数由带正/",
    "负对照的 r140 承担。尺又一次比我先发现问题。",
    "",
]
io.open(PATH, "w", encoding="utf-8", newline="").write(text + nl.join(lines) + nl)
after = io.open(PATH, encoding="utf-8", newline="").read()
print("BYTES_BEFORE", len(text.encode("utf-8")), "BYTES_AFTER", len(after.encode("utf-8")))
print("PREFIX_INTACT", after.startswith(text[:2000]))
print("SECTIONS", after.count("## 五、"), after.count("## 六、"))
print("TAIL", repr(after[-30:]))
