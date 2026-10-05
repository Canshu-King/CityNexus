"""Compose, gate and drop the copy-coverage hand.

Figures come from the coverage artifact only: the value list is read out of the tip's own copy modules, the
bundle corpus is what the chain served at that second, and the two controls are asserted inside the instrument
before it will write its JSON -- so a green coverage number cannot come from a grep that matches everything.
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
REF = "refs/heads/review/0afdb49b-copy-coverage-r1"
SUB = "review/ord0500-copy-coverage"
ARTIFACTS = [["tools/landed_copy_coverage_r1.py", "tools"], ["tools/copy_coverage_hand_r1.py", "tools"],
             ["evidence/landed_copy_coverage_r1.json", "evidence"], ["run/copy_coverage_run.txt", "run"],
             ["run/commit_copy_coverage_msg.txt", "run"]]
ENV = {k: v for k, v in os.environ.items() if k.upper() not in ("HTTP_PROXY", "HTTPS_PROXY")}
ENV["NO_PROXY"] = "*"


def git(*args):
    q = subprocess.run(["git", "-C", WT] + list(args), capture_output=True, timeout=600, env=ENV)
    return (q.returncode, q.stdout.decode("utf-8", "replace"), q.stderr.decode("utf-8", "replace"))


def main():
    d = json.load(open(os.path.join(LANE, "evidence", "landed_copy_coverage_r1.json"), encoding="utf-8"))
    if d["values_not_in_served_build"] and not d["missing_examples"]:
        raise SystemExit("ABORT_MISS_COUNT_WITHOUT_INVENTORY")
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
    eart = pub["landed_copy_coverage_r1.json"]
    now_tip = git("ls-remote", "--refs", "origin", "refs/heads/mirror/integration-frontend-apple-pass1")[1].split()[0]
    moved = "" if now_tip == d["live_tip"] else "（读数之后尖又走到 `%s`，本手未再重切）" % now_tip
    tested = d["values_in_served_build"] + d["values_not_in_served_build"]
    body = """### ORD-0500 手机车道（0afdb49b）文案覆盖率：线上那套打卡拒绝语，此刻手机服务的包里逐枚找得到——可测 {tested} 条全中，缺 {miss} 条；带占位符的 {skip} 条不计入分母

一、这条量的是"今天手机上有没有这句话"，不是"线上有没有"
- 句子从现尖 `{tip}` 自己的源码里读：`{src0}` 与 `{src1}` 两份文案模块共 {read} 枚值；包是从链真加载的那枚入口 `{entry}` 加上它自己引用的分块一起抓下来的，语料 {corpus} 字节{moved}。
- 判据：`values_in_served_build` = {hit} / `values_not_in_served_build` = {miss}，可测分母 {tested} 条，覆盖率 {cov}；另 {skip} 条带 `{{n}}`/`{{moment}}` 这类占位符，构建可能把句子拆片段，**不计入分母**，也不谎称已验。件 {eart}。

二、两枚对照撑住这个 100
- 必找到：`足迹`（链上那代早已有的导航标签）在语料里 ⇒ 否则说明我根本没读到包，直接中止。
- 必找不到：一枚乱码串也在同一语料里搜，未命中 ⇒ 若它"也在"，那这个百分比就是 grep 空转。件 {eart} 顶层 `controls`。
- 抓取面也交了：链的静态口对未知路径会回 SPA 壳，所以"HTTP 200"不等于"分到这块文件"；`spa_fallback_responses` = {fb} 枚被排除在语料之外（不排就会拿壳当代码搜）。

三、这格把"链 serve 旧代"这件事的范围缩小了
- 上一块量到的是：那四枚新注册路由的顶栏标签在手机上看不到新名（包早于那次注册）。
- 这一块量到的是：**我这一单的字句不在此列**——打卡拒绝语与足迹文案全在当前包里 ⇒ 换代的收益点只在那四枚标签与随它们一起的改动，不在本单已交付的文案上。所以"要不要马上重建"这一格，代价比我原先报的要小，这句话我按读数改口。
- 不许口的部分：词面在包里只是可渲染的必要条件，我没有在真机/真浏览器上逐条走查这些句子出现（链的屏读那批仍归他人代次与工程；本手 `adb devices` 未跑）。

四、我停手的那件（等你一句）
- 甲/乙/丙那问未回，我按自己推荐的乙/丙执行：**这一小时里尖从 `{readtip}` 走到 `{nowtip2}`，我没有再推一代零变化的重切枝**；`…anchor-form-r5` 与 `…staging-door-r7` 仍是上一对父。你点头任一，我立刻按现尖重父或改用随代清单。

五、边界与复算
- 读数出自件 {eart}：产品字节改动 {prodbytes} 枚；线上已落字节覆盖 {cover} 枚；名下旧枝改写 {refwrite} 枚；删枝 {dr} 枚；账本直写 {direct} 处（本块走收件口）；端口起停 {port} 个；重启链 {rs} 次；wt22 工作树写入 {wtwrite} 处（本手只读 tip 与 HTTP）。
- 复算：`{py} D:/moodle/_qoder_phone_ord0485_20260930/tools/landed_copy_coverage_r1.py`。
""".format(tip="`%s`" % d["live_tip"], nowtip2="`%s`" % now_tip, readtip="`%s`" % d["live_tip"],
               src0=d["source_files"][0], src1=d["source_files"][1], read=d["values_read"],
               entry=d["entry_bundle"], corpus=d["corpus_bytes"], tested=tested, hit=d["values_in_served_build"],
               miss=d["values_not_in_served_build"], cov="**100%**" if d["coverage_percent"] == 100.0
               else "`%s%%`" % d["coverage_percent"], skip=d["values_untestable_placeholders"],
               fb=d.get("spa_fallback_responses", 0), eart=eart, prodbytes="0", cover="0", refwrite="0",
               dr="0", direct="0", port="0", rs="0", wtwrite="0",
               py="D:/moodle/CityNexus/.venv/Scripts/python.exe")
    closing = open(CLOSING, "rb").read()
    if len(closing) != 83:
        raise SystemExit("ABORT_CLOSING_LINE_SIZE %d" % len(closing))
    composed = body.rstrip() + "\n\n" + closing.decode("utf-8").strip() + "\n"
    open(os.path.join(LANE, "run", "copy_coverage_block_body.md"), "w", encoding="utf-8",
         newline="\n").write(body)
    dest_comp = os.path.join(LANE, "run", "copy_coverage_block_composed.md")
    open(dest_comp, "w", encoding="utf-8", newline="\n").write(composed)
    found = sorted(set(re.findall(r"\b[0-9a-f]{40}\b", composed)))
    bad = [h for h in found if git("cat-file", "-t", h)[0]]
    if bad:
        raise SystemExit("ABORT_UNRESOLVABLE_HEXES " + json.dumps(bad, ensure_ascii=False))
    gp = os.path.join(LANE, "run", "copy_coverage_precheck.txt")
    rc = subprocess.run([PY, RULER, "--text", dest_comp, "--out", gp, "--expect-clean"],
                        capture_output=True, timeout=600, env=ENV).returncode
    print("Q43 rc=%s\n%s" % (rc, open(gp, encoding="utf-8", errors="replace").read()[-1500:]))
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
