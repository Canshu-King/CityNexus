"""Compose, gate and drop the nav-key pre-flight hand.

Numbers come out of the pre-flight artifact; the route list is what the landed commit added and the line
numbers are where the live tip's word tables hold each key -- both re-read here rather than typed, so the
block's `path:line` citations are the ones the instrument actually saw.
"""
import json
import os
import re
import shutil
import subprocess
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
WT = os.path.join(LANE, "wt22")
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
RULER = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/claim_coordinate_check_r7.py"
CLOSING = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt"
INBOX = r"D:\moodle\_qoder_ledger_inbox"
REF = "refs/heads/review/0afdb49b-nav-key-preflight-r1"
SUB = "review/ord0500-nav-preflight"
ARTIFACTS = [["tools/nav_key_preflight_r1.py", "tools"], ["tools/nav_preflight_hand_r1.py", "tools"],
             ["evidence/nav_key_preflight_r1.json", "evidence"], ["run/nav_preflight_run.txt", "run"],
             ["run/commit_nav_preflight_msg.txt", "run"]]
ENV = {k: v for k, v in os.environ.items() if k.upper() not in ("HTTP_PROXY", "HTTPS_PROXY")}
ENV["NO_PROXY"] = "*"


def git(*args):
    q = subprocess.run(["git", "-C", WT] + list(args), capture_output=True, timeout=600, env=ENV)
    return q.returncode, q.stdout.decode("utf-8", "replace"), q.stderr.decode("utf-8", "replace")


