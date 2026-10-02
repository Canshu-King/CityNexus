"""ORD-0500 r6 self-declaration block, assembled from the lines this lane just read.

Nothing here is typed from memory: every `path:line` was read out of `git show <live tip>...` in the
same run that writes the block (the tip's own bytes, not a worktree's), and the one blob coordinate
comes from `git rev-parse` on my published ref.  If a line the block cites stops carrying the text it
claims, this script aborts instead of posting the page.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime

REPO = r"D:/moodle/CityNexus"
LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
R5 = "1230fd50bb7565ecd4dbde6041796f5bc97cc81d"
CLOSING = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt"
DICT = "frontend/src/i18n/LocaleContext.tsx"
R5COPY = "frontend/src/features/checkin/checkinCopy.ts"
TIPFILE = "frontend/src/features/trip/TripItinerary.tsx"


def git(*args):
    p = subprocess.run(["git", "-C", REPO] + list(args), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=180)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def tip_of_authority():
    rc, out = git("ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1")
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].endswith("integration-frontend-apple-pass1"):
            if re.fullmatch(r"[0-9a-f]{40}", parts[0]):
                return parts[0]
    raise SystemExit("ABORT_NO_TIP " + out[:200])


def lines_at(rev, path):
    rc, out = git("show", "%s:%s" % (rev, path))
    if rc != 0:
        raise SystemExit("ABORT_UNREADABLE %s:%s %s" % (rev, path, out[:120]))
    return out.splitlines()


def must_contain(rows, n, needle, what):
    text = rows[n - 1].strip() if 0 < n <= len(rows) else "BEYOND_FILE"
    if needle not in text:
        raise SystemExit("ABORT_CITATION %s -- line %d reads %r, not %r" % (what, n, text[:90], needle))
    return text


def main():
    tip = tip_of_authority()
    dl = lines_at(tip, DICT)
    tl = lines_at(tip, TIPFILE)
    rl = lines_at(R5, R5COPY)
    rc, blob = git("rev-parse", "%s:%s" % (R5, R5COPY))
    blob = blob.strip()

    en_button = must_contain(dl, 114, '"checkin.button": "Check in"', "en button label")
    en_dup = must_contain(dl, 118, '"checkin.duplicate"', "en duplicate row")
    en_ref = must_contain(dl, 119, '"checkin.refused"', "en refused row")
    zh_button = must_contain(dl, 1249, '"checkin.button": "打卡"', "zh button label")
    zh_dup = must_contain(dl, 1253, '"checkin.duplicate"', "zh duplicate row")
    zh_ref = must_contain(dl, 1254, '"checkin.refused"', "zh refused row")
    reads_dup = must_contain(tl, 171, 't("checkin.duplicate")', "base screen reads duplicate")
    reads_ref = must_contain(tl, 174, 't("checkin.refused")', "base screen reads refused")
    reads_label = must_contain(tl, 517, 't("checkin.button")', "base screen reads the label")
    bad_en = must_contain(rl, 60, "Tap 打卡 on one of the stops.", "my english sentence")
    cjk = re.compile(r"[\u3400-\u9fff\uf900-\ufaff\uff00-\uffef]+")
    en_rows = re.findall(r'en: "(.*?)"', chr(10).join(rl))
    hits = sorted({m for x in en_rows for m in cjk.findall(x)})

    s = {
        "t": datetime.now().astimezone(), "tip": tip, "blob": blob,
        "en_button": en_button, "zh_button": zh_button, "bad_en": bad_en,
        "reads_dup": reads_dup, "reads_ref": reads_ref, "reads_label": reads_label,
        "en_dup": en_dup, "zh_dup": zh_dup, "en_ref": en_ref, "zh_ref": zh_ref,
        "en_rows": len(en_rows), "cjk_hits": "、".join(hits) if hits else "无",
    }
    block = """### ORD-0500 r6 · 自申报：我写的英文句子里有一个只有中文档才存在的控件名（车道 phone，{t:%H:%M}）

**零、为什么这张单是我自己申报的**。`## ORDERS` 段内此刻指向我名（`0afdb49b`）的只有号令者 17:16 那两条裁语（ORD-0485 字典那笔作废、手机第二站压底栏那格归滚动容器与底栏两家），没有新单头；所以按令自申报，题面是**我自己写下的字**，量出来的坐标全在现尖与我那枚已发布枝上。现尖读回 `{tip}`（`git ls-remote origin refs/heads/mirror/integration-frontend-apple-pass1`），本块每一行引用都是 `git show` 现读，不是记忆。

**一、缺陷本体：英语旅客在屏幕上找不到我让他按的那个词**。我在 `review/newlane-ord0500-phone-checkin-entry-r5`（我 r5 那枝）写的 `frontend/src/features/checkin/checkinCopy.ts`（blob `{blob}`）第 60 行，en 档那句逐字是：

  > `{bad_en}`

