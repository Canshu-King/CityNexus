r"""扫全部本地 git 树，算"哪一棵有没有能推到 GitHub 的远端"，并把结果写成一条总线帖。

09-26 13:40 我为了核号令者那句"剩下全部卡在我没推枝"，去 D 的那棵树上看了一眼：
`git -C _qoder_d_ord0338_fix cat-file -t 1a779b69` = commit（东西在、可达），
但那棵树的 remote 只有一个 `iso -> D:/moodle/_qoder_th_20260918`，**没有任何 github URL** ⇒
"推枝"这件事在这棵树里不是不愿做，是没有门可推。这条要量全：39 棵树里到底几棵是这样。
"""
import io
import os
import re
import subprocess
import sys
import time

ROOT = r"D:\moodle"
CLOSING = io.open(os.path.join(ROOT, r"_qoder_cmdr_ref_20260921\live_checks\CLOSING_LINE.txt"),
                  encoding="utf-8").read().strip()
OUT = os.path.join(ROOT, r"_qoder_cmdr_ref_20260921\live_checks\patrol\_bus_no_origin.md")
LANE_ID = re.compile(r"(494abfd7|8ccd71d8|aad2d1f2|e345b9d6|c01d72a3|d2305848|a17ae861|8e094dec|d9e2c9ae|1d64acf5)")
LANE_NAME = {"494abfd7": "号令者", "8ccd71d8": "F", "aad2d1f2": "HJ-P3", "e345b9d6": "D",
             "c01d72a3": "B", "d2305848": "E 红队", "a17ae861": "S3", "8e094dec": "S1",
             "d9e2c9ae": "S2", "1d64acf5": "S4", "352ef353": "N1", "9759f1ac": "N2"}


def g(d, *args):
    r = subprocess.run(["git", "-C", d] + list(args), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return (r.stdout or "").strip() if r.returncode == 0 else ""


def scan():
    rows = []
    for name in sorted(os.listdir(ROOT)):
        p = os.path.join(ROOT, name)
        if not os.path.isdir(p) or not os.path.exists(os.path.join(p, ".git")):
            continue
        rem = g(p, "remote", "-v")
        urls = set(re.findall(r"\S+\s+(\S+)\s+\(fetch\)", rem))
        gh = sorted(u for u in urls if "github.com" in u)
        head = g(p, "log", "-1", "--format=%H|%ad|%s", "--date=format:%m-%d %H:%M")
        subj = head.split("|", 2)[-1] if head else ""
        lane = None
        m = LANE_ID.search(head) or LANE_ID.search(subj) or LANE_ID.search(name)
        if m:
            lane = LANE_NAME[m.group(1)]
        rows.append({"dir": name, "gh": bool(gh), "nremote": len(urls),
                     "head": head.split("|")[0][:10] if head else "", "lane": lane,
                     "date": head.split("|")[1] if "|" in head else "",
                     "subj": subj[:70]})
    return rows


def main():
    rows = scan()
    no_gh = [r for r in rows if not r["gh"]]
    with_gh = [r for r in rows if r["gh"]]
    fresh = [r for r in rows if r["date"].startswith("09-26")]
    fresh_no = [r for r in fresh if not r["gh"]]
    lane_no = [r for r in no_gh if r["lane"]]
    body = []
    body.append("`@commander 494abfd7` `@下一班` `@值守` —— 我把\"推不了枝\"量了一遍：**有些车道那棵树里根本没有能推到 GitHub 的远端**")
    body.append("")
    body.append("【值守 42d1a6fa · %s】起因是你 13:26 那块（`CMDR 13:35 本班收口`）里那句"
                "\"剩下全部卡在车道没推枝\"。我去 D 那棵树核了一下，**结论比\"没推\"更具体**：" % time.strftime("%H:%M", time.localtime()))
    body.append("")
    body.append("```text")
    body.append("D:/moodle/_qoder_d_ord0338_fix")
    body.append("  git cat-file -t 1a779b69            = commit      ← 东西在，且 branch agent/d-e345b9d6-ord0338 可达它")
    body.append("  git log -1                          = %s" % next((r["head"] + " " + r["date"] for r in rows if r["dir"] == "_qoder_d_ord0338_fix"), "?"))
    body.append("  git remote -v                       = iso -> D:/moodle/_qoder_th_20260918（只有这一条）")
    body.append("  ⇒ 这棵树里没有任何 github.com 的 URL：从这棵树\"git push\"到 GitHub 是**做不到的动作**，不是不肯做")
    body.append("")
    body.append("全量扫 D:/moodle 下带 .git 的目录：共 %d 棵，其中有 github.com 远端 %d 棵，没有的 %d 棵。" % (
        len(rows), len(with_gh), len(no_gh)))
    body.append("HEAD 落在今天（09-26）的 %d 棵里，没有 github 远端的 %d 棵（第二列=树名/HEAD/正文里出现过的车道 id，认不出写 ?）：" % (len(fresh), len(fresh_no)))
    for r in fresh_no:
        body.append("  %-32s %-8s %s %-12s %s" % (r["dir"], r["lane"] or "?", r["head"], r["date"], r["subj"]))
    body.append("")
    body.append("有 github 远端、今天有动的（对照，证明这不是普遍现象）：")
    for r in fresh:
        if r["gh"]:
            body.append("  %-32s %-8s %s" % (r["dir"], r["lane"] or "?", r["head"]))
    body.append("```")
    body.append("")
    body.append("**所以两件事分开看**：")
    body.append("1. D 的 ORD-0338 甲**字节是完好的、可核的**，而且我看到你 13:38 已经在 `D:/moodle/_qoder_cmdr_ord0338_land` "
                "里把它取过来了（本地分支 `cmdr/d-ord0338-fetched`，HEAD `436d4a36…`）⇒ 这一枚不该算在\"车道不推\"的账上，"
                "它是**树的远端配置**问题，换一棵有 origin 的树或给那棵树补一条 URL 就通。")
    body.append("2. B 的 `_qoder_b_lane_20260923`（HEAD = `38277c4e…`，也就是你 13:26 那块写的权威线）也没有 github 远端 ⇒ "
                "她那两格 `PlanWithAiSheet.tsx:1021 / :1048` 交不出来，**可能同样不是不愿，是推不动**。下一班派单前先看一眼树，"
                "别再用\"未推=未交付\"去判一个物理上做不到的动作。")
    body.append("")
    body.append("**我没有动手**：0 次 push、0 次建枝、0 次改别人的树或 remote 配置、0 字未写账本。"
                "补 remote URL 是别人的树，我按规矩不碰；要谁做、怎么做由你定。")
    body.append("")
    body.append("边界：只用 `git -C <目录> remote -v / log -1 / cat-file -t` 这类只读命令。")
    body.append("")
    body.append(CLOSING)
    text = "\n".join(body) + "\n"
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(text)
    print("WROTE %s bytes=%d trees=%d no_gh=%d fresh=%d fresh_no=%d" % (
        OUT, len(text.encode("utf-8")), len(rows), len(no_gh), len(fresh), len(fresh_no)))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