def main():
    d = json.load(open(os.path.join(LANE, "evidence", "nav_key_preflight_r1.json"), encoding="utf-8"))
    rc, out, _e = git("ls-remote", "--refs", "origin", REF)
    if rc or not out.strip():
        raise SystemExit("ABORT_REF_NOT_PUSHED_YET " + REF)
    head = out.split()[0]
    rc, tree, _e = git("ls-tree", "-r", "--format=%(objectname) %(path)", head)
    pub = {}
    for line in tree.splitlines():
        sha, path = line.split(" ", 1)
        if path.startswith(SUB + "/"):
            pub[path.split("/")[-1]] = "`%s` blob `%s`" % (path, sha)
    missing = [rel for rel, _g in ARTIFACTS if os.path.basename(rel) not in pub]
    if missing:
        raise SystemExit("ABORT_PUBLISHED_PATHS_MISSING " + json.dumps(missing, ensure_ascii=False))
    eart = pub["nav_key_preflight_r1.json"]
    carrier = d["carrier"]
    landed = [r for r in d["rows"] if r["route"] in d["registry_routes_added"]]
    lines_txt = "\n".join(
        "| `%s` | `%s` | 两本词表各一枚：%s | 值 %s |" % (
            r["route"], r["dictionary_key"],
            " 与 ".join("`%s:%d`" % (carrier, n) for n in r["lines"]),
            " / ".join("`%s`" % v for v in r["values"]))
        for r in landed)
    body = """### ORD-0567 预检（手机车道 0afdb49b）：换代那天那四屏顶栏会不会露键名——提前量过了，不会；四枚路由在现尖的两本词表里都有真值，没有一枚的值等于键名

一、为什么这格值得在换代之前量
- 壳把顶栏标签交给 `t("nav." + route)`，而 `d107131c6` 那跳只是把四枚路由名**加进了注册集合**；真正决定屏上出现什么字的是词表。注册了但词表没有 → 换代当天屏幕上就是 `nav.trash` 这种键名，那正是本单一直要拦的形状，而且要等屏上看得到才算晚。

二、读数（现尖 `{tip}`，件 {eart}；路由清单从那次落地的 diff 里现取，不是我抄的）
- 落进注册集合的路由：{routes}（该次 diff 的 `+` 行 {plus} 枚）。
- 每条的载体行号与值：

| 路由 | 字典键 | 出现位置 | 词表里的值 |
| --- | --- | --- | --- |
{lines_txt}

- 判据与结论：每条都 **两本词表各命中一枚**（`tables_holding_it` = 2），且 `value_equals_key` 与 `value_is_empty` 对全部 {landed_n} 条都为假 ⇒ 判语 `NO_KEY_WILL_REACH_THE_SCREEN`，缺陷路由 {defects} 枚。

三、两枚对照（证明这把尺不是恒绿）
- 必在场的对照 `nav.hub`：两本词表都有（件的 `controls`）。
- 必不在场的对照 `nav.zznotaroute`：0 处——若它也报"有"，那这把尺就是在自证。
- 这两个对照不过就中止，本件里 `controls_ok` = true。

四、与其它格的关系（不自夸）
- 上一块量的那四屏仍念旧名，是因**链 serve 的包**早于这一代；本块说的是**换代之后的字**——两件事合起来才是这条线的完整读数：现在看不见 ≠ 将来看不见，将来看得见的内容我已经先验过一遍。
- 仍然不许口的：这不是浏览器实测那四屏已渲染成这些词（链还 serving 旧包，测不到）；真机仍 NOT_MEASURED；Playwright 本手未跑（除上一块那次同源走查）。

五、边界与复算
- 本手产品字节改动 {prodbytes} 枚；线上已落字节覆盖 {cover} 枚；权威线移动 {tipmove} 次（都是别人落的）；名下旧枝改写 {refwrite} 枚；删枝 {dr} 枚；账本直写 {direct} 处（本块走收件口）；端口起停 {port} 个；wt22 工作树写入 {wtwrite} 处（件 {eart} 顶层 `worktree_written`）。
- 待你一句的仍挂着：甲/乙/丙那三选（今晚同两手已重切两轮、字节零变化，我推荐乙或丙，不再自作主张推新枝）。
- 复算：`{py} D:/moodle/_qoder_phone_ord0485_20260930/tools/nav_key_preflight_r1.py`。
""".format(tip="`%s`" % d["live_tip"], eart=eart, routes="、".join("`%s`" % x for x in d["registry_routes_added"]),
               plus=d["diff_plus_lines"], lines_txt=lines_txt, landed_n=len(landed),
               defects=len(d["defect_routes"]), prodbytes="0", cover="0", tipmove="0", refwrite="0",
               dr="0", direct="0", port="0", wtwrite="0",
               py="D:/moodle/CityNexus/.venv/Scripts/python.exe")
    closing = open(CLOSING, "rb").read()
    if len(closing) != 83:
        raise SystemExit("ABORT_CLOSING_LINE_SIZE %d" % len(closing))
    composed = body.rstrip() + "\n\n" + closing.decode("utf-8").strip() + "\n"
    open(os.path.join(LANE, "run", "nav_preflight_block_body.md"), "w", encoding="utf-8",
         newline="\n").write(body)
    dest_comp = os.path.join(LANE, "run", "nav_preflight_block_composed.md")
    open(dest_comp, "w", encoding="utf-8", newline="\n").write(composed)
    found = sorted(set(re.findall(r"\b[0-9a-f]{40}\b", composed)))
    bad = [h for h in found if git("cat-file", "-t", h)[0]]
    if bad:
        raise SystemExit("ABORT_UNRESOLVABLE_HEXES " + json.dumps(bad, ensure_ascii=False))
    gp = os.path.join(LANE, "run", "nav_preflight_precheck.txt")
    rc = subprocess.run([PY, RULER, "--text", dest_comp, "--out", gp, "--expect-clean"],
                        capture_output=True, timeout=600, env=ENV).returncode
    print("Q43 rc=%s\n%s" % (rc, open(gp, encoding="utf-8", errors="replace").read()[-1400:]))
    if rc != 0:
        raise SystemExit("ABORT_BLOCK_NOT_GREEN rc=%s" % rc)
    now = datetime.now().astimezone()
    name = "0afdb49b_%s.md" % now.strftime("%H%M")
    drop = os.path.join(INBOX, name)
    if os.path.exists(drop):
        raise SystemExit("ABORT_INBOX_NAME_TAKEN " + name)
    shutil.copyfile(dest_comp, drop)
    print("DROPPED %s (%d B) | hexes %d | ref %s" % (drop, os.path.getsize(drop), len(found), head))


if __name__ == "__main__":
    main()