而这枚按钮在 en 档屏上的真文字是 `{en_button}`（`frontend/src/i18n/LocaleContext.tsx:114`），「打卡」两个字属于 zh 档那一行 `{zh_button}`（`frontend/src/i18n/LocaleContext.tsx:1249`）。我把整表 {en_rows} 行 en 值逐行扫了一遍 CJK：命中的只有这一行，命中字是 {cjk_hits}——所以这不是风格问题，是一句**指不到屏幕上任何东西**的指引，而这一格在我 r5 那页的"没走的"里也没被具名（我只具名了真机与整套 e2e）。

**二、顺带量到的第二格：我这笔把字典里那两行变成了没有读者的字**。改之前那两行是真上屏的：基座屏读 `frontend/src/features/trip/TripItinerary.tsx:171` 逐字 `{reads_dup}`，另一支在 `:174` 逐字 `{reads_ref}`；`checkin.duplicate` 两档各一行（`frontend/src/i18n/LocaleContext.tsx:118` 与 `:1253`），`checkin.refused` 同在 `:119` 与 `:1254`。我 r5 换成本屏自带词汇之后，这四行在我这屏不再被读。**这就是我 r5 那枚文件头「一枚词一个主人」那句目前不成立的地方**——注释也是话，我一并按实测改写成「谁读、谁不读」的形状，不留漂亮话。

**三、我要裁的那一句，以及我不等裁会怎么做**。这四行死词归谁，只有你能定：(i) 留着不动，我只加一枚臂钉住「没有读者」这个事实，将来谁再读它、臂就红；(ii) 删掉，但那要动 `frontend/src/i18n/LocaleContext.tsx` 这枚全树最热的文件，而 ORD-0485 刚被裁作废、字典通道归 ORD-0533；(iii) 让我屏回去读字典那两行，等于撤销自带词汇的选择，Q64 那条路径要重量一遍。**我推荐 (i)，且不裁也按 (i) 做**——因为 (ii)(iii) 动的都是别人的东西；这一格我不自己拍。

**四、不需等裁的两格与验收形状**。（A）`targetRequired` 两档都改成插值：句子交 `{{button}}`，值取该档屏幕真在用那枚 `t("checkin.button")`（同一枚读法在基座屏 `frontend/src/features/trip/TripItinerary.tsx:517` 逐字 `{reads_label}`），我不再往句子里写死任何一档的字。验收：两档屏读各一趟（`390x844`、触摸档、判据读渲染文字），断言是「句子里出现的控件名 == 该档屏上那枚按钮的真文字」，另加一条 en 屏 CJK 命中 0 枚。（C）注释那句改成可回读的形状。（反件）把插值退回写死的「打卡」：en 那臂必须红、zh 那臂必须仍绿——这证明臂量的是**档位错配**，不是句子好不好看。（基座对照）同一把尺在现尖 `{tip}` 与在 r5 枝上各跑一趟，两趟都留件。

**五、形制与不动的那一格**。开工基座 = 现读尖；交件推新枝 `refs/heads/review/newlane-ord0500-phone-checkin-entry-r6`（r1–r5 冻结、0 force、0 覆盖），因为 r6 要改的 `checkinCopy.ts` 只存在于 r5 枝上、现尖还没有它——我不想留下需要按顺序落的两枚枝，所以 r6 是**自带 r5 全部字节的自足候选**（同一族的 `checkins.ts`／`TripItinerary.tsx`／`main.py`／契约一起带，逐枚 blob 对现尖现量，不合就 ABORT 上报而不是硬合）。编号若要给请点一句，我暂按 ORD-0500 r6 走。`LocaleContext.tsx` 在 (i) 形状下一字不动；`:8000`／`:4781`／`:4782`／`:4783`／`:4785`／`:4787`／`:8693` 不碰；`demo/reset` 不跑（它删 52 张表）；账本与权威枝不写；交块前跑 `claim_coordinate_check_r7.py --text <块> --expect-clean`。

**六、21:00 收队令之前能不能交完**：这一件的产品改动只有一枚文件一处插值，加两档屏读与一枚反件，我在 19:0x 开工，量得完就交块；量不完我按规矩把没走的那格具名报出来、不交半件。

""".format(**s)
    closing = open(CLOSING, "rb").read()
    if len(closing) != 83:
        raise SystemExit("ABORT_CLOSING_LINE_SIZE %d" % len(closing))
    out = block.rstrip() + "\n" + closing.decode("utf-8").rstrip() + "\n"
    path = os.path.join(LANE, "run", "selfdecl_ord0500_r6_%s.md" % s["t"].strftime("%H%M"))
    open(path, "w", encoding="utf-8", newline="\n").write(out)
    print(json.dumps({"draft": path, "bytes": len(out.encode("utf-8")), "tip": tip,
                      "blob": blob, "en_rows": s["en_rows"], "cjk_hits": hits,
                      "all_citations_verified": True}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
