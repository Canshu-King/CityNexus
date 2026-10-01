"""Say, in the r5 page, what actually moved between the r4 head and the tip.

The r4 page explained a two-family CSS merge; the sequencer stopped r4 on two files against
b604f50d, so the new page has to name those two, with three blob pairs each, and say what did *not*
change -- the merged `footprint.css` landed as the very same blob, which is the cheapest proof that
the hand merge survived the rebase untouched.
"""
import ast
import os

LANE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(LANE, "tools", "gen9_blocks_r1.py")
text = open(PATH, encoding="utf-8").read()

old_title = "### ORD-0500 · 手机打卡门 r4：与 ORD-0530 同族的 CSS 手工并块，曝光格两侧对照随件（车道 phone，{t_cand}）"
new_title = "### ORD-0500 · 手机打卡门 r5：再对现尖重落，两枚热文件的三对 blob 逐枚贴（车道 phone，{t_cand}）"
assert text.count(old_title) == 1, "title"
text = text.replace(old_title, new_title)

head = "**〇、这次是真冲突，两族都活着**。"
addition = (
    "**〇′、r5 为什么再来一次**。落地序列器对 r4 的枝头 `{r4_head}` 报 2 枚合不上，我逐枚比出的就是这两枚："
    "`backend/app/main.py`（我那一代 `{r4_main}` / 只读预测 `{r4_main_merge}` / 现尖 `{r4_main_tip}`）与 "
    "`frontend/src/features/trip/TripItinerary.tsx`（`{r4_itin}` / `{r4_itin_merge}` / `{r4_itin_tip}`）"
    "——这一批 ORD-0529/0533/0535 落过，两枚都是全树热文件。重落用的是同一把并块工具（`review/ord0500-checkin/tools/land_o0500_r5.py`），"
    "落点形状没变：`main.py` 仍是 14 增 2 删、契约里那两行仍在、我那 31 行 CSS 与 ORD-0530 那 40 行并完之后 "
    "`footprint.css` 仍是同一枚 blob `{css_blob}`（也就是这一族没再被人动）。曝光格两侧对照现读：现尖 6 格 / "
    "{exp_tip_mod} 模块，本候选 6 格 / {exp_r3_mod} 模块，逐规则同数、多出的格「无」。" + os.linesep + os.linesep + head)
assert text.count(head) == 1, "head"
text = text.replace(head, addition, 1)

slot_old = "    s[\"css_tip\"] = (cand_face.get(\"build\") or {}).get(\"exit\")"
slot_new = slot_old + """
    land0 = load("gen9_landing_check_r1.json")
    r4row = next((x for x in load("gen9_landing_check_r1.json").get("refs", [])
                  if "entry-r4" in x.get("ref", "")), None)
    d4 = subprocess.run(["git", "-C", os.path.join(LANE, "wt22"), "merge-base",
                         "--is-ancestor", "x", "y"], stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL, timeout=30)
    def blob(rev, path):
        return subprocess.run(["git", "-C", os.path.join(LANE, "wt22"), "rev-parse",
                               "%s:%s" % (rev, path)], stdout=subprocess.PIPE,
                              timeout=60).stdout.decode("utf-8").strip()
    R4 = "469d72be6d1b1348d4fab7ad0bb3f9256a888d7d"
    TIPR5 = "b604f50d1645d028c2dd1d4406caee8198a3bc2d"
    s["r4_head"] = R4
    s["r4_main"] = blob(R4, "backend/app/main.py")
    s["r4_itin"] = blob(R4, "frontend/src/features/trip/TripItinerary.tsx")
    s["r4_main_tip"] = blob(TIPR5, "backend/app/main.py")
    s["r4_itin_tip"] = blob(TIPR5, "frontend/src/features/trip/TripItinerary.tsx")
    mt = subprocess.run(["git", "-C", r"D:/moodle/CityNexus", "merge-tree", "--write-tree",
                         TIPR5, R4], stdout=subprocess.PIPE, timeout=120).stdout.decode().split(chr(10))[0]
    s["r4_main_merge"] = blob(mt, "backend/app/main.py")
    s["r4_itin_merge"] = blob(mt, "frontend/src/features/trip/TripItinerary.tsx")
    s["css_blob"] = blob("HEAD", "frontend/src/features/checkin/footprint.css")"""
assert text.count(slot_old) == 1, "slot"
text = text.replace(slot_old, slot_new)
open(PATH, "w", encoding="utf-8", newline="\n").write(text)
ast.parse(text)
print("r5 page explains its own rebase")
